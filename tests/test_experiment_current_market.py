"""Tests for the offline A/B/C experiment.

The current listings used here are a TEMPORARY test fixture written to pytest's tmp_path (real historical rows
re-dated to 2025-26). They exist only for the duration of a test and are never used as training data.
"""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from training.data_loading import CURRENT, HISTORICAL, SOURCE_COL, load_current, split_current_holdout
from training.experiment_current_market import (
    PRODUCTION_FILES, ExperimentConfig, ExperimentDataError, enrich_all, prepare, run, sample_weights, to_features,
    verify_historical,
)
from training.spec_enrichment import MISSING, SPEC_COLS
from training.train_utils import DATA_FILE_PATH

FAST = dict(loss='absolute_error', learning_rate=0.1, max_iter=30, max_leaf_nodes=15, min_samples_leaf=5,
            l2_regularization=1.0, early_stopping=False, random_state=42)


def fixture_csv(tmp_path, n=100, with_specs=False):
    hist = pd.read_csv(DATA_FILE_PATH).sample(n, random_state=1).reset_index(drop=True)
    dates = pd.date_range('2025-01-01', '2026-06-30', periods=n).strftime('%Y-%m-%d')
    cols = ['company', 'model', 'edition', 'year', 'km_driven', 'fuel', 'transmission', 'owner', 'seller_type',
            'selling_price'] + (SPEC_COLS if with_specs else [])
    cur = hist[cols].assign(city=np.array(['Delhi', 'Mumbai', 'Pune', 'Delhi'] * n)[:n], listing_date=dates)
    cur['km_driven'] = cur['km_driven'] + np.arange(n)  # distinct listings
    path = tmp_path / 'current-listings.csv'
    cur.to_csv(path, index=False)
    return str(path)


def config(tmp_path, **kw):
    base = dict(current_path=fixture_csv(tmp_path), output_dir=str(tmp_path / 'out'), model_params=dict(FAST),
                min_current_rows=50, min_group_rows=5)
    base.update(kw)
    return ExperimentConfig(**base)


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


# ---- stops instead of guessing ----

def test_missing_current_file_stops(tmp_path):
    with pytest.raises(ExperimentDataError, match='not found'):
        prepare(ExperimentConfig(current_path=str(tmp_path / 'absent.csv')))


def test_invalid_rows_stop_the_run(tmp_path):
    path = fixture_csv(tmp_path)
    df = pd.read_csv(path)
    df.loc[3, 'selling_price'] = -1
    df.to_csv(path, index=False)
    with pytest.raises(ExperimentDataError, match='invalid rows'):
        prepare(ExperimentConfig(current_path=path, min_current_rows=50))


# ---- 1-3 time features ----

def test_time_features_historical_current_and_age(tmp_path):
    cfg = config(tmp_path)
    historical, current_train, holdout, _, _ = prepare(cfg)
    h = to_features(historical.head(50), 2020)
    c = to_features(current_train, 2020)
    assert (h['listing_year'] == 2020).all()
    assert (h['age_at_listing'] == 2020 - historical.head(50)['year'].to_numpy()).all()
    assert (c['listing_year'] == current_train['listing_date'].dt.year.to_numpy()).all()
    assert (c['age_at_listing'] == c['listing_year'] - current_train['year'].to_numpy()).all()
    assert 'year' not in h.columns  # replaced by age_at_listing + listing_year


# ---- 4-6 holdout ----

def test_newest_20_percent_held_out(tmp_path):
    _, current_train, holdout, _, _ = prepare(config(tmp_path))
    assert len(holdout) == 20 and len(current_train) == 80
    assert holdout['listing_date'].min() >= current_train['listing_date'].max()


def test_holdout_never_enters_training(tmp_path):
    out = run(config(tmp_path))
    split = out['data']['split']
    assert out['training_rows']['A_historical'] == out['data']['historical_rows']
    assert out['training_rows']['B_historical_current'] == out['data']['historical_rows'] + split['current_training_rows']
    assert out['leakage_audit']['current holdout never entered training']


def test_holdout_never_enters_spec_lookup(tmp_path):
    path = fixture_csv(tmp_path)
    current, _ = load_current(path)
    train, holdout = split_current_holdout(current, 0.2)
    # a variant that exists ONLY in the holdout, with specs provided there
    holdout = holdout.copy()
    holdout.loc[holdout.index[0], ['edition'] + SPEC_COLS] = ['HOLDOUT ONLY', 1, 2, 3, 4, 5]
    probe = train.head(1).copy()
    probe[['company', 'model', 'edition', 'fuel', 'transmission', 'year']] = \
        holdout.loc[holdout.index[:1], ['company', 'model', 'edition', 'fuel', 'transmission', 'year']].to_numpy()
    probe[SPEC_COLS] = np.nan
    historical = pd.read_csv(DATA_FILE_PATH).head(0).assign(**{SOURCE_COL: HISTORICAL})
    (_, enriched_probe, _), _ = enrich_all(historical, probe, holdout)
    assert (enriched_probe[[f'{s}_source' for s in SPEC_COLS]] == MISSING).all(axis=None)


# ---- 7 price independence ----

def test_price_changes_do_not_affect_spec_enrichment(tmp_path):
    historical, current_train, holdout, _, _ = prepare(config(tmp_path))
    (_, _, a), _ = enrich_all(historical, current_train, holdout)
    (_, _, b), _ = enrich_all(historical.assign(selling_price=1), current_train.assign(selling_price=1),
                              holdout.assign(selling_price=10**9))
    pd.testing.assert_frame_equal(a[SPEC_COLS], b[SPEC_COLS])


