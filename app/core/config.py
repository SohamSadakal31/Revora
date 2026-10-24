import logging
import os
from dotenv import load_dotenv

load_dotenv()

DEV_DEFAULTS = {'API_KEY': 'demo-key', 'JWT_SECRET_KEY': 'secret', 'ADMIN_PASSWORD': 'admin'}


class Settings:
    PROJECT_NAME = 'Car Price API'
    API_KEY = os.getenv('API_KEY', DEV_DEFAULTS['API_KEY'])
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', DEV_DEFAULTS['JWT_SECRET_KEY'])
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', '30'))
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', DEV_DEFAULTS['ADMIN_PASSWORD'])
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    MODEL_PATH = os.getenv('MODEL_PATH', 'app/models/model.joblib')
    MODEL_RANGE_PATH = os.getenv('MODEL_RANGE_PATH', 'app/models/model_range.joblib')
    MODEL_META_PATH = os.getenv('MODEL_META_PATH', 'app/models/model_meta.json')
    USAGE_DB_PATH = os.getenv('USAGE_DB_PATH', 'logs/usage.db')
    USERS_DB_PATH = os.getenv('USERS_DB_PATH', 'logs/users.db')
    # security
    LOGIN_MAX_FAILURES = int(os.getenv('LOGIN_MAX_FAILURES', '5'))       # failed logins before a lock-out ...
    LOGIN_LOCK_MINUTES = int(os.getenv('LOGIN_LOCK_MINUTES', '15'))      # ... lasting this long
    RESET_CODE_MINUTES = int(os.getenv('RESET_CODE_MINUTES', '30'))      # password-reset codes expire after this
    EMAILS_PER_USER_PER_DAY = int(os.getenv('EMAILS_PER_USER_PER_DAY', '20'))
    # outgoing email (password reset, sharing quotations) - disabled until SMTP_HOST and SMTP_FROM are set
    APP_NAME = os.getenv('QUOTE_BUSINESS_NAME', 'Revora')
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM = os.getenv('SMTP_FROM', '')
    SMTP_STARTTLS = os.getenv('SMTP_STARTTLS', 'true').lower() == 'true'
    # database backups (backup service)
    BACKUP_DIR = os.getenv('BACKUP_DIR', 'logs/backups')
    BACKUP_KEEP = int(os.getenv('BACKUP_KEEP', '14'))
    BACKUP_INTERVAL_HOURS = float(os.getenv('BACKUP_INTERVAL_HOURS', '24'))


settings = Settings()

for name, default in DEV_DEFAULTS.items():
    if getattr(settings, name) == default:
        logging.warning(f'{name} is using the development default - set it in .env before going live')
