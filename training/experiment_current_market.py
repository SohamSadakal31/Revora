"""Offline A/B/C experiment: does current-market data improve prices for current listings?

    A  historical data only
    B  historical + current training portion (equal weight)
    C  historical + current training portion, current rows weighted higher (fixed, pre-declared weight)
    (separate, exploratory) B + city

Every experiment is evaluated on the SAME held-out newest current listings, which never touch training,
spec lookup, preprocessing, weights or hyperparameters. The production model is never read or written.

Run (inside the API image so library versions match production):
    python -m training.experiment_current_market [--holdout 0.2] [--current-weight 2.0] [--with-city]
"""
import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from training.data_loading import (
    CURRENT, HISTORICAL, SOURCE_COL, add_time_features, load_training_data, split_current_holdout,
)
from training.spec_enrichment import (
    MATCH_VARIANT, MATCH_YEAR, PROVIDED, SPEC_COLS, build_spec_lookup, enrich_specs,
)
from training.train_utils import CURRENT_DATA_FILE_PATH, DATA_FILE_PATH, MODEL_META_PATH, MODEL_PATH, MODEL_RANGE_PATH

OUTPUT_DIR = os.path.join('experiments', 'current_market')
PRODUCTION_FILES = [MODEL_PATH, MODEL_RANGE_PATH, MODEL_META_PATH]

CAT_COLS = ['company', 'model', 'owner', 'fuel', 'transmission']
# seller type enters as a 0/1 number so the model can be told its direction (see build_model)
DEALER_COL = 'sold_by_dealer'
DEALER_TYPES = {'dealer', 'trustmark dealer'}
NUM_COLS = ['age_at_listing', 'listing_year', 'km_driven', DEALER_COL] + SPEC_COLS  # replaces the production `year` feature
VARIANT_COL = 'edition'

# production hyperparameters (training/train_model.py), fixed - never tuned on the holdout. squared_error (on log
# price) keeps the monotonic rules exact: with absolute_error, scikit-learn re-fits leaf values after the constrained
# splits, which let ~1-4% of cars break them (e.g. a dealer priced below a private seller)
PRODUCTION_PARAMS = dict(loss='squared_error', learning_rate=0.05, max_iter=1500, max_leaf_nodes=15,
                         min_samples_leaf=5, l2_regularization=1.0, early_stopping=False, random_state=42)


class ExperimentDataError(RuntimeError):
    """The experiment cannot run on this data (missing file, invalid rows, too few listings)."""


@dataclass
class ExperimentConfig:
    # ASSUMPTION (not confirmed by the project): the historical CSV has no listing dates; its newest cars are
    # from 2020, so its listings are assumed to date from 2020. Change here if the collection year is known.
    historical_listing_year: int = 2020
    historical_listing_year_confirmed: bool = False
    holdout_fraction: float = 0.2
    historical_weight: float = 1.0      # experiment C only
    current_weight: float = 2.0         # experiment C only - declared up front, never chosen on the holdout
    run_city_experiment: bool = False
    min_city_train_rows: int = 30       # a city needs this many current training rows to be usable
    min_group_rows: int = 20            # breakdown groups smaller than this are not reported
    min_current_rows: int = 50          # refuse to run on fewer current listings
    allow_invalid_rows: bool = False    # invalid current rows stop the run unless explicitly allowed
    model_params: dict = field(default_factory=lambda: dict(PRODUCTION_PARAMS))
    historical_path: str = DATA_FILE_PATH
    current_path: str = CURRENT_DATA_FILE_PATH
    output_dir: str = OUTPUT_DIR


# ---------------------------------------------------------------- data

def _file_md5(path):
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def _range(s):
    return [None, None] if s.dropna().empty else [s.min(), s.max()]


