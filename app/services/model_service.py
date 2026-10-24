import hashlib
import json
import os
from datetime import date
import joblib
import pandas as pd
from app.core.config import settings
from app.cache.redis_cache import set_cached_prediction, get_cached_prediction

model = joblib.load(settings.MODEL_PATH)
price_range = joblib.load(settings.MODEL_RANGE_PATH) if os.path.exists(settings.MODEL_RANGE_PATH) else None
model_meta = {}
if os.path.exists(settings.MODEL_META_PATH):
    with open(settings.MODEL_META_PATH, encoding='utf-8') as f:
        model_meta = json.load(f)

# part of the cache key, so prices cached from an older model are not served after retraining
with open(settings.MODEL_PATH, 'rb') as f:
    MODEL_VERSION = hashlib.md5(f.read()).hexdigest()[:8]

# every brand / model / fuel ... the model has seen, used to reject typos instead of guessing
_encoder = model.regressor_.named_steps['pre'].named_transformers_['cat']
KNOWN_VALUES = {col: set(cats) for col, cats in zip(_encoder.feature_names_in_, _encoder.categories_)}
DEALER_TYPES = {'dealer', 'trustmark dealer'}
KNOWN_VALUES['seller_type'] = DEALER_TYPES | {'individual'}  # a 0/1 number in the model, not a category

AVERAGE_KM_PER_YEAR = 10_000
# bump whenever the content of a price result changes, so cached results in the old format are not served
RESULT_FORMAT = 2  # 2: added forecast

# Dealer listings are priced this much above the same car from a private seller. Measured, not assumed: the median
# dealer-vs-individual price gap across 302 same model + year groups in the historical data (2020), where both seller
# types were listed in the same market. Applied to the private-seller estimate, so it is never counted twice.
DEALER_PREMIUM = 0.028

# The model is trained on the car's age when listed and the year of the listing. A car is priced at its age today,
# in today's listing year (the model uses its latest learned market level for years after its newest listings).
MARKET_YEAR = int(os.getenv('MARKET_YEAR', date.today().year))
if model_meta.get('feature_version') != 3:
    raise RuntimeError(f'{settings.MODEL_PATH} was not trained with the current features - retrain with '
                       'python -m training.train_model')


def _model_input(data: dict) -> dict:
    features = {k: v for k, v in data.items() if k != 'year'}
    if features.get('mileage_mpg') is None:
        features['mileage_mpg'] = float('nan')  # unknown mileage: the model was trained with missing values
    return _with_dealer_flag(dict(features, age_at_listing=MARKET_YEAR - data['year'], listing_year=MARKET_YEAR))


def _with_dealer_flag(row: dict) -> dict:
    return dict(row, sold_by_dealer=1.0 if row['seller_type'] in DEALER_TYPES else 0.0)


def _estimate(estimator, rows: list) -> list:
    """Private-seller price from the model, plus DEALER_PREMIUM for dealer listings."""
    private = estimator.predict(pd.DataFrame([dict(r, sold_by_dealer=0.0) for r in rows]))
    return [float(p) * (1 + DEALER_PREMIUM if r['seller_type'] in DEALER_TYPES else 1) for p, r in zip(private, rows)]


class UnknownValueError(ValueError):
    pass


def _normalise(data: dict) -> dict:
    # the model is trained on lowercase text, so "petrol" and "Petrol" mean the same thing
    return {key: val.strip().lower() if isinstance(val, str) else val for key, val in data.items()}


def _check_known(data: dict):
    for col, known in KNOWN_VALUES.items():
        if data[col] not in known:
            raise UnknownValueError(f"Unknown {col} '{data[col]}'. See GET /options for accepted values.")


def _factors(data: dict, price: float) -> list:
    """How much each condition moves the price, compared with a typical car of the same model and year."""
    typical_km = max(data['age_at_listing'], 1) * AVERAGE_KM_PER_YEAR
    references = [
        ('Kilometres driven', {'km_driven': float(typical_km)}, f'vs a typical {typical_km:,} km'),
        ('Previous owners', {'owner': 'first'}, 'vs a first-owner car'),
        ('Sold by', {'seller_type': 'individual'}, 'vs a private seller'),
    ]
    if data['edition']:
        references.insert(0, ('Variant', {'edition': ''}, 'vs an average variant of this model'))
    reference_prices = _estimate(model, [_with_dealer_flag(dict(data, **changes)) for _, changes, _ in references])
    return [
        {'factor': name, 'effect': round(float(price - ref), 2), 'compared_to': note}
        for (name, _, note), ref in zip(references, reference_prices)
        if abs(price - ref) >= 1000
    ]


def _forecast(data: dict, years=(1, 2, 3)) -> dict:
    """The same car 1-3 years older, driven at its own km-per-year rate so far, at today's market level."""
    age = data['age_at_listing']
    km_per_year = data['km_driven'] / age if age >= 1 and data['km_driven'] > 0 else AVERAGE_KM_PER_YEAR
    rows = [dict(data, age_at_listing=age + k, km_driven=data['km_driven'] + k * km_per_year) for k in years]
    prices = _estimate(model, rows)
    return {'forecast': [{'years': k, 'price': round(p, 2)} for k, p in zip(years, prices)],
            'forecast_km_per_year': round(km_per_year)}


def predict_car_price(data: dict) -> dict:
    data = _normalise(data)
    _check_known(data)
    data = _model_input(data)
    cache_key = f'{MODEL_VERSION} r{RESULT_FORMAT} {MARKET_YEAR} {DEALER_PREMIUM} ' + " ".join([str(val) for val in data.values()])
    cached = get_cached_prediction(cache_key)
    if cached:
        return cached

    price = _estimate(model, [data])[0]
    result = {'price': round(price, 2)}
    if price_range:
        low = _estimate(price_range['low'], [data])[0]
        high = _estimate(price_range['high'], [data])[0]
        result['price_low'], result['price_high'] = round(min(low, price), 2), round(max(high, price), 2)
    result['factors'] = _factors(data, price)
    result.update(_forecast(data))
    set_cached_prediction(cache_key, result)
    return result
