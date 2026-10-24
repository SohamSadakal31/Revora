import os
import tempfile

# no Redis on this port: also proves predictions work when the cache is down
os.environ['REDIS_URL'] = 'redis://localhost:1'
os.environ['USAGE_DB_PATH'] = os.path.join(tempfile.mkdtemp(), 'usage.db')
os.environ['USERS_DB_PATH'] = os.path.join(tempfile.mkdtemp(), 'users.db')

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

CAR = {
    'company': 'Maruti', 'model': 'Swift', 'edition': 'VDI', 'year': 2015, 'owner': 'First',
    'fuel': 'Diesel', 'seller_type': 'Individual', 'transmission': 'Manual', 'km_driven': 60000,
    'mileage_mpg': 55, 'engine_cc': 1248, 'max_power_bhp': 74, 'torque_nm': 190, 'seats': 5,
}


@pytest.fixture(scope='module')
def headers():
    r = client.post('/login', json={'username': settings.ADMIN_USERNAME, 'password': settings.ADMIN_PASSWORD})
    assert r.status_code == 200
    return {'token': r.json()['access_token'], 'api-key': settings.API_KEY}


def predict(headers, **changes):
    return client.post('/predict', json=dict(CAR, **changes), headers=headers)


def test_login_rejects_wrong_password():
    r = client.post('/login', json={'username': settings.ADMIN_USERNAME, 'password': 'wrong'})
    assert r.status_code == 401


def test_predict_requires_auth():
    assert client.post('/predict', json=CAR).status_code == 422  # missing headers
    r = client.post('/predict', json=CAR, headers={'token': 'bad', 'api-key': settings.API_KEY})
    assert r.status_code == 401


def test_predict_returns_sensible_price_and_range(headers):
    r = predict(headers)
    assert r.status_code == 200
    body = r.json()
    assert 200_000 < body['price'] < 1_000_000
    assert body['price_low'] <= body['price'] <= body['price_high']
    assert isinstance(body['factors'], list)


def test_text_inputs_are_case_insensitive(headers):
    assert predict(headers).json()['price'] == predict(headers, company='maruti', fuel='DIESEL').json()['price']


def test_more_km_never_raises_price(headers):
    prices = [predict(headers, km_driven=km).json()['price'] for km in (20_000, 60_000, 120_000, 200_000)]
    assert prices == sorted(prices, reverse=True)


def test_newer_car_never_cheaper(headers):
    prices = [predict(headers, year=y).json()['price'] for y in (2010, 2013, 2016, 2019)]
    assert prices == sorted(prices)


def test_unknown_model_rejected(headers):
    r = predict(headers, model='Swfit')
    assert r.status_code == 422
    assert 'Unknown model' in r.json()['detail']


def test_out_of_range_values_rejected(headers):
    assert predict(headers, year=1900).status_code == 422
    assert predict(headers, km_driven=-5).status_code == 422


def test_health_and_options():
    health = client.get('/health').json()
    assert health['status'] == 'ok' and health['redis'] == 'unavailable'
    assert 'swift' in client.get('/options').json()['model']


def test_stats_counts_searches(headers):
    predict(headers)
    stats = client.get('/stats', headers=headers).json()
    assert stats['total_searches'] >= 1


def test_mileage_is_optional_and_never_required(headers):
    cng = dict(CAR, fuel='CNG', edition='')
    cng.pop('mileage_mpg')
    r = client.post('/predict', json=cng, headers=headers)
    assert r.status_code == 200 and r.json()['price'] > 0
    assert predict(headers, mileage_mpg=0).status_code == 422  # 0 is not a fuel economy


def test_dealer_never_priced_below_private_seller(headers):
    for car in (CAR, dict(CAR, company='Hyundai', model='i20', edition='Asta', year=2012, km_driven=150000)):
        dealer = predict(headers, **{k: v for k, v in car.items() if k != 'seller_type'}, seller_type='Dealer').json()['price']
        private = predict(headers, **{k: v for k, v in car.items() if k != 'seller_type'}, seller_type='Individual').json()['price']
        assert dealer >= private


def test_dealer_price_is_private_price_plus_measured_premium(headers):
    from app.services.model_service import DEALER_PREMIUM
    body = {k: v for k, v in CAR.items() if k != 'seller_type'}
    dealer = predict(headers, **body, seller_type='Dealer').json()
    private = predict(headers, **body, seller_type='Individual').json()
    assert dealer['price'] == pytest.approx(private['price'] * (1 + DEALER_PREMIUM), rel=1e-4)
    sold_by = [f for f in dealer['factors'] if f['factor'] == 'Sold by']
    assert sold_by and sold_by[0]['effect'] > 0


def test_health_reports_dealer_premium_used_by_the_website():
    from app.services.model_service import DEALER_PREMIUM
    assert client.get('/health').json()['dealer_premium'] == DEALER_PREMIUM


def test_cached_results_include_current_format(headers, monkeypatch):
    # a result cached in an older format must not be served after the format changes
    import app.services.model_service as ms
    stale = {}
    monkeypatch.setattr(ms, 'get_cached_prediction', lambda key: stale.get(key))
    monkeypatch.setattr(ms, 'set_cached_prediction', lambda key, value: stale.__setitem__(key, value))
    old_key_result = {'price': 1.0, 'factors': []}
    data = ms._model_input(ms._normalise(dict(CAR)))
    stale[f"{ms.MODEL_VERSION} {ms.MARKET_YEAR} {ms.DEALER_PREMIUM} " + " ".join(str(v) for v in data.values())] = old_key_result
    assert 'forecast' in predict(headers).json()