def data_summary(current: pd.DataFrame, report) -> dict:
    as_py = lambda v: v.item() if hasattr(v, 'item') else v  # noqa: E731
    return {
        'total_rows': report.total_rows, 'valid_rows': report.valid_rows, 'invalid_rows': report.invalid_count,
        'listing_date_range': [None if d is None else d.strftime('%Y-%m-%d') for d in _range(current['listing_date'])],
        'companies': int(current['company'].str.lower().nunique()),
        'models': int(current[['company', 'model']].apply(lambda s: s.str.lower()).drop_duplicates().shape[0]),
        'cities': int(current['city'].str.strip().str.lower().nunique()),
        'fuel': current['fuel'].str.lower().value_counts().to_dict(),
        'transmission': current['transmission'].str.lower().value_counts().to_dict(),
        'seller_type': current['seller_type'].str.lower().value_counts().to_dict(),
        'price_range': [as_py(v) for v in _range(current['selling_price'])],
        'year_range': [as_py(v) for v in _range(current['year'])],
        'km_range': [as_py(v) for v in _range(current['km_driven'])],
        'missing_specs_in_file': {s: int(current[s].isna().sum()) for s in SPEC_COLS},
        # source listing ids that repeat make their rows invalid (see report); these are counted there
        'duplicate_listing_ids': int(report.invalid_rows['errors'].str.contains('listing_id is duplicated').sum())
        if report.invalid_count else 0,
        # same car details listed more than once (kept; always kept on one side of the holdout split)
        'repeated_cars_same_details': int(current['listing_id'].duplicated().sum()),
        'warnings': list(report.warnings),
    }


# Float values pass through a CSV text round trip (read, clean, write). Depending on the platform's float parser that
# can move a value by one unit in the last place (~1e-16 relative), e.g. torque 219.66895999999997 -> 219.66896.
# 1e-12 relative absorbs that noise; any real edit (even +0.01 on a torque of 60) is many orders of magnitude larger.
FLOAT_RTOL = 1e-12


def _same_values(a: pd.Series, b: pd.Series) -> pd.Series:
    """Per row: equal values, or both missing. Float columns allow FLOAT_RTOL round-trip noise; others are exact."""
    both_missing = a.isna() & b.isna()
    if pd.api.types.is_float_dtype(a) and pd.api.types.is_float_dtype(b):
        return pd.Series(np.isclose(a, b, rtol=FLOAT_RTOL, atol=0), index=a.index) | both_missing
    return (a == b) | both_missing


def verify_historical(config: ExperimentConfig) -> dict:
    """The original file needs no check. Any other historical file must be the documented mileage clean-up of it:
    same rows and columns, identical non-mileage values, and exactly the output of the cleaning rules (float values
    are compared up to FLOAT_RTOL, which only absorbs CSV round-trip noise)."""
    from training.clean_historical_data import MILEAGE, clean
    if os.path.abspath(config.historical_path) == os.path.abspath(DATA_FILE_PATH):
        return {'dataset': config.historical_path, 'cleaned': False}
    original = pd.read_csv(DATA_FILE_PATH)
    used = pd.read_csv(config.historical_path)
    if len(used) != len(original) or list(used.columns) != list(original.columns):
        raise ExperimentDataError(f'{config.historical_path}: rows/columns differ from {DATA_FILE_PATH}')
    differing = [c for c in original.columns if c != MILEAGE and not _same_values(original[c], used[c]).all()]
    if differing:
        raise ExperimentDataError(f'{config.historical_path}: non-mileage columns differ from the original: {differing}')
    expected, _ = clean(original)
    matches_rules = bool(_same_values(expected[MILEAGE], used[MILEAGE]).all())
    if not matches_rules:
        raise ExperimentDataError(f'{config.historical_path}: mileage differs from the documented cleaning rules')
    return {'dataset': config.historical_path, 'cleaned': True, 'rows': len(used),
            'mileage_values_changed': int((~_same_values(original[MILEAGE], used[MILEAGE])).sum()),
            'non_mileage_columns_identical': True, 'matches_cleaning_rules': matches_rules}


def gas_mileage_coverage(historical: pd.DataFrame) -> dict:
    out = {}
    for fuel in ('CNG', 'LPG'):
        g = historical[historical['fuel'].str.upper() == fuel]
        out[fuel] = {'rows': len(g), 'with_mileage': int(g['mileage_mpg'].notna().sum()),
                     'missing_mileage': int(g['mileage_mpg'].isna().sum())}
    return out


def prepare(config: ExperimentConfig):
    """Loads, validates and splits the data. Raises ExperimentDataError instead of guessing."""
    verify_historical(config)
    _, historical, current, report = load_training_data(config.historical_path, config.current_path)
    if current is None:
        raise ExperimentDataError(f'{config.current_path} not found - the experiment needs real current listings')
    if report.invalid_count and not config.allow_invalid_rows:
        raise ExperimentDataError('current listings contain invalid rows - fix them first:\n' + report.summary())
    if len(current) < config.min_current_rows:
        raise ExperimentDataError(f'only {len(current)} valid current listings; need at least {config.min_current_rows}')

    current_train, holdout = split_current_holdout(current, config.holdout_fraction)
    return historical, current_train, holdout, data_summary(current, report), report