# ---- 8 same holdout, weights ----

def test_all_experiments_use_the_same_holdout(tmp_path):
    out = run(config(tmp_path))
    overall = [r['overall'] for r in out['results'].values()]
    assert {o['rows'] for o in overall} == {out['data']['split']['current_holdout_rows']}
    assert len({tuple(o['actual_range']) for o in overall}) == 1
    assert all(out['leakage_audit'].values())


def test_weights_depend_only_on_source():
    train = pd.DataFrame({SOURCE_COL: [HISTORICAL, CURRENT, CURRENT], 'selling_price': [1, 2, 3]})
    w = sample_weights(train, ExperimentConfig(historical_weight=1.0, current_weight=2.0))
    assert w.tolist() == [1.0, 2.0, 2.0]


def test_city_experiment_is_separate(tmp_path):
    out = run(config(tmp_path, run_city_experiment=True, min_city_train_rows=10))
    assert {'A_historical', 'B_historical_current', 'C_weighted'} <= set(out['results'])
    assert 'EXPLORATORY_B_plus_city' in out['results']


# ---- 9 production artifacts ----

def test_production_artifacts_not_overwritten(tmp_path):
    before = {p: md5(p) for p in PRODUCTION_FILES}
    cfg = config(tmp_path)
    run(cfg)
    assert {p: md5(p) for p in PRODUCTION_FILES} == before
    written = json.load(open(tmp_path / 'out' / 'experiment_results.json'))
    assert written['production_checksums_unchanged'] == before
    assert (tmp_path / 'out' / 'model_A_historical.joblib').exists()
    assert (tmp_path / 'out' / 'experiment_report.md').exists()


def test_leakage_audit_detects_injected_leak(tmp_path, monkeypatch):
    import training.experiment_current_market as exp
    real_prepare = exp.prepare

    def leaky_prepare(cfg):
        historical, current_train, holdout, summary, report = real_prepare(cfg)
        return historical, pd.concat([current_train, holdout.head(3)]), holdout, summary, report

    monkeypatch.setattr(exp, 'prepare', leaky_prepare)
    with pytest.raises(ExperimentDataError, match='leakage audit failed'):
        run(config(tmp_path))
    assert not (tmp_path / 'out' / 'experiment_results.json').exists()


# ---- cleaned historical dataset ----

CLEANED = 'data/car-details-cleaned.csv'


def test_cleaned_historical_runs_with_missing_gas_mileage(tmp_path):
    out = run(config(tmp_path, historical_path=CLEANED))
    assert out['historical_dataset']['cleaned'] and out['historical_dataset']['mileage_values_changed'] == 102
    gas = out['gas_mileage_coverage']['historical']
    assert gas['CNG']['with_mileage'] == 0 and gas['CNG']['missing_mileage'] == 56
    assert gas['LPG']['with_mileage'] == 0 and gas['LPG']['missing_mileage'] == 38
    assert out['gas_mileage_coverage']['missing_mileage_in_training']['A_historical'] > 0  # left NaN, not filled
    assert out['leakage_audit']['historical data contains no target leakage']
    assert all(out['leakage_audit'].values())
    assert out['config']['historical_listing_year_confirmed'] is False
    assert out['config']['historical_path'] == CLEANED
    assert 'UNCONFIRMED ASSUMPTION' in open(tmp_path / 'out' / 'experiment_report.md', encoding='utf-8').read()


@pytest.mark.parametrize('column, change', [
    ('selling_price', lambda s: s.where(s.index != 0, s + 1)),
    ('year', lambda s: s.where(s.index != 5, s - 1)),
    ('mileage_mpg', lambda s: s.fillna(40.0)),  # invented values
])
def test_tampered_historical_file_is_rejected(tmp_path, column, change):
    df = pd.read_csv(CLEANED)
    df[column] = change(df[column])
    path = tmp_path / 'tampered.csv'
    df.to_csv(path, index=False)
    with pytest.raises(ExperimentDataError):
        run(config(tmp_path, historical_path=str(path)))
    assert not (tmp_path / 'out' / 'experiment_results.json').exists()


def _cleaned_with_torque(tmp_path, change):
    df = pd.read_csv(CLEANED)
    row = df['torque_nm'].first_valid_index()
    df.loc[row, 'torque_nm'] = change(df.loc[row, 'torque_nm'])
    path = tmp_path / 'cleaned-torque.csv'
    df.to_csv(path, index=False)
    return str(path), row


def test_float_round_trip_noise_is_accepted(tmp_path):
    # a CSV round trip can shift a float by a few units in the last place (e.g. 219.66895999999997 -> 219.66896)
    path, row = _cleaned_with_torque(tmp_path, lambda v: v * (1 + 1e-15))
    assert pd.read_csv(path).loc[row, 'torque_nm'] != pd.read_csv(DATA_FILE_PATH).loc[row, 'torque_nm']
    assert verify_historical(ExperimentConfig(historical_path=path))['cleaned']


def test_meaningful_torque_change_is_rejected(tmp_path):
    path, _ = _cleaned_with_torque(tmp_path, lambda v: v + 0.01)
    with pytest.raises(ExperimentDataError, match='torque_nm'):
        verify_historical(ExperimentConfig(historical_path=path))


def test_more_than_255_models_supported(tmp_path):
    # real vehicle names from the historical data, relabelled into 300 distinct models (test-only fixture)
    path = fixture_csv(tmp_path, n=300)
    df = pd.read_csv(path)
    df['model'] = [f'model{i}' for i in range(len(df))]
    df.to_csv(path, index=False)
    out = run(config(tmp_path, current_path=path))
    assert all(out['leakage_audit'].values())
