"""Loading and validation of training data.

Historical data (data/car-details.csv) is always used. Current-market listings (data/current-listings.csv)
are optional: when the file is absent, everything behaves exactly as before.

Every returned row carries a `source` column ('historical' or 'current') so the two stay distinguishable.
Current listings are validated row by row; invalid rows are never dropped silently - they are returned in a
report with the reason, and excluded from the valid set.
"""
import hashlib
import os
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from training.train_utils import DATA_FILE_PATH, CURRENT_DATA_FILE_PATH

SOURCE_COL = 'source'
HISTORICAL = 'historical'
CURRENT = 'current'

# column names follow data/car-details.csv (e.g. `company`, not `brand`)
CURRENT_REQUIRED_COLS = [
    'company', 'model', 'edition', 'year', 'km_driven', 'fuel', 'transmission', 'owner',
    'seller_type', 'selling_price', 'city', 'listing_date',
]
# the model uses these specs; listings often lack them, so they are optional (missing -> NaN, which the
# HistGradientBoosting model handles natively, as it already does for ~200 historical rows)
CURRENT_OPTIONAL_COLS = ['mileage_mpg', 'engine_cc', 'max_power_bhp', 'torque_nm', 'seats']
COLUMN_ALIASES = {'brand': 'company'}

# categorical fields with a closed set of values, taken from the historical data (compared case-insensitively)
ALLOWED_VALUES = {
    'fuel': {'petrol', 'diesel', 'cng', 'lpg'},
    'transmission': {'manual', 'automatic'},
    'owner': {'first', 'second', 'third', 'fourth & above', 'test drive car'},
    'seller_type': {'individual', 'dealer', 'trustmark dealer'},
}
MIN_YEAR = 1980

# fields that identify one physical listing; used to keep repeated copies of a listing on the same side
# of a train / evaluation split
LISTING_KEY_COLS = ['company', 'model', 'edition', 'year', 'km_driven', 'fuel', 'transmission', 'owner', 'city']


class CurrentDataError(ValueError):
    """The current-listings file cannot be used at all (e.g. required columns are missing)."""


@dataclass
class ValidationReport:
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: pd.DataFrame = field(default_factory=pd.DataFrame)  # original row + `row_number` + `errors`
    warnings: list = field(default_factory=list)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_rows)

    def summary(self) -> str:
        lines = [f'Current listings: {self.total_rows} rows, {self.valid_rows} valid, {self.invalid_count} invalid']
        if self.invalid_count:
            reasons = self.invalid_rows['errors'].str.split('; ').explode().value_counts()
            lines.append('Invalid rows by reason:')
            lines += [f'  {count:>5}  {reason}' for reason, count in reasons.items()]
            shown = self.invalid_rows.head(10)
            lines.append('First invalid rows (row_number is the line in the CSV):')
            lines += [f"  line {r.row_number}: {r.errors}" for r in shown.itertuples()]
        lines += [f'Warning: {w}' for w in self.warnings]
        return '\n'.join(lines)


def load_historical(path: str = DATA_FILE_PATH) -> pd.DataFrame:
    """The historical dataset, exactly as training has always read it, tagged with its source."""
    df = pd.read_csv(path).drop_duplicates()
    df[SOURCE_COL] = HISTORICAL
    return df


def _validate_current(raw: pd.DataFrame, today: date) -> tuple[pd.DataFrame, ValidationReport]:
    report = ValidationReport(total_rows=len(raw))
    df = raw.rename(columns={c: COLUMN_ALIASES.get(c.strip().lower(), c.strip().lower()) for c in raw.columns})

    missing = [c for c in CURRENT_REQUIRED_COLS if c not in df.columns]
    if missing:
        raise CurrentDataError(f'current listings file is missing required columns: {missing}')
    for col in CURRENT_OPTIONAL_COLS:
        if col not in df.columns:
            df[col] = np.nan
            report.warnings.append(f"optional column '{col}' not present - left empty (model handles missing values)")

    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    def flag(mask, message):
        for i in df.index[mask]:
            errors[i].append(message)

    # required text fields
    for col in ['company', 'model', 'city']:
        blank = df[col].isna() | (df[col].astype(str).str.strip() == '')
        flag(blank, f'{col} is empty')
    df['edition'] = df['edition'].fillna('')  # the variant is optional for the model

    # the source's own listing id, when supplied, must identify exactly one row. It is kept as
    # `source_listing_id`; `listing_id` is reserved for the internal repeated-car key used by holdout splits
    if 'listing_id' in df.columns:
        ids = df['listing_id'].astype('string').str.strip()
        blank_id = ids.isna() | (ids == '')
        flag(blank_id, 'listing_id is empty')
        flag(~blank_id & ids.duplicated(keep=False), 'listing_id is duplicated')
        df = df.drop(columns='listing_id').assign(source_listing_id=ids)

    # numeric fields
    numeric = {}
    for col in ['year', 'km_driven', 'selling_price'] + CURRENT_OPTIONAL_COLS:
        numeric[col] = pd.to_numeric(df[col], errors='coerce')
        not_numeric = df[col].notna() & numeric[col].isna()
        flag(not_numeric, f'{col} is not a number')
        df[col] = numeric[col]
    for col in ['year', 'km_driven', 'selling_price']:
        flag(df[col].isna() & ~errors.map(lambda e, c=col: f'{c} is not a number' in e), f'{col} is missing')

    # dates
    parsed_dates = pd.to_datetime(df['listing_date'], errors='coerce', format='ISO8601')
    flag(df['listing_date'].isna() | parsed_dates.isna(), 'listing_date is missing or not a valid date (use YYYY-MM-DD)')
    flag(parsed_dates.dt.date > today, 'listing_date is in the future')
    df['listing_date'] = parsed_dates

    # ranges
    flag(df['year'].notna() & ((df['year'] < MIN_YEAR) | (df['year'] != df['year'].round())),
         f'year must be a whole number >= {MIN_YEAR}')
    listing_year = parsed_dates.dt.year.fillna(today.year)
    flag(df['year'].notna() & (df['year'] > listing_year), 'year is after the listing date')
    flag(df['km_driven'] < 0, 'km_driven is negative')
    flag(df['selling_price'] <= 0, 'selling_price must be positive')

    # closed categories
    for col, allowed in ALLOWED_VALUES.items():
        normalised = df[col].astype(str).str.strip().str.lower()
        flag(~normalised.isin(allowed), f'{col} must be one of {sorted(allowed)}')

    invalid_mask = errors.map(bool)
    invalid = raw.loc[invalid_mask].copy()
    invalid.insert(0, 'row_number', invalid.index + 2)  # +1 for the header line, +1 for 1-based lines
    invalid['errors'] = errors[invalid_mask].map('; '.join)
    report.invalid_rows = invalid

    valid = df.loc[~invalid_mask].copy()
    valid['year'] = valid['year'].astype(int)
    report.valid_rows = len(valid)

    duplicates = valid.duplicated(subset=LISTING_KEY_COLS + ['selling_price', 'listing_date']).sum()
    if duplicates:
        report.warnings.append(f'{duplicates} rows are exact repeats of another listing (kept, grouped for splits)')
    return valid, report


