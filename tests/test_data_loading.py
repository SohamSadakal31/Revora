from datetime import date

import pandas as pd
import pytest

from training.data_loading import (
    CURRENT, HISTORICAL, SOURCE_COL, CurrentDataError, dataset_statistics, load_current, load_historical,
    load_training_data, split_current_holdout,
)
from training.train_utils import DATA_FILE_PATH

TODAY = date(2026, 9, 30)
HEADER = ('company,model,edition,year,km_driven,fuel,transmission,owner,seller_type,selling_price,'
          'city,listing_date')
GOOD_ROWS = [
    'Maruti,Wagon,R LXI CNG,2019,80214,CNG,Manual,First,Dealer,368000,Delhi,2026-09-01',
    'Maruti,SX4,Vxi,2012,141558,Petrol,Manual,Third,Individual,102000,Delhi,2026-08-15',
    'Hyundai,i20,Asta,2021,30000,Petrol,Manual,First,Dealer,720000,Mumbai,2026-07-20',
]


def write_csv(tmp_path, lines, header=HEADER):
    path = tmp_path / 'current-listings.csv'
    path.write_text('\n'.join([header] + lines) + '\n', encoding='utf-8')
    return str(path)


def load(tmp_path, lines, header=HEADER):
    return load_current(write_csv(tmp_path, lines, header), today=TODAY)


# ---- historical only ----

def test_historical_loading_matches_previous_training_input():
    legacy = pd.read_csv(DATA_FILE_PATH).drop_duplicates()
    historical = load_historical()
    pd.testing.assert_frame_equal(historical.drop(columns=SOURCE_COL), legacy)
    assert (historical[SOURCE_COL] == HISTORICAL).all()


def test_missing_current_file_means_historical_only(tmp_path):
    combined, historical, current, report = load_training_data(current_path=str(tmp_path / 'absent.csv'))
    assert current is None and report is None
    assert len(combined) == len(historical)
    assert 'Current rows: 0' in dataset_statistics(historical, current)


# ---- valid current data ----

def test_valid_current_listings(tmp_path):
    current, report = load(tmp_path, GOOD_ROWS)
    assert report.total_rows == 3 and report.valid_rows == 3 and report.invalid_count == 0
    assert (current[SOURCE_COL] == CURRENT).all()
    assert pd.api.types.is_datetime64_any_dtype(current['listing_date'])
    assert current['mileage_mpg'].isna().all()  # optional spec columns become empty, not invented
    assert any('mileage_mpg' in w for w in report.warnings)


def test_brand_column_accepted_as_company(tmp_path):
    current, report = load(tmp_path, GOOD_ROWS, header=HEADER.replace('company', 'brand'))
    assert report.valid_rows == 3 and 'company' in current.columns


# ---- invalid data ----

def test_missing_required_columns_rejected(tmp_path):
    header = HEADER.replace(',city', '').replace(',listing_date', '')
    rows = [r.rsplit(',', 2)[0] for r in GOOD_ROWS]
    with pytest.raises(CurrentDataError, match="city.*listing_date"):
        load(tmp_path, rows, header)


@pytest.mark.parametrize('row, reason', [
    ('Maruti,Swift,VXI,twenty,50000,Petrol,Manual,First,Dealer,500000,Pune,2026-01-01', 'year is not a number'),
    ('Maruti,Swift,VXI,2018,-5,Petrol,Manual,First,Dealer,500000,Pune,2026-01-01', 'km_driven is negative'),
    ('Maruti,Swift,VXI,2018,50000,Petrol,Manual,First,Dealer,0,Pune,2026-01-01', 'selling_price must be positive'),
    ('Maruti,Swift,VXI,2018,50000,Petrol,Manual,First,Dealer,abc,Pune,2026-01-01', 'selling_price is not a number'),
    ('Maruti,Swift,VXI,2018,,Petrol,Manual,First,Dealer,500000,Pune,2026-01-01', 'km_driven is missing'),
    ('Maruti,Swift,VXI,1950,50000,Petrol,Manual,First,Dealer,500000,Pune,2026-01-01', 'year must be'),
    ('Maruti,Swift,VXI,2026,50000,Petrol,Manual,First,Dealer,500000,Pune,2025-05-01', 'year is after the listing'),
    ('Maruti,Swift,VXI,2018,50000,Electric,Manual,First,Dealer,500000,Pune,2026-01-01', 'fuel must be one of'),
    ('Maruti,Swift,VXI,2018,50000,Petrol,Manual,First,Dealer,500000,,2026-01-01', 'city is empty'),
])
def test_invalid_rows_reported_not_silently_dropped(tmp_path, row, reason):
    current, report = load(tmp_path, GOOD_ROWS + [row])
    assert report.valid_rows == 3 and report.invalid_count == 1
    assert reason in report.invalid_rows.iloc[0]['errors']
    assert report.invalid_rows.iloc[0]['row_number'] == 5  # line in the CSV, header is line 1
    assert reason in report.summary()


@pytest.mark.parametrize('bad_date', ['31/02/2026', 'yesterday', '2026-13-01', '', '2027-01-01'])
def test_invalid_dates_reported(tmp_path, bad_date):
    row = f'Maruti,Swift,VXI,2018,50000,Petrol,Manual,First,Dealer,500000,Pune,{bad_date}'
    _, report = load(tmp_path, GOOD_ROWS + [row])
    assert report.invalid_count == 1
    assert 'listing_date' in report.invalid_rows.iloc[0]['errors']


def test_multiple_problems_listed_together(tmp_path):
    row = 'Maruti,Swift,VXI,1950,-1,Petrol,Manual,First,Dealer,-3,Pune,not-a-date'
    _, report = load(tmp_path, GOOD_ROWS + [row])
    assert report.invalid_rows.iloc[0]['errors'].count(';') >= 3


# ---- combined + leakage ----

def test_combined_keeps_sources_distinguishable(tmp_path):
    path = write_csv(tmp_path, GOOD_ROWS)
    combined, historical, current, report = load_training_data(current_path=path, today=TODAY)
    assert len(combined) == len(historical) + 3
    assert combined[SOURCE_COL].value_counts().to_dict() == {HISTORICAL: len(historical), CURRENT: 3}
    stats = dataset_statistics(historical, current)
    assert 'Current rows: 3' in stats and '2026-07-20 to 2026-09-01' in stats and 'Delhi (2)' in stats


def test_holdout_is_most_recent_and_never_shares_a_listing(tmp_path):
    rows = [f'Maruti,Swift,VXI,2018,{40000 + i},Petrol,Manual,First,Dealer,{500000 + i},Pune,2026-0{1 + i % 9}-10'
            for i in range(20)]
    rows.append(rows[-1].replace('2026-02-10', '2026-02-11').replace('500019', '505000'))  # re-listed car
    current, _ = load(tmp_path, rows)
    train, holdout = split_current_holdout(current, holdout_fraction=0.25)
    assert set(train['listing_id']).isdisjoint(set(holdout['listing_id']))
    assert len(train) + len(holdout) == len(current)
    assert holdout['listing_date'].min() >= train['listing_date'].max()
    relisted = current[current['listing_id'].duplicated(keep=False)]['listing_id'].iloc[0]
    assert (relisted in set(train['listing_id'])) != (relisted in set(holdout['listing_id']))
