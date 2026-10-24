import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from app.core.config import settings


def _connect():
    os.makedirs(os.path.dirname(settings.USAGE_DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(settings.USAGE_DB_PATH)
    conn.execute(
        'CREATE TABLE IF NOT EXISTS searches (ts TEXT, company TEXT, model TEXT, edition TEXT, '
        'year INTEGER, km_driven REAL, fuel TEXT, price REAL)'
    )
    columns = {row[1] for row in conn.execute('PRAGMA table_info(searches)')}
    for column in ('user', 'payload', 'result'):  # added for "My estimates"; older rows keep NULL
        if column not in columns:
            conn.execute(f'ALTER TABLE searches ADD COLUMN {column} TEXT')
    return conn


def log_search(car: dict, result: dict, user: str | None = None):
    # usage stats must never break a prediction
    try:
        with _connect() as conn:
            conn.execute('INSERT INTO searches (ts, company, model, edition, year, km_driven, fuel, price, user, '
                         'payload, result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                             datetime.now(timezone.utc).isoformat(timespec='seconds'), car['company'], car['model'],
                             car['edition'], car['year'], car['km_driven'], car['fuel'], result['price'], user,
                             json.dumps(car), json.dumps(result)))
    except sqlite3.Error as e:
        logging.warning(f'Could not log search: {e}')


def usage_stats(top: int = 10) -> dict:
    with _connect() as conn:
        total = conn.execute('SELECT COUNT(*) FROM searches').fetchone()[0]
        popular = conn.execute(
            'SELECT company, model, COUNT(*) AS searches, ROUND(AVG(price)) AS avg_price FROM searches '
            'GROUP BY LOWER(company), LOWER(model) ORDER BY searches DESC LIMIT ?', (top,)
        ).fetchall()
    return {
        'total_searches': total,
        'most_searched': [dict(zip(['company', 'model', 'searches', 'avg_price'], row)) for row in popular]
    }


def user_history(user: str, limit: int = 50) -> list:
    """The user's own estimates, newest first."""
    with _connect() as conn:
        rows = conn.execute('SELECT ts, payload, result FROM searches WHERE user = ? AND payload IS NOT NULL '
                            'ORDER BY ts DESC, rowid DESC LIMIT ?', (user, limit)).fetchall()
    return [{'ts': ts, 'car': json.loads(payload), 'result': json.loads(result)} for ts, payload, result in rows]


def delete_user_history(user: str) -> int:
    with _connect() as conn:
        return conn.execute('DELETE FROM searches WHERE user = ?', (user,)).rowcount


def admin_usage(days: int = 30) -> dict:
    with _connect() as conn:
        per_day = conn.execute("SELECT substr(ts, 1, 10) AS day, COUNT(*) FROM searches WHERE ts >= date('now', ?) "
                               'GROUP BY day ORDER BY day', (f'-{days} days',)).fetchall()
        active = conn.execute("SELECT COUNT(DISTINCT user) FROM searches WHERE user IS NOT NULL "
                              "AND ts >= date('now', ?)", (f'-{days} days',)).fetchone()[0]
        by_fuel = conn.execute('SELECT fuel, COUNT(*) FROM searches GROUP BY LOWER(fuel) ORDER BY 2 DESC').fetchall()
    return {'estimates_per_day': [{'day': d, 'estimates': n} for d, n in per_day],
            'active_users': active,
            'estimates_by_fuel': [{'fuel': f, 'estimates': n} for f, n in by_fuel]}
