"""Reproducible mileage clean-up of the historical data - writes a SEPARATE cleaned file.

    python -m training.clean_historical_data

Reads   data/car-details.csv                  (never modified)
Writes  data/car-details-cleaned.csv          (same rows and columns; only mileage_mpg can differ)
        data/car-details-cleaning-log.csv     (one line per changed value: CSV line, vehicle, old, new, rule)
        data/car-details-cleaning-report.json (before / after counts per fuel)

Only mileage_mpg is touched, and no value is ever invented - a value is either kept or set to missing:

  KEEP_PLAUSIBLE  petrol / diesel values > 0 are kept. They are rated km/l x ~2.35 (mpg), rounded to 1-2 decimals
                  (so the exact factor cannot be recovered), and spot checks match published ratings, e.g. Swift
                  Dzire VDI 55.0 / 62.5 / 66.75 -> 23.4 / 26.6 / 28.4 km/l for its successive generations. All imply
                  5-45 km/l; a value outside that range would be reported as suspicious (none are).
  ZERO_TO_MISSING petrol / diesel values of 0 become missing: 0 is not a fuel-economy figure, and none of these
                  vehicles has a non-zero value for the same variant (any year) in the data to take instead.
  CNG_LPG_TO_MISSING all CNG / LPG values become missing: they sit around 0.017-0.054, no transformation turns
                  them into plausible km/kg figures, and the repository has no raw values to verify a conversion.
Anything else (already-missing values, other fuels) is left exactly as it is.
"""
import argparse
import hashlib
import json
import os

import numpy as np
import pandas as pd

from training.train_utils import DATA_DIR, DATA_FILE_PATH

CLEANED_PATH = os.path.join(DATA_DIR, 'car-details-cleaned.csv')
LOG_PATH = os.path.join(DATA_DIR, 'car-details-cleaning-log.csv')
REPORT_PATH = os.path.join(DATA_DIR, 'car-details-cleaning-report.json')

MILEAGE = 'mileage_mpg'
KM_PER_LITRE_TO_MPG = 2.352
LIQUID_FUELS = {'Petrol', 'Diesel'}
GAS_FUELS = {'CNG', 'LPG'}

KEEP_PLAUSIBLE = 'KEEP_PLAUSIBLE'
PLAUSIBLE_KM_PER_LITRE = (5, 45)  # widest realistic range (the Volvo XC90 T8 plug-in hybrid is rated ~42)
ZERO_TO_MISSING = 'ZERO_TO_MISSING'
CNG_LPG_TO_MISSING = 'CNG_LPG_TO_MISSING'


def _md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def is_plausible_liquid_mileage(values: pd.Series) -> pd.Series:
    """Implied km/l (mpg / 2.352) within a realistic range. Plausibility only - values are kept either way."""
    km_per_litre = values / KM_PER_LITRE_TO_MPG
    return km_per_litre.between(*PLAUSIBLE_KM_PER_LITRE)


def fuel_stats(df: pd.DataFrame) -> dict:
    out = {}
    for fuel, g in df.groupby('fuel'):
        v = g[MILEAGE]
        if fuel in LIQUID_FUELS:
            suspicious = (v == 0) | (v.notna() & (v != 0) & ~is_plausible_liquid_mileage(v))
        elif fuel in GAS_FUELS:
            suspicious = v.notna()
        else:
            suspicious = pd.Series(False, index=v.index)
        out[fuel] = {
            'rows': int(len(g)), 'missing': int(v.isna().sum()), 'zero': int((v == 0).sum()),
            'coverage': round(float(v.notna().mean()), 4),
            'min': None if v.dropna().empty else float(v.min()),
            'median': None if v.dropna().empty else float(v.median()),
            'max': None if v.dropna().empty else float(v.max()),
            'suspicious': int(suspicious.sum()), 'suspicious_pct': round(float(suspicious.mean()), 4),
        }
    return out


