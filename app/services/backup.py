"""Backups of the SQLite databases (user accounts, usage log).

    python -m app.services.backup          # one backup now
    python -m app.services.backup --loop   # backup now and every BACKUP_INTERVAL_HOURS (the `backup` service)

Uses SQLite's online backup API, so it is safe while the app is running. Keeps the newest BACKUP_KEEP copies of each.
"""
import argparse
import glob
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s backup: %(message)s')


def backup_once(databases=None, backup_dir=None, keep=None) -> list:
    databases = databases or [settings.USERS_DB_PATH, settings.USAGE_DB_PATH]
    backup_dir = backup_dir or settings.BACKUP_DIR
    keep = keep or settings.BACKUP_KEEP
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    written = []
    for db in databases:
        if not os.path.exists(db):
            continue
        name = os.path.splitext(os.path.basename(db))[0]
        target = os.path.join(backup_dir, f'{name}-{stamp}.db')
        with sqlite3.connect(db) as source, sqlite3.connect(target) as copy:
            source.backup(copy)
        written.append(target)
        for old in sorted(glob.glob(os.path.join(backup_dir, f'{name}-*.db')))[:-keep]:
            os.remove(old)
    logging.info('wrote %s', ', '.join(written) or 'nothing (no databases yet)')
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--loop', action='store_true')
    loop = ap.parse_args().loop
    while True:
        try:
            backup_once()
        except Exception:
            logging.exception('backup failed')
        if not loop:
            break
        time.sleep(settings.BACKUP_INTERVAL_HOURS * 3600)


if __name__ == '__main__':
    main()
