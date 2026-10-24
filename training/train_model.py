"""Train the production model: historical + current listings, current rows weighted x2 (experiment approach C).

    python -m training.train_model          (run inside the API image so library versions match production)

Uses exactly the pipeline measured in training/experiment_current_market.py:
  features   age_at_listing + listing_year (instead of manufacture year), km, specs, text categories, variant words
  data       historical (data/car-details-cleaned.csv; ODbL/DbCL) + data/current-listings.csv (CC0 + ODbL/DbCL)
  weights    historical 1.0, current 2.0
  target     log(price); squared-error loss (keeps the price rules exact); 5th / 95th percentile models for the range

1. Accuracy is measured first: trained without the newest 20% of current listings, scored on them.
2. The saved model is then trained on ALL rows (holdout included) - the reported scores are therefore conservative.
"""
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn

from training.experiment_current_market import (
    PRODUCTION_PARAMS, ExperimentConfig, build_model, enrich_all, feature_cols, metrics, prepare, sample_weights,
    to_features, verify_historical,
)
from training.spec_enrichment import build_spec_lookup, enrich_specs
from training.train_utils import CLEANED_DATA_FILE_PATH, MODEL_DIR, MODEL_META_PATH, MODEL_PATH, MODEL_RANGE_PATH

CONFIG = ExperimentConfig(historical_path=CLEANED_DATA_FILE_PATH, historical_weight=1.0, current_weight=2.0)
RANGE_QUANTILES = {'low': 0.05, 'high': 0.95}
DATA_SOURCES = {
    'historical': {'dataset': 'https://www.kaggle.com/datasets/nehalbirla/vehicle-dataset-from-cardekho',
                   'licence': 'ODbL v1.0 (database) / DbCL v1.0 (contents) - attribution required'},
    'current': [{'dataset': 'https://www.kaggle.com/datasets/vrajesh0sharma7/used-car-price-prediction',
                 'licence': 'CC0: Public Domain'},
                {'dataset': 'https://www.kaggle.com/datasets/nehalbirla/vehicle-dataset-from-cardekho (car details v4.csv)',
                 'licence': 'ODbL v1.0 / DbCL v1.0 - attribution required'}],
}


def fit(train: pd.DataFrame, params: dict):
    cols = feature_cols()
    model = build_model(train[cols], params)
    model.fit(train[cols], train['selling_price'].to_numpy(float), reg__sample_weight=sample_weights(train, CONFIG))
    return model


def quantile_params(q):
    return dict(PRODUCTION_PARAMS, loss='quantile', quantile=q)


def main():
    verify_historical(CONFIG)
    historical, current_train, holdout, _, _ = prepare(CONFIG)
    hly = CONFIG.historical_listing_year
    cols = feature_cols()

    # 1. honest score: nothing from the holdout is used for training, spec lookup or preprocessing
    (hist_e, cur_train_e, holdout_e), _ = enrich_all(historical, current_train, holdout)
    train = pd.concat([to_features(hist_e, hly), to_features(cur_train_e, hly)], ignore_index=True)
    test = to_features(holdout_e, hly)
    pred = fit(train, PRODUCTION_PARAMS).predict(test[cols])
    low = fit(train, quantile_params(RANGE_QUANTILES['low'])).predict(test[cols])
    high = fit(train, quantile_params(RANGE_QUANTILES['high'])).predict(test[cols])
    y = test['selling_price'].to_numpy(float)
    m = metrics(y, pred)
    m['range_coverage'] = float(((y >= np.minimum(low, pred)) & (y <= np.maximum(high, pred))).mean())

    print('\nModel Evaluation (newest 20% of current listings, never used for training)')
    print('--------------------------------------------------------------------------')
    print(f"Holdout      : {len(test):,} listings, {holdout['listing_date'].min():%Y-%m-%d} to "
          f"{holdout['listing_date'].max():%Y-%m-%d}")
    print(f"MAE          : ₹{m['mae']:,.2f}")
    print(f"RMSE         : ₹{m['rmse']:,.2f}")
    print(f"R²           : {m['r2']:.4f}")
    print(f"Median error : {m['median_pct_error']:.1%}")
    print(f"Within ±10%  : {m['within_10pct']:.1%}")
    print(f"Within ±20%  : {m['within_20pct']:.1%}")
    print(f"Range cover  : {m['range_coverage']:.1%} of real prices fall inside the predicted range")

    # 2. final model: every row; spec lookup from historical + all current listings
    current_all = pd.concat([current_train, holdout], ignore_index=True)
    lookup = build_spec_lookup(pd.concat([historical, current_all], ignore_index=True, sort=False))
    full = pd.concat([to_features(enrich_specs(historical, lookup), hly),
                      to_features(enrich_specs(current_all, lookup), hly)], ignore_index=True)
    model = fit(full, PRODUCTION_PARAMS)
    price_range = {k: fit(full, quantile_params(q)) for k, q in RANGE_QUANTILES.items()}

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(price_range, MODEL_RANGE_PATH)
    manufacture_years = full['listing_year'] - full['age_at_listing']
    meta = {
        'trained_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'approach': 'C - historical + current listings, current weighted x2',
        'feature_version': 3,
        'features': cols,
        'training_rows': {'historical': len(historical), 'current': len(current_all), 'total': len(full)},
        'data_years': [int(manufacture_years.min()), int(manufacture_years.max())],
        'listing_years': [int(full['listing_year'].min()), int(full['listing_year'].max())],
        'historical_listing_year': hly, 'historical_listing_year_confirmed': False,
        'sample_weights': {'historical': CONFIG.historical_weight, 'current': CONFIG.current_weight},
        'data_sources': DATA_SOURCES,
        'sklearn_version': sklearn.__version__,
        'holdout_metrics': {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()},
    }
    with open(MODEL_META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f"\nSaved model trained on {len(full):,} cars ({len(historical):,} historical + {len(current_all):,} current) "
          f"to {MODEL_DIR}")


if __name__ == '__main__':
    main()