def clean(original: pd.DataFrame):
    """Returns (cleaned, log). Never changes any column other than mileage_mpg."""
    cleaned = original.copy()
    v = original[MILEAGE]
    fuel = original['fuel']
    rules = pd.Series(pd.NA, index=original.index, dtype=object)
    rules[fuel.isin(LIQUID_FUELS) & (v == 0)] = ZERO_TO_MISSING
    rules[fuel.isin(GAS_FUELS) & v.notna()] = CNG_LPG_TO_MISSING
    changed = rules.notna()
    cleaned.loc[changed, MILEAGE] = np.nan

    log = original.loc[changed, ['name', 'company', 'model', 'edition', 'year', 'fuel']].copy()
    log.insert(0, 'csv_line', log.index + 2)  # +1 header, +1 for 1-based lines
    log['original_mileage_mpg'] = v[changed]
    log['cleaned_mileage_mpg'] = np.nan
    log['rule'] = rules[changed]
    return cleaned, log


def run(source=DATA_FILE_PATH, cleaned_path=CLEANED_PATH, log_path=LOG_PATH, report_path=REPORT_PATH) -> dict:
    source_md5 = _md5(source)
    original = pd.read_csv(source)
    cleaned, log = clean(original)

    for path in (cleaned_path, log_path, report_path):
        if os.path.abspath(path) == os.path.abspath(source):
            raise ValueError('refusing to overwrite the original historical data')
    cleaned.to_csv(cleaned_path, index=False)
    log.to_csv(log_path, index=False)

    liquid_kept = original['fuel'].isin(LIQUID_FUELS) & (original[MILEAGE] > 0)
    report = {
        'source': source, 'source_md5': source_md5, 'cleaned_file': cleaned_path,
        'original_rows': int(len(original)), 'cleaned_rows': int(len(cleaned)),
        'mileage_values_changed': int(len(log)),
        'set_to_missing': int(len(log)),
        'corrected_to_new_value': 0,
        'left_unchanged': int(len(original) - len(log)),
        'left_unchanged_detail': {
            'petrol_diesel_plausible_kept': int((liquid_kept & is_plausible_liquid_mileage(original[MILEAGE])).sum()),
            'petrol_diesel_positive_outside_plausible_range_kept': int((liquid_kept & ~is_plausible_liquid_mileage(
                original[MILEAGE])).sum()),
            'already_missing': int(original[MILEAGE].isna().sum()),
        },
        'changes_by_rule': log['rule'].value_counts().to_dict(),
        'changes_by_fuel': log['fuel'].value_counts().to_dict(),
        'before': fuel_stats(original), 'after': fuel_stats(cleaned),
        'rules': {KEEP_PLAUSIBLE: 'petrol/diesel > 0 kept (rated km/l x ~2.35; plausibility-checked, never altered)',
                  ZERO_TO_MISSING: 'petrol/diesel == 0 set to missing (no same-variant value to use)',
                  CNG_LPG_TO_MISSING: 'CNG/LPG set to missing (unit cannot be verified)'},
    }
    if _md5(source) != source_md5:
        raise RuntimeError('the original historical data changed during cleaning')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    r = run()
    print(f"Original rows {r['original_rows']:,} -> cleaned rows {r['cleaned_rows']:,}")
    print(f"mileage values changed: {r['mileage_values_changed']} (all set to missing, 0 given new values); "
          f"left unchanged: {r['left_unchanged']:,}")
    print('changes by rule:', r['changes_by_rule'])
    print('changes by fuel:', r['changes_by_fuel'])
    print(f"{'fuel':7} {'coverage before':>16} {'after':>7} {'suspicious before':>18} {'after':>6}")
    for fuel in r['before']:
        b, a = r['before'][fuel], r['after'][fuel]
        print(f"{fuel:7} {b['coverage']:>16.1%} {a['coverage']:>7.1%} {b['suspicious']:>18} {a['suspicious']:>6}")
    print(f'Wrote {CLEANED_PATH}, {LOG_PATH}, {REPORT_PATH}. Original unchanged (md5 {r["source_md5"]}).')


if __name__ == '__main__':
    main()
