"""Password change, account deletion, lock-out, password reset, history, forecast, sharing, admin stats, backups."""
import base64
import os
import re
import sqlite3
import tempfile
import uuid

os.environ['REDIS_URL'] = 'redis://localhost:1'
os.environ.setdefault('USAGE_DB_PATH', os.path.join(tempfile.mkdtemp(), 'usage.db'))
os.environ.setdefault('USERS_DB_PATH', os.path.join(tempfile.mkdtemp(), 'users.db'))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import backup, mailer  # noqa: E402

client = TestClient(app)
CAR = {'company': 'Maruti', 'model': 'Swift', 'edition': 'VDI', 'year': 2015, 'owner': 'First', 'fuel': 'Diesel',
       'seller_type': 'Individual', 'transmission': 'Manual', 'km_driven': 60000, 'engine_cc': 1248,
       'max_power_bhp': 74, 'torque_nm': 190, 'seats': 5}
PASSWORD = 'Passw0rd99'


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'USERS_DB_PATH', str(tmp_path / 'users.db'))
    monkeypatch.setattr(settings, 'USAGE_DB_PATH', str(tmp_path / 'usage.db'))


@pytest.fixture
def outbox(monkeypatch):
    """Email 'configured', but captured instead of sent."""
    sent = []
    monkeypatch.setattr(settings, 'SMTP_HOST', 'smtp.test')
    monkeypatch.setattr(settings, 'SMTP_FROM', 'noreply@test')
    monkeypatch.setattr(mailer, 'send_email', lambda to, subject, body, attachments=None: sent.append(
        {'to': to, 'subject': subject, 'body': body, 'attachments': attachments or []}))
    return sent


def new_user():
    email = f'{uuid.uuid4().hex[:10]}@example.com'
    r = client.post('/register', json={'email': email, 'password': PASSWORD, 'full_name': 'Test'})
    assert r.status_code == 201
    return email, {'token': r.json()['access_token'], 'api-key': settings.API_KEY}


def login(email, password):
    return client.post('/login', json={'email': email, 'password': password})


# ---- change password / delete account ----

def test_change_password():
    email, h = new_user()
    assert client.post('/account/password', headers=h,
                       json={'current_password': 'wrong-pass1', 'new_password': 'N3wPassword'}).status_code == 422
    assert client.post('/account/password', headers=h,
                       json={'current_password': PASSWORD, 'new_password': 'weak'}).status_code == 422
    assert client.post('/account/password', headers=h,
                       json={'current_password': PASSWORD, 'new_password': 'N3wPassword'}).status_code == 200
    assert login(email, PASSWORD).status_code == 401 and login(email, 'N3wPassword').status_code == 200


def test_delete_account_removes_account_and_history():
    email, h = new_user()
    client.post('/predict', json=CAR, headers=h)
    assert client.post('/account/delete', headers=h, json={'password': 'wrong-pass1'}).status_code == 422
    r = client.post('/account/delete', headers=h, json={'password': PASSWORD})
    assert r.status_code == 200 and r.json()['estimates_deleted'] == 1
    assert login(email, PASSWORD).status_code == 401
    assert client.get('/me', headers=h).status_code == 401
    rows = sqlite3.connect(settings.USAGE_DB_PATH).execute('SELECT COUNT(*) FROM searches WHERE user = ?', (email,))
    assert rows.fetchone()[0] == 0


def test_deleted_account_token_loses_access_immediately():
    email, _ = new_user()
    h = {'token': login(email, PASSWORD).json()['access_token'], 'api-key': settings.API_KEY}
    assert client.get('/history', headers=h).status_code == 200
    assert client.post('/account/delete', headers=h, json={'password': PASSWORD}).status_code == 200
    # the old, unexpired token must not keep working (nor re-create history for the deleted account)
    assert client.post('/predict', json=CAR, headers=h).status_code == 401
    assert client.get('/history', headers=h).status_code == 401
    assert client.get('/stats', headers=h).status_code == 401
    rows = sqlite3.connect(settings.USAGE_DB_PATH).execute('SELECT COUNT(*) FROM searches WHERE user = ?', (email,))
    assert rows.fetchone()[0] == 0


# ---- lock-out ----

def test_lockout_after_repeated_failures():
    email, _ = new_user()
    for _ in range(settings.LOGIN_MAX_FAILURES):
        assert login(email, 'wrong-pass1').status_code == 401
    locked = login(email, PASSWORD)  # even the right password is refused while locked
    assert locked.status_code == 429 and 'Try again' in locked.json()['detail']


def test_successful_login_resets_failure_count():
    email, _ = new_user()
    for _ in range(settings.LOGIN_MAX_FAILURES - 1):
        login(email, 'wrong-pass1')
    assert login(email, PASSWORD).status_code == 200
    assert login(email, 'wrong-pass1').status_code == 401  # counting started again, not locked


# ---- forgot / reset password ----

def test_forgot_password_unavailable_without_email_setup(monkeypatch):
    monkeypatch.setattr(settings, 'SMTP_HOST', '')
    assert client.post('/password/forgot', json={'email': 'a@b.com'}).status_code == 503


def test_forgot_password_same_answer_for_unknown_email(outbox):
    r = client.post('/password/forgot', json={'email': 'nobody@example.com'})
    assert r.status_code == 202 and 'If an account exists' in r.json()['detail'] and outbox == []