def enrich_all(historical, current_train, holdout):
    """Spec lookup built from historical + current TRAINING rows only; applied identically to all three."""
    lookup = build_spec_lookup(pd.concat([historical, current_train], ignore_index=True, sort=False))
    return tuple(enrich_specs(df, lookup) for df in (historical, current_train, holdout)), lookup


def spec_coverage(df: pd.DataFrame) -> dict:
    return {s: df[f'{s}_source'].value_counts().to_dict() for s in SPEC_COLS} | {
        'rows_with_all_specs': int(df[[f'{s}_source' for s in SPEC_COLS]]
                                   .isin([PROVIDED, MATCH_YEAR, MATCH_VARIANT]).all(axis=1).sum()),
        'rows': len(df)}


def to_features(df: pd.DataFrame, historical_listing_year: int, with_city=False) -> pd.DataFrame:
    """Same rules for every frame: time features, lowercase text. Uses no statistics of the frame itself."""
    out = add_time_features(df, historical_listing_year)
    seller = out['seller_type'].astype('string').str.strip().str.lower()
    out[DEALER_COL] = seller.isin(DEALER_TYPES).astype(float).where(seller.notna(), np.nan)
    cols = CAT_COLS + NUM_COLS + [VARIANT_COL] + (['city'] if with_city else [])
    out = out.reindex(columns=cols + [SOURCE_COL, 'selling_price', 'listing_id'])
    for col in CAT_COLS + [VARIANT_COL] + (['city'] if with_city else []):
        text = out[col].astype('string').str.strip().str.lower()
        out[col] = text.astype(object).where(text.notna(), np.nan)  # plain objects + np.nan for the encoders
    out[VARIANT_COL] = out[VARIANT_COL].fillna('')
    for col in NUM_COLS:
        out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


# ---------------------------------------------------------------- model

def build_model(X_fit: pd.DataFrame, params: dict, with_city=False):
    """Production pipeline with the new time features. Vocabulary / encoders are fitted on X_fit only."""
    cats = CAT_COLS + (['city'] if with_city else [])
    variant_words = CountVectorizer(token_pattern=r'[a-z0-9+]+', binary=True, min_df=5)
    n_words = len(variant_words.fit(X_fit[VARIANT_COL]).vocabulary_)
    pre = ColumnTransformer([
        # HistGradientBoosting accepts at most 255 categories per feature: the rarest values (by frequency in the
        # TRAINING rows only) share one "infrequent" code; a no-op when a feature has <= 255 values
        ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=np.nan,
                               encoded_missing_value=np.nan, max_categories=255), cats),
        ('num', 'passthrough', NUM_COLS),
        ('variant', variant_words, VARIANT_COL),
    ], sparse_threshold=0)
    # older at listing -> never pricier; more km -> never pricier; a dealer listing is never priced below the same car
    # from a private seller (how much above is learned, and may be ~0); market level (listing_year) unconstrained
    monotonic = ([0] * len(cats)
                 + [-1 if c in ('age_at_listing', 'km_driven') else 1 if c == DEALER_COL else 0 for c in NUM_COLS]
                 + [0] * n_words)
    reg = HistGradientBoostingRegressor(categorical_features=list(range(len(cats))), monotonic_cst=monotonic,
                                        **params)
    return TransformedTargetRegressor(regressor=Pipeline([('pre', pre), ('reg', reg)]),
                                      func=np.log, inverse_func=np.exp)


def feature_cols(with_city=False):
    return CAT_COLS + NUM_COLS + [VARIANT_COL] + (['city'] if with_city else [])


def sample_weights(train: pd.DataFrame, config: ExperimentConfig) -> np.ndarray:
    """Depends only on each training row's source - never on the holdout or on prices."""
    return np.where(train[SOURCE_COL] == CURRENT, config.current_weight, config.historical_weight).astype(float)


# ---------------------------------------------------------------- evaluation

