import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from training.clean_historical_data import (
    CNG_LPG_TO_MISSING, MILEAGE, ZERO_TO_MISSING, clean, run,
)
from training.train_utils import DATA_FILE_PATH

OTHER_COLS = ['name', 'company', 'model', 'edition', 'year', 'owner', 'fuel', 'seller_type', 'transmission',
              'km_driven', 'engine_cc', 'max_power_bhp', 'torque_nm', 'seats', 'selling_price']


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


@pytest.fixture(scope='module')
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp('clean')
    before = md5(DATA_FILE_PATH)
    report = run(cleaned_path=str(out / 'cleaned.csv'), log_path=str(out / 'log.csv'),
                 report_path=str(out / 'report.json'))
    return dict(out=out, report=report, md5_before=before, original=pd.read_csv(DATA_FILE_PATH),
                cleaned=pd.read_csv(out / 'cleaned.csv'), log=pd.read_csv(out / 'log.csv'))


def test_original_file_never_overwritten(result):
    assert md5(DATA_FILE_PATH) == result['md5_before'] == result['report']['source_md5']


def test_refuses_to_write_over_the_original(tmp_path):
    with pytest.raises(ValueError, match='overwrite'):
        run(cleaned_path=DATA_FILE_PATH, log_path=str(tmp_path / 'l.csv'), report_path=str(tmp_path / 'r.json'))


def test_row_count_and_columns_preserved(result):
    assert len(result['cleaned']) == len(result['original']) == result['report']['cleaned_rows']
    assert list(result['cleaned'].columns) == list(result['original'].columns)


def test_no_other_feature_modified(result):
    pd.testing.assert_frame_equal(result['cleaned'][OTHER_COLS], result['original'][OTHER_COLS])


def test_selling_price_never_modified(result):
    assert (result['cleaned']['selling_price'] == result['original']['selling_price']).all()


def test_valid_petrol_diesel_mileage_unchanged(result):
    o, c = result['original'], result['cleaned']
    keep = o.fuel.isin(['Petrol', 'Diesel']) & (o[MILEAGE] > 0)
    assert keep.sum() == 6616
    assert (c.loc[keep, MILEAGE] == o.loc[keep, MILEAGE]).all()


def test_zero_mileage_becomes_missing(result):
    o, c = result['original'], result['cleaned']
    zero = o.fuel.isin(['Petrol', 'Diesel']) & (o[MILEAGE] == 0)
    assert zero.sum() == 15 and c.loc[zero, MILEAGE].isna().all()


def test_cng_lpg_not_guessed(result):
    o, c = result['original'], result['cleaned']
    gas = o.fuel.isin(['CNG', 'LPG'])
    assert c.loc[gas, MILEAGE].isna().all()


def test_no_value_is_ever_invented(result):
    o, c = result['original'], result['cleaned']
    has_value = c[MILEAGE].notna()
    assert o.loc[has_value, MILEAGE].notna().all()
    assert (c.loc[has_value, MILEAGE] == o.loc[has_value, MILEAGE]).all()
    assert result['report']['corrected_to_new_value'] == 0


def test_every_change_is_logged(result):
    o, c, log = result['original'], result['cleaned'], result['log']
    changed = ~((o[MILEAGE] == c[MILEAGE]) | (o[MILEAGE].isna() & c[MILEAGE].isna()))
    assert len(log) == changed.sum() == result['report']['mileage_values_changed'] == 102
    assert set(log['rule']) == {ZERO_TO_MISSING, CNG_LPG_TO_MISSING}
    assert (o.loc[log['csv_line'] - 2, MILEAGE].to_numpy() == log['original_mileage_mpg'].to_numpy()).all()


def test_cleaning_is_deterministic(result, tmp_path):
    run(cleaned_path=str(tmp_path / 'c.csv'), log_path=str(tmp_path / 'l.csv'), report_path=str(tmp_path / 'r.json'))
    assert md5(tmp_path / 'c.csv') == md5(result['out'] / 'cleaned.csv')
    assert md5(tmp_path / 'l.csv') == md5(result['out'] / 'log.csv')


def test_rules_on_small_frame():
    frame = pd.DataFrame({
        'name': ['a', 'b', 'c', 'd', 'e'], 'company': 'X', 'model': 'Y', 'edition': 'Z', 'year': 2015,
        'fuel': ['Petrol', 'Diesel', 'CNG', 'LPG', 'Petrol'], MILEAGE: [44.4, 0.0, 0.04, np.nan, np.nan],
    })
    cleaned, log = clean(frame)
    assert cleaned[MILEAGE].tolist()[0] == 44.4
    assert cleaned[MILEAGE].iloc[1:].isna().all()
    assert log['rule'].tolist() == [ZERO_TO_MISSING, CNG_LPG_TO_MISSING]  # already-missing values not logged


def test_report_before_after(result):
    r = result['report']
    assert r['before']['CNG']['suspicious'] == 52 and r['after']['CNG']['suspicious'] == 0
    assert all(stats['suspicious'] == 0 for stats in r['after'].values())
    json.dumps(r)  # serialisable
