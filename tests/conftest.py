

import pytest
from unittest import mock
import fakeredis
from unittest import mock
import redis
from datetime import datetime, timedelta
import mysql.connector
from freezegun import freeze_time
from service_monitor.shared.utils import init_database
import os

@pytest.fixture(scope='session')
def init_env():
    env_vars = {
        'DB_USER': 'root',
        'DB_PASSWORD': 'password',  
        'DB_NAME': 'testdatabase',
        'DB_PORT': '3306',
        'DB_ADDRESS': 'localhost',
        'CACHE_ADDRESS': 'localhost',
        'CACHE_PORT': '8000',
        'MAX_POOL': '100',
        'MIN_POOL': '5',
        'TIMEOUT': '1',
    } 
    with mock.patch.dict(os.environ, env_vars):
        yield

@pytest.fixture(scope='function')
def init_cache():
    server = fakeredis.FakeServer()
    with mock.patch('redis.Redis', return_value=fakeredis.FakeStrictRedis(version=6, server=server)):
        yield
        redis.Redis().flushdb()

@pytest.fixture(scope='module')
def db(init_env):
    db = mysql.connector.connect(
        host=os.getenv('DB_ADDRESS'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cursor = db.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {os.getenv('DB_NAME')}")
    init_database(db)
    yield db
    cursor.execute(f"DROP DATABASE IF EXISTS {os.getenv('DB_NAME')}")
    cursor.close()
    db.close()