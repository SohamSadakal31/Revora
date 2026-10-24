"""User accounts stored in SQLite, identified by email. Passwords are kept only as salted PBKDF2-SHA256 hashes."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from app.core.config import settings

PBKDF2_ITERATIONS = 310_000  # OWASP recommendation for PBKDF2-HMAC-SHA256
EMAIL_RULE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class UserError(ValueError):
    pass


class UserExistsError(UserError):
    pass


def _connect():
    os.makedirs(os.path.dirname(settings.USERS_DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(settings.USERS_DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, full_name TEXT, password_hash TEXT, '
                 'created_at TEXT)')
    if 'email' not in {row[1] for row in conn.execute('PRAGMA table_info(users)')}:
        conn.execute('ALTER TABLE users ADD COLUMN email TEXT')  # accounts created before email existed
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS users_email ON users(email)')
    return conn


def _hash(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, PBKDF2_ITERATIONS)
    return f'pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}'


def _matches(password: str, stored: str) -> bool:
    _, iterations, salt, digest = stored.split('$')
    candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(candidate.hex(), digest)


def normalise_email(email: str) -> str:
    return email.strip().lower()


def check_password_rules(password: str):
    if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        raise UserError('Password must be at least 8 characters and contain a letter and a number.')


def create_user(email: str, password: str, full_name: str = '') -> dict:
    email = normalise_email(email)
    if len(email) > 254 or not EMAIL_RULE.match(email):
        raise UserError('Enter a valid email address.')
    check_password_rules(password)
    with _connect() as conn:
        try:
            # the email is the account id (stored as both username and email)
            conn.execute('INSERT INTO users (username, full_name, password_hash, created_at, email) '
                         'VALUES (?, ?, ?, ?, ?)', (email, full_name.strip()[:60],
                                                    _hash(password, secrets.token_bytes(16)),
                                                    datetime.now(timezone.utc).isoformat(timespec='seconds'), email))
        except sqlite3.IntegrityError:
            raise UserExistsError('An account with this email already exists.')
    return {'email': email, 'full_name': full_name.strip()[:60]}


def authenticate(email: str, password: str) -> dict | None:
    """The user's details if the password is right, else None."""
    with _connect() as conn:
        row = conn.execute('SELECT email, full_name, password_hash FROM users WHERE email = ?',
                           (normalise_email(email),)).fetchone()
    if row is None:
        _matches(password, _hash('dummy-password', b'0' * 16))  # same work either way: no timing hint
        return None
    return {'email': row[0], 'full_name': row[1]} if _matches(password, row[2]) else None


def get_user(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute('SELECT email, full_name FROM users WHERE email = ?', (normalise_email(email),)).fetchone()
    return {'email': row[0], 'full_name': row[1]} if row else None


# ---------------- password change / account deletion ----------------

def _set_password(email: str, password: str):
    with _connect() as conn:
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?',
                     (_hash(password, secrets.token_bytes(16)), normalise_email(email)))


def change_password(email: str, current_password: str, new_password: str):
    if authenticate(email, current_password) is None:
        raise UserError('Your current password is not correct.')
    check_password_rules(new_password)
    _set_password(email, new_password)


def delete_user(email: str, password: str):
    """Deletes the account (the caller also deletes the user's history)."""
    if authenticate(email, password) is None:
        raise UserError('Your password is not correct.')
    with _connect() as conn:
        _security_tables(conn)
        conn.execute('DELETE FROM users WHERE email = ?', (normalise_email(email),))
        conn.execute('DELETE FROM password_resets WHERE email = ?', (normalise_email(email),))
        conn.execute('DELETE FROM login_failures WHERE login = ?', (normalise_email(email),))


def count_users() -> int:
    with _connect() as conn:
        return conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]


def signups_per_day(days: int = 30) -> list:
    with _connect() as conn:
        return conn.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) FROM users "
            "WHERE created_at >= date('now', ?) GROUP BY day ORDER BY day", (f'-{days} days',)).fetchall()


# ---------------- failed-login lock-out ----------------