def metrics(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    ape = np.abs(p - y) / y
    return {'rows': int(len(y)), 'mae': float(mean_absolute_error(y, p)),
            'rmse': float(mean_squared_error(y, p) ** 0.5),
            'r2': float(r2_score(y, p)) if len(y) > 1 else None,
            'median_abs_error': float(np.median(np.abs(p - y))),
            'median_pct_error': float(np.median(ape)),
            'within_10pct': float((ape <= .10).mean()), 'within_20pct': float((ape <= .20).mean()),
            'actual_range': [float(y.min()), float(y.max())], 'prediction_range': [float(p.min()), float(p.max())]}


def breakdown(frame: pd.DataFrame, key: str, min_rows: int) -> dict:
    out = {}
    for value, g in frame.groupby(key, observed=True):
        if len(g) >= min_rows:
            m = metrics(g['actual'], g['predicted'])
            out[str(value)] = {k: m[k] for k in ('rows', 'mae', 'median_pct_error', 'within_10pct', 'within_20pct')}
    return out


def evaluate(holdout: pd.DataFrame, predictions: np.ndarray, min_rows: int) -> dict:
    frame = pd.DataFrame({
        'actual': holdout['selling_price'].to_numpy(float), 'predicted': predictions,
        'price_bucket': pd.cut(holdout['selling_price'].to_numpy(float), [0, 2e5, 5e5, 10e5, 20e5, np.inf],
                               labels=['<2L', '2-5L', '5-10L', '10-20L', '>20L']),
        'age_bucket': pd.cut(holdout['age_at_listing'].to_numpy(float), [-1, 3, 6, 10, 15, np.inf],
                             labels=['0-3y', '4-6y', '7-10y', '11-15y', '>15y']),
        'company': holdout['company'].to_numpy(), 'fuel': holdout['fuel'].to_numpy(),
    })
    return {'overall': metrics(frame['actual'], frame['predicted']),
            **{f'by_{k}': breakdown(frame, k, min_rows) for k in ('price_bucket', 'company', 'age_bucket', 'fuel')}}


# ---------------------------------------------------------------- leakage audit

def leakage_audit(ctx: dict) -> dict:
    holdout, holdout_ids = ctx['holdout'], set(ctx['holdout']['listing_id'])
    checks = {}
    trains = ctx['train_frames']
    checks['current holdout never entered training'] = all(
        holdout_ids.isdisjoint(set(t['listing_id'].dropna())) for t in trains.values())
    checks['current holdout never entered spec lookup'] = holdout_ids.isdisjoint(set(ctx['lookup_ids']))
    fitted_ok = True
    for name, model in ctx['models'].items():
        pre = model.regressor_.named_steps['pre']
        train = trains[name]
        vocab = set(pre.named_transformers_['variant'].vocabulary_)
        train_tokens = set(CountVectorizer(token_pattern=r'[a-z0-9+]+').fit(train[VARIANT_COL]).vocabulary_)
        cats_seen = all(set(c[~pd.isna(c)]) <= set(train[col].dropna())
                        for col, c in zip(pre.named_transformers_['cat'].feature_names_in_,
                                          pre.named_transformers_['cat'].categories_))
        fitted_ok &= vocab <= train_tokens and cats_seen and model.regressor_.named_steps['reg'].n_features_in_ > 0
    checks['current holdout never influenced preprocessing'] = fitted_ok
    checks['current holdout never influenced hyperparameters'] = all(
        {k: m.regressor_.named_steps['reg'].get_params()[k] for k in ctx['params']} == ctx['params']
        for m in ctx['models'].values())
    checks['current holdout never influenced sample weights'] = all(
        len(w) == len(trains[name]) for name, w in ctx['weights'].items())
    checks['target price was not used for spec enrichment'] = ctx['price_invariant_enrichment']
    checks['no future listing information leaked into training'] = all(
        t.loc[t[SOURCE_COL] == CURRENT, 'listing_year'].max() <= holdout['listing_year'].min()
        if (t[SOURCE_COL] == CURRENT).any() else True for t in trains.values()) and (
        ctx['current_train_last_date'] <= ctx['holdout_first_date'])
    checks['duplicate listings did not cross train/holdout'] = set(ctx['current_train_ids']).isdisjoint(holdout_ids)
    checks['test metrics calculated only after predictions were generated'] = ctx['predictions_complete_before_metrics']
    checks['historical data contains no target leakage'] = ctx['historical_ok']
    return checks


# ---------------------------------------------------------------- run

def run(config: ExperimentConfig) -> dict:
    prod_before = {p: _file_md5(p) for p in PRODUCTION_FILES}
    historical_check = verify_historical(config)
    historical, current_train, holdout, summary, report = prepare(config)

    (hist_e, cur_train_e, holdout_e), lookup = enrich_all(historical, current_train, holdout)
    shuffled = lambda d: d.assign(selling_price=np.random.default_rng(0).permutation(d['selling_price'].to_numpy()))  # noqa: E731
    (_, _, holdout_shuffled), _ = enrich_all(shuffled(historical), shuffled(current_train), shuffled(holdout))
    price_invariant = holdout_e[SPEC_COLS].equals(holdout_shuffled[SPEC_COLS])

    hly = config.historical_listing_year
    feats = {}
    for with_city in (False, True):
        feats[with_city] = (to_features(hist_e, hly, with_city), to_features(cur_train_e, hly, with_city),
                            to_features(holdout_e, hly, with_city))

    experiments = {
        'A_historical': dict(city=False, frames=('hist',), weighted=False),
        'B_historical_current': dict(city=False, frames=('hist', 'cur'), weighted=False),
        'C_weighted': dict(city=False, frames=('hist', 'cur'), weighted=True),
    }
    city_info = None
    if config.run_city_experiment:
        counts = current_train['city'].str.strip().str.lower().value_counts()
        usable = counts[counts >= config.min_city_train_rows]
        covered = holdout['city'].str.strip().str.lower().isin(usable.index).mean()
        city_info = {'cities_with_enough_training_rows': usable.to_dict(), 'holdout_rows_in_those_cities': covered}
        if len(usable) >= 2 and covered >= 0.5:
            experiments['EXPLORATORY_B_plus_city'] = dict(city=True, frames=('hist', 'cur'), weighted=False)
        else:
            city_info['skipped'] = 'not enough city coverage (need >=2 cities with enough rows, >=50% of holdout)'

    models, train_frames, weights, predictions = {}, {}, {}, {}
    for name, spec in experiments.items():
        hist_f, cur_f, hold_f = feats[spec['city']]
        train = pd.concat([{'hist': hist_f, 'cur': cur_f}[k] for k in spec['frames']], ignore_index=True)
        w = sample_weights(train, config) if spec['weighted'] else np.ones(len(train))
        cols = feature_cols(spec['city'])
        model = build_model(train[cols], config.model_params, spec['city'])
        model.fit(train[cols], train['selling_price'].to_numpy(float), reg__sample_weight=w)
        models[name], train_frames[name], weights[name] = model, train, w
        predictions[name] = model.predict(hold_f[cols])
    predictions_complete = len(predictions) == len(experiments)

    audit = leakage_audit({
        'holdout': feats[False][2], 'train_frames': train_frames, 'models': models, 'weights': weights,
        'lookup_ids': pd.concat([historical, current_train], sort=False)['listing_id'].dropna(),
        'params': {k: v for k, v in config.model_params.items()},
        'price_invariant_enrichment': price_invariant,
        # selling_price identical to the original, and mileage = documented rules (which never read the price)
        'historical_ok': historical_check['cleaned'] is False or (
            historical_check['non_mileage_columns_identical'] and historical_check['matches_cleaning_rules']),
        'current_train_last_date': current_train['listing_date'].max(),
        'holdout_first_date': holdout['listing_date'].min(),
        'current_train_ids': current_train['listing_id'],
        'predictions_complete_before_metrics': predictions_complete,
    })
    if not all(audit.values()):
        failed = [k for k, v in audit.items() if not v]
        raise ExperimentDataError(f'leakage audit failed - no results written: {failed}')

    hold_f = feats[False][2]
    results = {name: evaluate(hold_f, predictions[name], config.min_group_rows) for name in experiments}

    prod_after = {p: _file_md5(p) for p in PRODUCTION_FILES}
    if prod_after != prod_before:
        raise ExperimentDataError('production artifacts changed during the experiment')

    os.makedirs(config.output_dir, exist_ok=True)
    for name, model in models.items():
        joblib.dump(model, os.path.join(config.output_dir, f'model_{name}.joblib'))
    output = {
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'config': asdict(config),
        'data': {'historical_rows': len(historical), 'current': summary, 'split': {
            'current_training_rows': len(current_train), 'current_holdout_rows': len(holdout),
            'current_training_last_date': str(current_train['listing_date'].max().date()),
            'holdout_first_date': str(holdout['listing_date'].min().date()),
            'holdout_last_date': str(holdout['listing_date'].max().date())}},
        'spec_coverage': {'historical': spec_coverage(hist_e), 'current_training': spec_coverage(cur_train_e),
                          'current_holdout': spec_coverage(holdout_e)},
        'training_rows': {n: len(t) for n, t in train_frames.items()},
        'city_experiment': city_info,
        'historical_dataset': historical_check,
        'gas_mileage_coverage': {
            'historical': gas_mileage_coverage(historical),
            'missing_mileage_in_training': {n: int(t['mileage_mpg'].isna().sum()) for n, t in train_frames.items()},
            'pipeline': 'trained and predicted with missing mileage left as NaN (handled natively, not filled)'},
        'leakage_audit': audit,
        'results': results,
        'production_checksums_unchanged': prod_before,
    }
    with open(os.path.join(config.output_dir, 'experiment_config.json'), 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2)
    with open(os.path.join(config.output_dir, 'experiment_results.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)
    with open(os.path.join(config.output_dir, 'experiment_report.md'), 'w', encoding='utf-8') as f:
        f.write(render_report(output))
    return output


def render_report(o: dict) -> str:
    cfg, d = o['config'], o['data']
    lines = ['# Current-market experiment', '',
             f"Created {o['created_at']}. Offline only - production model unchanged.", '',
             '## Data', f"- Historical rows: {d['historical_rows']:,} (listing year {cfg['historical_listing_year']}"
             + (')' if cfg['historical_listing_year_confirmed'] else ' - UNCONFIRMED ASSUMPTION)'),
             f"- Historical dataset: `{cfg['historical_path']}`",
             f"- Current rows: {d['current']['valid_rows']:,} valid / {d['current']['total_rows']:,} "
             f"({d['current']['listing_date_range'][0]} to {d['current']['listing_date_range'][1]})",
             f"- Current training: {d['split']['current_training_rows']:,} (up to {d['split']['current_training_last_date']})",
             f"- Current holdout: {d['split']['current_holdout_rows']:,} "
             f"({d['split']['holdout_first_date']} to {d['split']['holdout_last_date']})", '',
             '## Results on the current holdout', '',
             '| Experiment | Training rows | MAE | RMSE | R² | Median abs error | Median % error | ±10% | ±20% |',
             '|---|---|---|---|---|---|---|---|---|']
    for name, r in o['results'].items():
        m = r['overall']
        r2 = 'n/a' if m['r2'] is None else f"{m['r2']:.4f}"
        lines.append(f"| {name} | {o['training_rows'][name]:,} | ₹{m['mae']:,.0f} | ₹{m['rmse']:,.0f} | {r2} | "
                     f"₹{m['median_abs_error']:,.0f} | {m['median_pct_error']:.1%} | {m['within_10pct']:.1%} | "
                     f"{m['within_20pct']:.1%} |")
    lines += ['', 'EXPLORATORY_* rows are a separate experiment, not part of the A/B/C comparison.', '',
              '## Leakage audit'] + [f"- {'PASS' if v else 'FAIL'}: {k}" for k, v in o['leakage_audit'].items()]
    for name, r in o['results'].items():
        lines += ['', f'## Breakdown - {name}']
        for key in ('by_price_bucket', 'by_company', 'by_age_bucket', 'by_fuel'):
            if r[key]:
                lines.append(f"**{key[3:]}**: " + '; '.join(
                    f"{g} (n={v['rows']}): median {v['median_pct_error']:.1%}, ±20% {v['within_20pct']:.0%}"
                    for g, v in r[key].items()))
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--holdout', type=float, default=0.2)
    ap.add_argument('--current-weight', type=float, default=2.0)
    ap.add_argument('--historical-listing-year', type=int, default=2020)
    ap.add_argument('--historical-path', default=DATA_FILE_PATH,
                    help='e.g. data/car-details-cleaned.csv (verified against the original before use)')
    ap.add_argument('--with-city', action='store_true')
    ap.add_argument('--allow-invalid-rows', action='store_true')
    a = ap.parse_args()
    config = ExperimentConfig(holdout_fraction=a.holdout, current_weight=a.current_weight,
                              historical_listing_year=a.historical_listing_year, run_city_experiment=a.with_city,
                              allow_invalid_rows=a.allow_invalid_rows, historical_path=a.historical_path)
    try:
        output = run(config)
    except ExperimentDataError as e:
        print(f'EXPERIMENT STOPPED: {e}')
        raise SystemExit(2)
    print(render_report(output))
    print(f'Artifacts written to {config.output_dir}/')


if __name__ == '__main__':
    main()
