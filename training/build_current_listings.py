"""Build data/current-listings.csv from legal public datasets (downloaded with Kaggle's official client - no scraping).

    pip install kagglehub
    python -m training.build_current_listings [--force]

Only datasets whose licence allows commercial (production) use are included. Each row keeps its provenance in the
`data_source` and `licence` columns.

Datasets reviewed and NOT used (see data/current-listings-sources.md): generated/synthetic values, required fields
missing (city, seller type, date), licence unknown, or non-commercial licence.
"""
import argparse
import json
import os

import pandas as pd

from training import import_cardekho_vehicle_v4, import_used_car_price_prediction
from training.train_utils import CURRENT_DATA_FILE_PATH, DATA_DIR

SOURCES = [import_used_car_price_prediction, import_cardekho_vehicle_v4]  # only licences allowing commercial use
HEADER = ['company', 'model', 'edition', 'year', 'owner', 'fuel', 'seller_type', 'transmission', 'km_driven',
          'mileage_mpg', 'engine_cc', 'max_power_bhp', 'torque_nm', 'seats', 'selling_price', 'city',
          'listing_date', 'listing_id', 'data_source', 'licence']
REPORT_PATH = os.path.join(DATA_DIR, 'current-listings-import-report.json')
EXCLUDED_PATH = os.path.join(DATA_DIR, 'current-listings-import-excluded.csv')


def download(kaggle_id: str, filename: str) -> str:
    import kagglehub
    folder = kagglehub.dataset_download(kaggle_id)
    for root, _, files in os.walk(folder):
        if filename in files:
            return os.path.join(root, filename)
    raise FileNotFoundError(f'{filename} not found in {kaggle_id}')


def build(paths: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rows, excluded, report = [], [], {'sources': {}}
    for module in SOURCES:
        raw = pd.read_csv(paths[module.KAGGLE_ID], low_memory=False)
        kept, dropped = module.convert(raw)
        kept = kept.assign(data_source=module.SOURCE_URL, licence=module.LICENCE)[HEADER]
        rows.append(kept)
        excluded.append(dropped.assign(data_source=module.SOURCE_URL))
        report['sources'][module.SOURCE_URL] = {
            'licence': module.LICENCE, 'source_rows': len(raw), 'written_rows': len(kept),
            'excluded_rows': len(dropped),
            'excluded_by_reason': dropped['reason'].str.split('; ').explode().value_counts().to_dict(),
            'listing_date_range': [kept['listing_date'].min(), kept['listing_date'].max()],
        }
    combined = pd.concat(rows, ignore_index=True)
    report['total_rows'] = len(combined)
    report['rows_by_licence'] = combined['licence'].value_counts().to_dict()
    return combined, pd.concat(excluded, ignore_index=True), report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--force', action='store_true', help='replace an existing data/current-listings.csv')
    a = ap.parse_args()
    if os.path.exists(CURRENT_DATA_FILE_PATH) and not a.force:
        raise SystemExit(f'{CURRENT_DATA_FILE_PATH} exists - use --force to rebuild it')
    paths = {m.KAGGLE_ID: download(m.KAGGLE_ID, m.SOURCE_FILE) for m in SOURCES}
    combined, excluded, report = build(paths)
    combined.to_csv(CURRENT_DATA_FILE_PATH, index=False)
    excluded.to_csv(EXCLUDED_PATH, index=False)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