def _security_tables(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS login_failures (login TEXT, ts TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS password_resets (email TEXT, code_hash TEXT, expires_at TEXT, '
                 'attempts INTEGER, created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS email_log (sender TEXT, ts TEXT)')


def _now() -> datetime:
    return datetime.now(timezone.utc)


def minutes_locked(login: str) -> int:
    """Minutes until this login may try again (0 = not locked)."""
    with _connect() as conn:
        _security_tables(conn)
        since = (_now() - timedelta(minutes=settings.LOGIN_LOCK_MINUTES)).isoformat()
        rows = conn.execute('SELECT ts FROM login_failures WHERE login = ? AND ts >= ? ORDER BY ts',
                            (login.strip().lower(), since)).fetchall()
    if len(rows) < settings.LOGIN_MAX_FAILURES:
        return 0
    unlock = datetime.fromisoformat(rows[-settings.LOGIN_MAX_FAILURES][0]) + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
    return max(1, -(-int((unlock - _now()).total_seconds()) // 60))


def record_failed_login(login: str):
    with _connect() as conn:
        _security_tables(conn)
        conn.execute('INSERT INTO login_failures VALUES (?, ?)', (login.strip().lower(), _now().isoformat()))


def clear_failed_logins(login: str):
    with _connect() as conn:
        _security_tables(conn)
        conn.execute('DELETE FROM login_failures WHERE login = ?', (login.strip().lower(),))


# ---------------- password reset codes ----------------

def _code_hash(email: str, code: str) -> str:
    return hashlib.sha256(f'{settings.JWT_SECRET_KEY}|{email}|{code}'.encode()).hexdigest()


def create_reset_code(email: str) -> str | None:
    """A 6-digit code for an existing account (None if there is no such account or too many requests)."""
    email = normalise_email(email)
    if get_user(email) is None:
        return None
    with _connect() as conn:
        _security_tables(conn)
        hour_ago = (_now() - timedelta(hours=1)).isoformat()
        if conn.execute('SELECT COUNT(*) FROM password_resets WHERE email = ? AND created_at >= ?',
                        (email, hour_ago)).fetchone()[0] >= 3:
            return None
        code = f'{secrets.randbelow(1_000_000):06d}'
        conn.execute('DELETE FROM password_resets WHERE email = ? AND created_at < ?', (email, hour_ago))
        conn.execute('INSERT INTO password_resets VALUES (?, ?, ?, 0, ?)', (
            email, _code_hash(email, code),
            (_now() + timedelta(minutes=settings.RESET_CODE_MINUTES)).isoformat(), _now().isoformat()))
    return code


def reset_password(email: str, code: str, new_password: str):
    email = normalise_email(email)
    check_password_rules(new_password)
    with _connect() as conn:
        _security_tables(conn)
        row = conn.execute('SELECT rowid, code_hash, expires_at, attempts FROM password_resets WHERE email = ? '
                           'ORDER BY created_at DESC LIMIT 1', (email,)).fetchone()
        if row is None or row[3] >= 5 or datetime.fromisoformat(row[2]) < _now():
            raise UserError('This code is invalid or has expired. Please request a new one.')
        correct = hmac.compare_digest(row[1], _code_hash(email, code.strip()))
        if correct:
            conn.execute('DELETE FROM password_resets WHERE email = ?', (email,))
        else:  # counted outside the error, so the transaction keeps it (max 5 guesses per code)
            conn.execute('UPDATE password_resets SET attempts = attempts + 1 WHERE rowid = ?', (row[0],))
    if not correct:
        raise UserError('This code is not correct.')
    _set_password(email, new_password)
    clear_failed_logins(email)


# ---------------- outgoing email limit ----------------

def email_allowed(sender: str) -> bool:
    with _connect() as conn:
        _security_tables(conn)
        day_ago = (_now() - timedelta(days=1)).isoformat()
        sent = conn.execute('SELECT COUNT(*) FROM email_log WHERE sender = ? AND ts >= ?', (sender, day_ago)).fetchone()[0]
        if sent >= settings.EMAILS_PER_USER_PER_DAY:
            return False
        conn.execute('INSERT INTO email_log VALUES (?, ?)', (sender, _now().isoformat()))
    return True


def discard_reset_codes(email: str):
    """Forget unsent codes, so a failed email does not use up the hourly reset allowance."""
    with _connect() as conn:
        _security_tables(conn)
        conn.execute('DELETE FROM password_resets WHERE email = ?', (normalise_email(email),))
