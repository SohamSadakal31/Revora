"""Validate data/current-listings.csv without training anything.

    python -m training.validate_current_listings [--path data/current-listings.csv]

Exit code: 0 = all rows valid, 1 = some rows invalid (listed with reasons), 2 = file missing or unusable.
"""
import argparse
import sys

from training.data_loading import CurrentDataError, load_current
from training.experiment_current_market import data_summary
from training.train_utils import CURRENT_DATA_FILE_PATH


def _fmt_range(r, money=False):
    if r[0] is None:
        return '-'
    return f'₹{r[0]:,.0f} to ₹{r[1]:,.0f}' if money else f'{r[0]:,} to {r[1]:,}' if not isinstance(r[0], str) \
        else f'{r[0]} to {r[1]}'


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--path', default=CURRENT_DATA_FILE_PATH)
    args = ap.parse_args(argv)

    try:
        current, report = load_current(args.path)
    except CurrentDataError as e:
        print(f'INVALID FILE: {e}')
        return 2
    if current is None:
        print(f'NOT FOUND: {args.path} - copy data/current-listings.template.csv and add real listings')
        return 2

    s = data_summary(current, report)
    specs = ', '.join(f'{k} {v}' for k, v in s['missing_specs_in_file'].items())
    print(f"""Current listings: {args.path}
  Total rows            : {s['total_rows']}
  Valid rows            : {s['valid_rows']}
  Invalid rows          : {s['invalid_rows']}
  Listing dates (valid) : {_fmt_range(s['listing_date_range'])}
  Unique companies      : {s['companies']}
  Unique models         : {s['models']}
  Unique cities         : {s['cities']}
  Price range           : {_fmt_range(s['price_range'], money=True)}
  Year range            : {_fmt_range(s['year_range'])}
  km range              : {_fmt_range(s['km_range'])}
  Missing specs (valid rows, left missing - never guessed): {specs}
  Duplicate listing_id  : {s['duplicate_listing_ids']} rows (invalid)
  Same car details repeated under different ids: {s['repeated_cars_same_details']} (kept, grouped together)
  Fuel / transmission / seller: {s['fuel']} / {s['transmission']} / {s['seller_type']}""")
    if report.invalid_count or report.warnings:
        print('\n' + report.summary())
    if report.invalid_count:
        print('\nRESULT: fix the invalid rows above before running the experiment.')
        return 1
    print('\nRESULT: all rows valid. Next: python -m training.experiment_current_market')
    return 0


if __name__ == '__main__':
    sys.exit(main())
