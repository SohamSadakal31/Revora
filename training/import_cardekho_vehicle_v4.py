"""Converter for `car details v4.csv` from the public "Vehicle dataset" (Kaggle) - used by training.build_current_listings.

Source  : https://www.kaggle.com/datasets/nehalbirla/vehicle-dataset-from-cardekho  (car details v4.csv)
Licence : ODbL v1.0 (database) / DbCL v1.0 (contents) - the same dataset as the historical data; attribution required
Date    : 2023-01-14 for every row - the dataset's documented update date ("Data Update 2023/01/14"); the file has no
          per-listing dates and contains cars up to 2022

Mainly private-seller listings (1,997 of 2,059), which the other current source almost entirely lacks.

Only reformatting - nothing is estimated or filled:
* names: "<make> <model text>" split by the historical rule (1st word company, 2nd model, rest edition);
  'Maruti Suzuki' is written 'Maruti' (historical spelling)
* specs only when stated with a unit ('87 bhp @ 6000 rpm', '109 Nm @ 4500 rpm', '1198 cc'); unit-less values such as
  '88@4000' stay blank; the file has no fuel-economy figure, so mileage stays blank
* owner: Fourth / '4 or More' -> Fourth & Above; fuel: 'Petrol + CNG' / 'CNG + CNG' -> CNG, 'Petrol + LPG' -> LPG
* excluded with the reason: electric / hybrid, 'UnRegistered Car' owner, seller types 'Corporate' and
  'Commercial Registration' (no clear equivalent)
"""
import re

import numpy as np
import pandas as pd

KAGGLE_ID = 'nehalbirla/vehicle-dataset-from-cardekho'
SOURCE_FILE = 'car details v4.csv'
SOURCE_URL = f'https://www.kaggle.com/datasets/{KAGGLE_ID}'
LICENCE = 'ODbL v1.0 / DbCL v1.0'
SNAPSHOT_DATE = '2023-01-14'
ID_PREFIX = 'v4-'

BRAND_SPELLING = {'Maruti Suzuki': 'Maruti'}
FUEL = {'Petrol': 'Petrol', 'Diesel': 'Diesel', 'CNG': 'CNG', 'LPG': 'LPG',
        'Petrol + CNG': 'CNG', 'CNG + CNG': 'CNG', 'Petrol + LPG': 'LPG'}
OWNER = {'First': 'First', 'Second': 'Second', 'Third': 'Third', 'Fourth': 'Fourth & Above',
         '4 or More': 'Fourth & Above'}
SELLER = {'Individual': 'Individual'}
NUMBER = r'(\d+(?:\.\d+)?)'


def _stated(text, unit: str) -> float:
    """Number followed by the given unit, else NaN (never assumes a unit)."""
    if not isinstance(text, str):
        return np.nan
    m = re.match(rf'\s*{NUMBER}\s*{unit}\b', text.replace(',', ''), re.I)
    return float(m.group(1)) if m else np.nan


def convert(raw: pd.DataFrame):
    make = raw['Make'].str.strip().map(lambda b: BRAND_SPELLING.get(b, b))
    full_name = (make + ' ' + raw['Model'].astype(str).str.strip()).str.strip()
    parts = full_name.str.split(' ', n=2)
    fuel = raw['Fuel Type'].str.strip().map(FUEL)
    out = pd.DataFrame({
        'company': parts.str[0], 'model': parts.str[1], 'edition': parts.str[2].fillna(''),
        'year': raw['Year'],
        'owner': raw['Owner'].str.strip().map(OWNER),
        'fuel': fuel,
        'seller_type': raw['Seller Type'].str.strip().map(SELLER),
        'transmission': raw['Transmission'].str.strip().str.capitalize(),
        'km_driven': raw['Kilometer'],
        'mileage_mpg': np.nan,
        'engine_cc': raw['Engine'].map(lambda t: _stated(t, 'cc')),
        'max_power_bhp': raw['Max Power'].map(lambda t: _stated(t, 'bhp')),
        'torque_nm': raw['Max Torque'].map(lambda t: _stated(t, 'nm')),
        'seats': pd.to_numeric(raw['Seating Capacity'], errors='coerce'),
        'selling_price': raw['Price'],
        'city': raw['Location'].str.strip(),
        'listing_date': SNAPSHOT_DATE,
        'listing_id': ID_PREFIX + (raw.index + 2).astype(str),  # line in the source CSV
    })
    checks = [
        (raw['Fuel Type'].str.strip().isin(['Electric', 'Hybrid']), 'electric / hybrid fuel is not an accepted value'),
        (fuel.isna() & ~raw['Fuel Type'].str.strip().isin(['Electric', 'Hybrid']), 'unknown fuel'),
        (out['owner'].isna(), 'owner has no equivalent (e.g. UnRegistered Car)'),
        (out['seller_type'].isna(), 'seller type has no equivalent (Corporate / Commercial Registration)'),
        (~(raw['Price'] > 0), 'price is 0 or missing'),
    ]
    reasons = pd.Series('', index=raw.index)
    for mask, reason in checks:
        reasons[mask.fillna(False).astype(bool)] += reason + '; '
    bad = reasons != ''
    excluded = pd.DataFrame({'source_id': 'line ' + (raw.index[bad] + 2).astype(str),
                             'vehicle': full_name[bad], 'reason': reasons[bad].str.rstrip('; ')})
    return out.loc[~bad], excluded
