import numpy as np
import pandas as pd
import pytest

from training.data_loading import CURRENT, HISTORICAL, SOURCE_COL, add_time_features, load_historical
from training.spec_enrichment import (
    CONFLICT, MATCH_VARIANT, MATCH_YEAR, MISSING, PROVIDED, SPEC_COLS, build_spec_lookup, enrich_specs,
    enrichment_summary,
)

SPECS = dict(mileage_mpg=50.0, engine_cc=1197.0, max_power_bhp=82.0, torque_nm=113.0, seats=5.0)


def ref_row(year=2018, edition='VXI', price=500000, **spec_changes):
    return dict(company='Maruti', model='Swift', edition=edition, fuel='Petrol', transmission='Manual',
                year=year, selling_price=price, **dict(SPECS, **spec_changes))


def listing(year=2018, edition='VXI', **extra):
    return dict(company='Maruti', model='Swift', edition=edition, fuel='Petrol', transmission='Manual',
                year=year, selling_price=600000, **extra)


def enrich(reference_rows, listing_rows):
    return enrich_specs(pd.DataFrame(listing_rows), build_spec_lookup(pd.DataFrame(reference_rows)))


def test_same_year_match_fills_all_specs():
    out = enrich([ref_row(), ref_row()], [listing()])
    for spec, value in SPECS.items():
        assert out.loc[0, spec] == value and out.loc[0, f'{spec}_source'] == MATCH_YEAR


def test_matching_ignores_case_and_spacing():
    out = enrich([ref_row(edition='VXi  Optional')], [dict(listing(edition=' vxi optional'), company='MARUTI')])
    assert out.loc[0, 'engine_cc_source'] == MATCH_YEAR


def test_other_year_used_only_when_all_years_agree():
    out = enrich([ref_row(year=2016), ref_row(year=2017)], [listing(year=2019)])
    assert out.loc[0, 'engine_cc_source'] == MATCH_VARIANT and out.loc[0, 'engine_cc'] == 1197.0


def test_conflict_left_missing_per_spec():
    # the facelift changed power between years: power is a conflict, seats still agree
    out = enrich([ref_row(year=2016, max_power_bhp=76.8), ref_row(year=2017, max_power_bhp=79.4)], [listing(year=2019)])
    assert np.isnan(out.loc[0, 'max_power_bhp']) and out.loc[0, 'max_power_bhp_source'] == CONFLICT
    assert out.loc[0, 'seats'] == 5.0 and out.loc[0, 'seats_source'] == MATCH_VARIANT


def test_same_year_conflict_not_resolved_from_other_years():
    refs = [ref_row(year=2018, torque_nm=110), ref_row(year=2018, torque_nm=113), ref_row(year=2017)]
    out = enrich(refs, [listing(year=2018)])
    assert out.loc[0, 'torque_nm_source'] == CONFLICT and np.isnan(out.loc[0, 'torque_nm'])


def test_unknown_variant_stays_missing_not_guessed():
    out = enrich([ref_row()], [listing(edition='LXI CNG 1.0'), dict(listing(), model='New Wagon-R')])
    for spec in SPEC_COLS:
        assert out[f'{spec}_source'].eq(MISSING).all() and out[spec].isna().all()


def test_provided_values_never_overwritten():
    out = enrich([ref_row()], [listing(engine_cc=1248.0)])
    assert out.loc[0, 'engine_cc'] == 1248.0 and out.loc[0, 'engine_cc_source'] == PROVIDED
    assert out.loc[0, 'seats_source'] == MATCH_YEAR


def test_selling_price_does_not_influence_specs():
    cheap = enrich([ref_row(price=1), ref_row(price=1)], [listing()])
    dear = enrich([ref_row(price=10**8), ref_row(price=10**8)], [dict(listing(), selling_price=1)])
    pd.testing.assert_frame_equal(cheap[SPEC_COLS], dear[SPEC_COLS])


def test_reference_missing_values_do_not_count_as_conflict():
    out = enrich([ref_row(), ref_row(mileage_mpg=np.nan)], [listing()])
    assert out.loc[0, 'mileage_mpg_source'] == MATCH_YEAR


def test_held_out_rows_rejected_as_reference():
    refs = pd.DataFrame([ref_row(), ref_row()]).assign(is_holdout=[False, True])
    with pytest.raises(ValueError, match='held-out'):
        build_spec_lookup(refs)


def test_holdout_listing_not_enriched_from_itself():
    # a held-out current listing with its own specs must not become a reference for itself or others
    train_ref = pd.DataFrame([ref_row(year=2016)])
    holdout = pd.DataFrame([listing(year=2020, edition='ZXI', engine_cc=1197.0)])
    out = enrich_specs(holdout.drop(columns='engine_cc'), build_spec_lookup(train_ref))
    assert out.loc[0, 'engine_cc_source'] == MISSING


def test_summary_counts():
    out = enrich([ref_row()], [listing(), listing(edition='unknown')])
    summary = enrichment_summary(out)
    assert 'rows with all specs known: 1 / 2' in summary


def test_real_historical_data_builds_lookup():
    historical = load_historical()
    lookup = build_spec_lookup(historical)
    assert lookup.reference_rows == len(historical)
    sample = historical.dropna(subset=SPEC_COLS).head(200).drop(columns=SPEC_COLS)
    out = enrich_specs(sample, lookup)
    matched = out[[f'{s}_source' for s in SPEC_COLS]].isin([MATCH_YEAR, MATCH_VARIANT])
    assert matched.to_numpy().mean() > 0.8


# ---- time features for the future experiment ----

def test_time_features_require_explicit_historical_year():
    df = pd.DataFrame([dict(year=2015)]).assign(**{SOURCE_COL: HISTORICAL})
    with pytest.raises(ValueError):
        add_time_features(df, None)


def test_time_features_use_real_listing_dates_for_current_rows():
    df = pd.DataFrame([
        {'year': 2015, SOURCE_COL: HISTORICAL, 'listing_date': pd.NaT},
        {'year': 2019, SOURCE_COL: CURRENT, 'listing_date': pd.Timestamp('2026-09-01')},
    ])
    out = add_time_features(df, historical_listing_year=2020)
    assert out['listing_year'].tolist() == [2020, 2026]
    assert out['age_at_listing'].tolist() == [5, 7]
    assert out['listing_year_assumed'].tolist() == [True, False]


def test_time_features_reject_impossible_ages():
    df = pd.DataFrame([{'year': 2021, SOURCE_COL: HISTORICAL}])
    with pytest.raises(ValueError, match='before their manufacture year'):
        add_time_features(df, historical_listing_year=2020)