def test_reset_password_with_emailed_code(outbox):
    email, _ = new_user()
    assert client.post('/password/forgot', json={'email': email.upper()}).status_code == 202
    code = re.search(r'\b(\d{6})\b', outbox[-1]['body']).group(1)
    wrong = '000000' if code != '000000' else '111111'
    assert client.post('/password/reset', json={'email': email, 'code': wrong, 'new_password': 'Res3tPass'}).status_code == 422
    assert client.post('/password/reset', json={'email': email, 'code': code, 'new_password': 'Res3tPass'}).status_code == 200
    assert login(email, 'Res3tPass').status_code == 200
    assert client.post('/password/reset', json={'email': email, 'code': code,
                                                'new_password': 'An0therPass'}).status_code == 422  # single use


def test_reset_code_locked_after_five_wrong_guesses(outbox):
    email, _ = new_user()
    client.post('/password/forgot', json={'email': email})
    code = re.search(r'\b(\d{6})\b', outbox[-1]['body']).group(1)
    wrong = '000000' if code != '000000' else '111111'
    for _ in range(5):
        client.post('/password/reset', json={'email': email, 'code': wrong, 'new_password': 'Res3tPass'})
    r = client.post('/password/reset', json={'email': email, 'code': code, 'new_password': 'Res3tPass'})
    assert r.status_code == 422 and 'expired' in r.json()['detail']


def test_reset_requests_limited_per_hour(outbox):
    email, _ = new_user()
    for _ in range(5):
        client.post('/password/forgot', json={'email': email})
    assert len(outbox) == 3


# ---- history + forecast ----

def test_history_is_private_and_newest_first():
    a_email, a = new_user()
    _, b = new_user()
    client.post('/predict', json=CAR, headers=a)
    client.post('/predict', json=dict(CAR, km_driven=90000), headers=a)
    history = client.get('/history', headers=a).json()
    assert [h['car']['km_driven'] for h in history] == [90000, 60000]
    assert history[0]['result']['price'] > 0 and 'forecast' in history[0]['result']
    assert client.get('/history', headers=b).json() == []


def test_forecast_never_rises_and_uses_own_km_rate():
    _, h = new_user()
    body = client.post('/predict', json=CAR, headers=h).json()
    prices = [body['price']] + [f['price'] for f in body['forecast']]
    assert [f['years'] for f in body['forecast']] == [1, 2, 3]
    assert prices == sorted(prices, reverse=True)
    assert body['forecast_km_per_year'] > 0


# ---- share quotation ----

def share(h, **changes):
    data = {'to': 'customer@example.com', 'filename': 'QT-20260930-ABC123.pdf',
            'pdf_base64': base64.b64encode(b'%PDF-1.4 test').decode(), 'message': 'Hello'}
    return client.post('/share/quotation', headers=h, json=dict(data, **changes))


def test_share_quotation_unavailable_without_email_setup(monkeypatch):
    monkeypatch.setattr(settings, 'SMTP_HOST', '')
    _, h = new_user()
    assert share(h).status_code == 503


def test_share_quotation_sends_pdf(outbox):
    _, h = new_user()
    assert share(h, to='not-an-email').status_code == 422
    assert share(h, pdf_base64=base64.b64encode(b'not a pdf').decode()).status_code == 422
    assert share(h, filename='../../etc/passwd').status_code == 422
    assert share(h).status_code == 202
    mail = outbox[-1]
    assert mail['to'] == 'customer@example.com' and mail['body'].startswith('Hello')
    assert mail['attachments'][0][0] == 'QT-20260930-ABC123.pdf'


def test_share_quotation_daily_limit(outbox, monkeypatch):
    monkeypatch.setattr(settings, 'EMAILS_PER_USER_PER_DAY', 2)
    _, h = new_user()
    assert [share(h).status_code for _ in range(3)] == [202, 202, 429]


# ---- admin ----

def test_admin_stats_admin_only():
    _, h = new_user()
    client.post('/predict', json=CAR, headers=h)
    assert client.get('/admin/stats', headers=h).status_code == 403
    token = client.post('/login', json={'username': settings.ADMIN_USERNAME,
                                        'password': settings.ADMIN_PASSWORD}).json()['access_token']
    stats = client.get('/admin/stats', headers={'token': token, 'api-key': settings.API_KEY}).json()
    assert stats['registered_users'] >= 1 and stats['total_estimates'] >= 1 and stats['active_users'] >= 1


def test_admin_cannot_change_or_delete_env_account():
    token = client.post('/login', json={'username': settings.ADMIN_USERNAME,
                                        'password': settings.ADMIN_PASSWORD}).json()['access_token']
    assert client.post('/account/delete', headers={'token': token}, json={'password': 'x'}).status_code == 400


# ---- backups ----

def test_backup_copies_databases_and_keeps_newest(tmp_path):
    db = tmp_path / 'users.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE t (x)')
        conn.execute('INSERT INTO t VALUES (42)')
    target = tmp_path / 'backups'
    for i in range(4):
        (target / f'users-2020010{i}-000000.db').parent.mkdir(exist_ok=True)
        sqlite3.connect(target / f'users-2020010{i}-000000.db').close()
    written = backup.backup_once([str(db)], str(target), keep=3)
    assert len(written) == 1 and sqlite3.connect(written[0]).execute('SELECT x FROM t').fetchone() == (42,)
    assert len(list(target.glob('users-*.db'))) == 3


def test_failed_email_does_not_use_up_reset_allowance(monkeypatch, outbox):
    email, _ = new_user()

    def broken(*args, **kwargs):
        raise OSError('smtp down')
    monkeypatch.setattr(mailer, 'send_email', broken)
    for _ in range(4):
        assert client.post('/password/forgot', json={'email': email}).status_code == 503
    sent = []
    monkeypatch.setattr(mailer, 'send_email', lambda to, subject, body, attachments=None: sent.append(body))
    assert client.post('/password/forgot', json={'email': email}).status_code == 202 and len(sent) == 1
