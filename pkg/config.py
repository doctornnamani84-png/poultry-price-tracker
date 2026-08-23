import os
from urllib.parse import quote_plus


def get_database_uri():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url

    host = os.environ.get('DB_HOST', 'localhost')
    user = os.environ.get('DB_USER', 'root')
    password = os.environ.get('DB_PASSWORD', '')
    port = os.environ.get('DB_PORT', '3306')
    name = os.environ.get('DB_NAME', 'poultry_price_tracker')
    encoded_user = quote_plus(user)
    encoded_password = quote_plus(password)
    auth = f'{encoded_user}:{encoded_password}' if password else encoded_user
    return f'mysql+mysqlconnector://{auth}@{host}:{port}/{name}'


class GeneralConfig(object):
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-this')
    TECH_SUPPORT = '08064289872'
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class LiveConfig(GeneralConfig):
    SECRET_KEY = os.environ.get('LIVE_SECRET_KEY', 'live_nB8N2P1-epu-1g')
    ADMIN_EMAIL = 'live@admin.com'


class TestConfig(GeneralConfig):
    ADMIN_EMAIL = 'test@admin.com'
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False