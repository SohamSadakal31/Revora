import os

import pandas as pd

from training.data_loading import CURRENT_OPTIONAL_COLS, CURRENT_REQUIRED_COLS, load_current
from training.validate_current_listings import main as validate

TEMPLATE = os.path.join('data', 'current-listings.template.csv')
EXPECTED_HEADER = ('company,model,edition,year,owner,fuel,seller_type,transmission,km_driven,mileage_mpg,engine_cc,'
                   'max_power_bhp,torque_nm,seats,selling_price,city,listing_date,listing_id')
HEADER = EXPECTED_HEADER
ROWS = [  # test-only rows, written to pytest's tmp_path
    'Maruti,Wagon,R LXI CNG,2019,First,CNG,Dealer,Manual,80214,,,,,,368000,Delhi,2026-09-01,A1',
    'Maruti,SX4,Vxi,2012,Third,Petrol,Individual,Manual,141558,,1586,,,5,102000,Delhi,2026-08-15,A2',
]


def write(tmp_path, rows, header=HEADER):
    path = tmp_path / 'current-listings.csv'
    path.write_text('\n'.join([header] + rows) + '\n', encoding='utf-8')
    return str(path)


def test_template_has_exact_header_and_no_data():
    with open(TEMPLATE, encoding='utf-8') as f:
        lines = f.read().splitlines()
    assert lines == [EXPECTED_HEADER]
    assert set(CURRENT_REQUIRED_COLS + CURRENT_OPTIONAL_COLS) <= set(EXPECTED_HEADER.split(','))


def test_template_is_accepted_by_the_loader():
    current, report = load_current(TEMPLATE)
    assert report.total_rows == 0 and report.invalid_count == 0 and len(current) == 0


def test_source_listing_id_kept_not_overwritten(tmp_path):
    current, report = load_current(write(tmp_path, ROWS))
    assert report.invalid_count == 0
    assert current['source_listing_id'].tolist() == ['A1', 'A2']
    assert current['listing_id'].str.len().eq(12).all()  # internal repeated-car key still present
    assert current.loc[current.source_listing_id == 'A1', 'engine_cc'].isna().all()  # blank spec stays missing


def test_duplicate_and_blank_listing_ids_are_invalid(tmp_path):
    rows = ROWS + [ROWS[0].replace('80214', '90000'), ROWS[1].rsplit(',', 1)[0] + ',']
    _, report = load_current(write(tmp_path, rows))
    errors = report.invalid_rows.set_index('row_number')['errors']
    assert 'listing_id is duplicated' in errors[2] and 'listing_id is duplicated' in errors[4]
    assert 'listing_id is empty' in errors[5]
    assert report.valid_rows == 1


def test_validate_command_missing_file(tmp_path, capsys):
    assert validate(['--path', str(tmp_path / 'absent.csv')]) == 2
    assert 'NOT FOUND' in capsys.readouterr().out


def test_validate_command_valid_file(tmp_path, capsys):
    assert validate(['--path', write(tmp_path, ROWS)]) == 0
    out = capsys.readouterr().out
    assert 'Valid rows            : 2' in out and 'Unique cities         : 1' in out
    assert '2026-08-15 to 2026-09-01' in out and 'all rows valid' in out


def test_validate_command_reports_invalid_rows(tmp_path, capsys):
    assert validate(['--path', write(tmp_path, ROWS + [ROWS[1].replace('102000', '-5').replace('A2', 'A3')])]) == 1
    out = capsys.readouterr().out
    assert 'Invalid rows          : 1' in out and 'selling_price must be positive' in out


def test_validate_command_missing_columns(tmp_path, capsys):
    header = HEADER.replace(',city', '')
    rows = [r.replace(',Delhi', '') for r in ROWS]
    assert validate(['--path', write(tmp_path, rows, header)]) == 2
    assert 'missing required columns' in capsys.readouterr().out


def test_validate_command_on_template(capsys):
    assert validate(['--path', TEMPLATE]) == 0
    assert 'Total rows            : 0' in capsys.readouterr().out