def load_current(path: str = CURRENT_DATA_FILE_PATH, today: date | None = None):
    """Returns (valid_rows, report), or (None, None) when the optional file does not exist."""
    if not os.path.exists(path):
        return None, None
    raw = pd.read_csv(path, dtype=str, keep_default_na=True)
    valid, report = _validate_current(raw, today or date.today())
    valid[SOURCE_COL] = CURRENT
    valid['listing_id'] = _listing_ids(valid)
    return valid, report


def load_training_data(historical_path: str = DATA_FILE_PATH, current_path: str = CURRENT_DATA_FILE_PATH,
                       today: date | None = None):
    """Returns (combined, historical, current, report). `current` and `report` are None without the file."""
    historical = load_historical(historical_path)
    current, report = load_current(current_path, today)
    combined = historical if current is None else pd.concat([historical, current], ignore_index=True, sort=False)
    return combined, historical, current, report


def _listing_ids(df: pd.DataFrame) -> pd.Series:
    """Same physical listing -> same id (text compared case-insensitively)."""
    if df.empty:
        return pd.Series([], index=df.index, dtype=object)
    key = df[LISTING_KEY_COLS].astype(str).apply(lambda s: s.str.strip().str.lower()).agg('|'.join, axis=1)
    return key.map(lambda k: hashlib.md5(k.encode()).hexdigest()[:12])


def split_current_holdout(current: pd.DataFrame, holdout_fraction: float = 0.2):
    """Time-based split of current listings for evaluation: the most recent listings are held out.

    All copies of the same listing (same listing_id) go to the same side, so no listing can appear in both
    training and evaluation. Returns (train, holdout).
    """
    if not 0 < holdout_fraction < 1:
        raise ValueError('holdout_fraction must be between 0 and 1')
    latest = current.groupby('listing_id')['listing_date'].max().sort_values(kind='stable')
    n_holdout = max(1, int(round(len(latest) * holdout_fraction)))
    holdout_ids = set(latest.index[-n_holdout:])
    is_holdout = current['listing_id'].isin(holdout_ids)
    return current[~is_holdout].copy(), current[is_holdout].copy()


def dataset_statistics(historical: pd.DataFrame, current: pd.DataFrame | None) -> str:
    lines = [f'Historical rows: {len(historical):,}']
    if current is None:
        lines += ['Current rows: 0 (data/current-listings.csv not found - historical data only)',
                  f'Combined rows: {len(historical):,}']
        return '\n'.join(lines)
    lines += [f'Current rows: {len(current):,}', f'Combined rows: {len(historical) + len(current):,}']
    if len(current):
        lines.append(f"Current date range: {current['listing_date'].min():%Y-%m-%d} to "
                     f"{current['listing_date'].max():%Y-%m-%d}")
        cities = current['city'].str.strip().value_counts()
        lines.append(f'Current cities ({len(cities)}): ' + ', '.join(f'{c} ({n})' for c, n in cities.head(15).items())
                     + (' ...' if len(cities) > 15 else ''))
        lines.append(f"Current unique listings: {current['listing_id'].nunique():,}")
    return '\n'.join(lines)


def add_time_features(df: pd.DataFrame, historical_listing_year: int) -> pd.DataFrame:
    """Adds `listing_year` and `age_at_listing` (years between manufacture and listing).

    Current rows use their real listing_date. Historical rows have no listing date, so the caller must state
    the year they were listed (a decision, not a default); those rows are marked `listing_year_assumed`.
    """
    if historical_listing_year is None:
        raise ValueError('historical_listing_year must be given explicitly')
    out = df.copy()
    is_current = out[SOURCE_COL] == CURRENT
    listing_year = pd.Series(float(historical_listing_year), index=out.index)
    if 'listing_date' in out.columns:
        listing_year[is_current] = pd.to_datetime(out.loc[is_current, 'listing_date']).dt.year
    out['listing_year'] = listing_year.astype(int)
    out['listing_year_assumed'] = ~is_current
    out['age_at_listing'] = out['listing_year'] - out['year']
    bad = out['age_at_listing'] < 0
    if bad.any():
        raise ValueError(f'{int(bad.sum())} rows were listed before their manufacture year - '
                         f'check historical_listing_year ({historical_listing_year})')
    return out
