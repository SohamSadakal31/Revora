import os
import sqlite3
import tempfile

os.environ['REDIS_URL'] = 'redis://localhost:1'
os.environ.setdefault('USAGE_DB_PATH', os.path.join(tempfile.mkdtemp(), 'usage.db'))
os.environ['USERS_DB_PATH'] = os.path.join(tempfile.mkdtemp(), 'users.db')

from fastapi.testclient import TestClient  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
settings.USERS_DB_PATH = os.environ['USERS_DB_PATH']  # other test modules may have imported settings first
CAR = {'company': 'Maruti', 'model': 'Swift', 'edition': 'VDI', 'year': 2015, 'owner': 'First', 'fuel': 'Diesel',
       'seller_type': 'Individual', 'transmission': 'Manual', 'km_driven': 60000, 'engine_cc': 1248,
       'max_power_bhp': 74, 'torque_nm': 190, 'seats': 5}


def register(email='Rahul.Sharma@Example.com', password='Str0ngPass', full_name='Rahul Sharma'):
    return client.post('/register', json={'email': email, 'password': password, 'full_name': full_name})


def login(email, password):
    return client.post('/login', json={'email': email, 'password': password})


def test_register_returns_a_working_token():
    r = register()
    assert r.status_code == 201 and r.json()['email'] == 'rahul.sharma@example.com'
    token = r.json()['access_token']
    assert client.get('/me', headers={'token': token}).json() == {'email': 'rahul.sharma@example.com',
                                                                    'full_name': 'Rahul Sharma', 'is_admin': False}
    p = client.post('/predict', json=CAR, headers={'token': token, 'api-key': settings.API_KEY})
    assert p.status_code == 200 and p.json()['price'] > 0


def test_login_by_email_any_case_and_wrong_password_rejected():
    register('login.test@example.com', 'Passw0rd99')
    r = login('LOGIN.Test@Example.COM', 'Passw0rd99')
    assert r.status_code == 200 and r.json()['email'] == 'login.test@example.com'
    assert login('login.test@example.com', 'wrong-pass1').status_code == 401
    assert login('nobody@example.com', 'Passw0rd99').status_code == 401


def test_email_required_valid_and_unique():
    assert client.post('/register', json={'password': 'Passw0rd99'}).status_code == 422
    assert register('not-an-email', 'Passw0rd99').status_code == 422
    assert register('shared@example.com', 'Passw0rd99').status_code == 201
    r = register('SHARED@example.com', 'Passw0rd99')
    assert r.status_code == 409 and 'email' in r.json()['detail']


def test_weak_passwords_rejected():
    assert register('weak1@example.com', 'short1').status_code == 422
    assert register('weak2@example.com', 'onlyletters').status_code == 422
    assert register('weak3@example.com', '12345678').status_code == 422


def test_passwords_are_stored_hashed_not_plain():
    register('hash.check@example.com', 'Passw0rd99')
    stored = sqlite3.connect(settings.USERS_DB_PATH).execute(
        "SELECT password_hash FROM users WHERE email = 'hash.check@example.com'").fetchone()[0]
    assert 'Passw0rd99' not in stored and stored.startswith('pbkdf2_sha256$')


def test_admin_account_from_env_still_works():
    r = client.post('/login', json={'username': settings.ADMIN_USERNAME, 'password': settings.ADMIN_PASSWORD})
    assert r.status_code == 200 and client.get('/me', headers={'token': r.json()['access_token']}).status_code == 200


def test_login_needs_an_email():
    assert client.post('/login', json={'password': 'Passw0rd99'}).status_code == 422


def test_me_requires_a_valid_token():
    assert client.get('/me', headers={'token': 'not-a-token'}).status_code == 401
