"""Technical-specification lookup for current listings.

Current listings usually lack mileage / engine / power / torque / seats. This fills them ONLY from reference
rows describing the same vehicle, and only when those rows agree. Nothing is guessed:

* specs come from reference rows with the same normalised company + model + edition + fuel + transmission,
  first for the same year (tier 1), otherwise across all years if every year agrees (tier 2);
* each spec is looked up on its own - if the reference rows disagree on e.g. power, power stays missing
  (marked 'conflict') while an agreeing spec such as seats is still filled;
* a value already present in the listing is never replaced;
* selling_price is never read (the lookup is built from spec columns only);
* every filled or missing value is labelled in `<spec>_source`, so enriched values stay distinguishable.

Leakage: the lookup must be built from reference data that contains no evaluation rows. Build it from the
historical data (default), or from historical + the TRAINING part of current listings - never from held-out
current listings. `build_spec_lookup` refuses reference rows marked as held out.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

SPEC_COLS = ['mileage_mpg', 'engine_cc', 'max_power_bhp', 'torque_nm', 'seats']
VARIANT_KEY = ['company', 'model', 'edition', 'fuel', 'transmission']
YEAR_KEY = VARIANT_KEY + ['year']

PROVIDED = 'provided'            # value was in the listing itself
MATCH_YEAR = 'lookup_same_year'  # all reference rows of this variant and year agree
MATCH_VARIANT = 'lookup_variant' # no same-year rows, but all years of this variant agree
CONFLICT = 'conflict'            # reference rows exist but disagree - left missing
MISSING = 'missing'              # no reference rows for this variant - left missing

HOLDOUT_FLAG = 'is_holdout'


def _normalise_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in VARIANT_KEY:
        out[col] = out[col].fillna('').astype(str).str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)
    out['year'] = pd.to_numeric(out['year'], errors='coerce').astype(float)
    return out


@dataclass
class SpecLookup:
    by_year: pd.DataFrame      # index YEAR_KEY, per spec: agreed value (NaN if none) and whether rows conflict
    by_variant: pd.DataFrame   # index VARIANT_KEY, same columns
    reference_rows: int


def _agreement(grouped) -> pd.DataFrame:
    table = {}
    for spec in SPEC_COLS:
        known = grouped[spec].nunique()           # distinct non-missing values
        table[spec] = grouped[spec].first().where(known == 1)
        table[f'{spec}_conflict'] = known > 1
        table[f'{spec}_support'] = grouped[spec].count()
    return pd.DataFrame(table)


def build_spec_lookup(reference: pd.DataFrame) -> SpecLookup:
    """Reference = rows whose specs are trusted (historical data, optionally plus current TRAINING rows)."""
    if HOLDOUT_FLAG in reference.columns and reference[HOLDOUT_FLAG].fillna(False).astype(bool).any():
        raise ValueError('spec lookup must not be built from held-out evaluation rows')
    ref = _normalise_keys(reference[YEAR_KEY + SPEC_COLS])  # deliberately no selling_price
    ref = ref.dropna(subset=['year'])
    return SpecLookup(
        by_year=_agreement(ref.groupby(YEAR_KEY)),
        by_variant=_agreement(ref.groupby(VARIANT_KEY)),
        reference_rows=len(ref),
    )


def enrich_specs(listings: pd.DataFrame, lookup: SpecLookup) -> pd.DataFrame:
    """Returns a copy with missing specs filled where the reference agrees, plus a `<spec>_source` column each."""
    out = listings.copy()
    for spec in SPEC_COLS:
        if spec not in out.columns:
            out[spec] = np.nan
    keys = _normalise_keys(out[YEAR_KEY])
    year_idx = pd.MultiIndex.from_frame(keys[YEAR_KEY])
    variant_idx = pd.MultiIndex.from_frame(keys[VARIANT_KEY])

    for spec in SPEC_COLS:
        provided = pd.to_numeric(out[spec], errors='coerce')
        y_val = lookup.by_year[spec].reindex(year_idx).to_numpy()
        y_conflict = lookup.by_year[f'{spec}_conflict'].reindex(year_idx).fillna(False).to_numpy(dtype=bool)
        y_known = lookup.by_year[f'{spec}_support'].reindex(year_idx).fillna(0).to_numpy() > 0
        v_val = lookup.by_variant[spec].reindex(variant_idx).to_numpy()
        v_conflict = lookup.by_variant[f'{spec}_conflict'].reindex(variant_idx).fillna(False).to_numpy(dtype=bool)

        value = provided.to_numpy(dtype=float).copy()
        source = np.full(len(out), MISSING, dtype=object)
        has = ~np.isnan(value)
        source[has] = PROVIDED

        # tier 1: same variant, same year
        use_year = ~has & ~np.isnan(y_val)
        value[use_year], source[use_year] = y_val[use_year], MATCH_YEAR
        year_conflict = ~has & y_conflict
        source[year_conflict] = CONFLICT

        # tier 2: only when the variant has no rows at all for this year, and all its years agree
        use_variant = ~has & ~y_known & ~np.isnan(v_val)
        value[use_variant], source[use_variant] = v_val[use_variant], MATCH_VARIANT
        source[~has & ~y_known & v_conflict] = CONFLICT

        out[spec] = value
        out[f'{spec}_source'] = source
    return out


def enrichment_summary(enriched: pd.DataFrame) -> str:
    lines = ['Specification enrichment (current listings):']
    for spec in SPEC_COLS:
        counts = enriched[f'{spec}_source'].value_counts()
        parts = ', '.join(f'{k} {counts.get(k, 0)}' for k in (PROVIDED, MATCH_YEAR, MATCH_VARIANT, CONFLICT, MISSING))
        lines.append(f'  {spec:<14} {parts}')
    complete = enriched[[f'{s}_source' for s in SPEC_COLS]].isin([PROVIDED, MATCH_YEAR, MATCH_VARIANT]).all(axis=1)
    lines.append(f'  rows with all specs known: {int(complete.sum())} / {len(enriched)}')
    return '\n'.join(lines)
