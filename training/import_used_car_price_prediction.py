"""Converter for the public 'Used Car Price Prediction' dataset (Kaggle) - used by training.build_current_listings.

Source  : https://www.kaggle.com/datasets/vrajesh0sharma7/used-car-price-prediction  (Used_Car_Price_Prediction.csv)
Licence : CC0: Public Domain
Dates   : each listing's own `ad_created_on` (2019-2021)

Only reformatting - nothing is estimated or filled:
* names: "<brand> <model> <variant>" split by the historical rule (1st word company, 2nd model, rest edition);
  the only brand respelling is 'mercedes benz' -> 'Mercedes-Benz' (historical spelling)
* owner: total_owners 1/2/3 -> First/Second/Third, 4+ -> Fourth & Above
* fuel: 'petrol & cng' -> CNG, 'petrol & lpg' -> LPG (the historical convention for bi-fuel cars)
* seller_type (DECISION, documented): source 'inperson_sale' / 'online' = the platform selling its own stock -> Dealer;
  'customer_to_customer' -> Individual
* the source has no specs and no listing id: specs stay blank; listing_id = 'uccp-<source line number>' (provenance)
* rows that cannot be represented without guessing are excluded with the reason
"""
import numpy as np
import pandas as pd

KAGGLE_ID = 'vrajesh0sharma7/used-car-price-prediction'
SOURCE_FILE = 'Used_Car_Price_Prediction.csv'
SOURCE_URL = f'https://www.kaggle.com/datasets/{KAGGLE_ID}'
LICENCE = 'CC0: Public Domain'

BRAND_SPELLING = {'mercedes benz': 'Mercedes-Benz'}
FUEL = {'petrol': 'Petrol', 'diesel': 'Diesel', 'petrol & cng': 'CNG', 'petrol & lpg': 'LPG'}
SELLER = {'inperson_sale': 'Dealer', 'online': 'Dealer', 'customer_to_customer': 'Individual'}


def owner_label(n):
    if pd.isna(n) or n < 1:
        return np.nan
    return {1: 'First', 2: 'Second', 3: 'Third'}.get(int(n), 'Fourth & Above')


def convert(raw: pd.DataFrame):
    brand = raw['make'].str.strip().map(lambda b: BRAND_SPELLING.get(b, b))
    full_name = (brand + ' ' + raw['model'].str.strip() + ' ' + raw['variant'].fillna('').str.strip()).str.strip()
    parts = full_name.str.split(' ', n=2)
    dates = pd.to_datetime(raw['ad_created_on'], errors='coerce')
    out = pd.DataFrame({
        'company': parts.str[0], 'model': parts.str[1], 'edition': parts.str[2].fillna(''),
        'year': raw['yr_mfr'],
        'owner': raw['total_owners'].map(owner_label),
        'fuel': raw['fuel_type'].str.strip().map(FUEL),
        'seller_type': raw['source'].map(SELLER),
        'transmission': raw['transmission'].str.strip().str.capitalize(),
        'km_driven': raw['kms_run'],
        'mileage_mpg': np.nan, 'engine_cc': np.nan, 'max_power_bhp': np.nan, 'torque_nm': np.nan, 'seats': np.nan,
        'selling_price': raw['sale_price'],
        'city': raw['city'].str.strip(),
        'listing_date': dates.dt.strftime('%Y-%m-%d'),
        'listing_id': 'uccp-' + (raw.index + 2).astype(str),  # line in the source CSV
    })

    checks = [
        (raw['fuel_type'].str.strip() == 'electric', 'electric fuel is not an accepted value'),
        (out['fuel'].isna() & (raw['fuel_type'].str.strip() != 'electric'), 'unknown fuel'),
        (out['transmission'].isna(), 'transmission missing in source'),
        (out['seller_type'].isna(), 'source (seller type) missing in source'),
        (out['owner'].isna(), 'total_owners missing or 0'),
        (dates.isna(), 'ad_created_on missing or not a date'),
        (~(raw['sale_price'] > 0), 'sale_price is 0 or missing (not a listed price)'),
    ]
    reasons = pd.Series('', index=raw.index)
    for mask, reason in checks:
        reasons[mask.fillna(False).astype(bool)] += reason + '; '
    bad = reasons != ''
    excluded = pd.DataFrame({'source_id': 'line ' + (raw.index[bad] + 2).astype(str),
                             'vehicle': full_name[bad], 'reason': reasons[bad].str.rstrip('; ')})
    return out.loc[~bad], excluded

