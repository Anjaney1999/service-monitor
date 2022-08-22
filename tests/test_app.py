from datetime import datetime, timedelta
from ipaddress import summarize_address_range
from fastapi.testclient import TestClient
from freezegun import freeze_time
import json
import redis
import pytest
import fakeredis
import os
from unittest import mock
from service_monitor.api.app import app
from service_monitor.shared.crud import SUMMARY_STATS_KEY, SUMMARY_STATS_LAST_MODIFIED_KEY, TOP_STATS_LAST_MODIFIED_KEY, TOP_KEY, dequeue_new_urls

@pytest.fixture(scope='module')
@freeze_time('2020-01-01')
def input_data():
    now = datetime.now()
    hour = now - timedelta(minutes=30)
    week = now - timedelta(days=5)
    month = now - timedelta(days=25)
    return [
        ('a', 'http://www.a.com', 'fail', hour),
        ('a', 'http://www.a.com', 'success', hour),
        ('a', 'http://www.a.com', 'success', hour),
        ('b', 'http://www.b.com', 'fail', hour),
        ('b', 'http://www.b.com', 'fail', hour),
        ('b', 'http://www.b.com', 'success', hour),
        ('a', 'http://www.a.com', 'fail', week),
        ('a', 'http://www.a.com', 'fail', week),
        ('c', 'http://www.c.com', 'success', week),
        ('c', 'http://www.c.com', 'success', week),
        ('c', 'http://www.c.com', 'success', week),
        ('b', 'http://www.b.com', 'success', month),
        ('b', 'http://www.b.com', 'success', month),
        ('b', 'http://www.b.com', 'success', month),
        ('c', 'http://www.c.com', 'fail', month),
        ('c', 'http://www.c.com', 'fail', month),
        ('c', 'http://www.c.com', 'fail', month),
        ('c', 'http://www.c.com', 'fail', month),
        ('c', 'http://www.c.com', 'fail', month),
    ] 

@pytest.fixture(scope='function')
def add_data(db, init_env, input_data):            
    db_name = os.getenv('DB_NAME')
    cursor = db.cursor()
    cursor.execute(f'TRUNCATE TABLE {db_name}.urls')
    cursor.executemany(f'INSERT INTO {db_name}.urls VALUES (%s, %s, %s, %s)', input_data)
    db.commit()
    yield
    cursor.execute(f'TRUNCATE TABLE {db_name}.urls')
    cursor.close()
            
@pytest.mark.parametrize('timespan,expected', [
    ('hour', [
        {'name': 'b', 'url': 'http://www.b.com', 'count': 2},
        {'name': 'a', 'url': 'http://www.a.com', 'count': 1},
    ]), 
    ('week', [
        {'name': 'a', 'url': 'http://www.a.com', 'count': 3},
        {'name': 'b', 'url': 'http://www.b.com', 'count': 2},
        {'name': 'c', 'url': 'http://www.c.com', 'count': 0},
    ]), 
    ('month', [
        {'name': 'c', 'url': 'http://www.a.com', 'count': 5},
        {'name': 'a', 'url': 'http://www.c.com', 'count': 3},
        {'name': 'b', 'url': 'http://www.b.com', 'count': 2},
    ])
])
@freeze_time('2020-01-01')
def test_top_fails_cache_latest(timespan, expected, init_env, init_cache, add_data):
    last_modified_key = TOP_STATS_LAST_MODIFIED_KEY.format(timespan=timespan, status='fail')
    top_key = TOP_KEY.format(timespan=timespan, status='fail')
    
    r = redis.Redis()
    r.set(last_modified_key, datetime.now().isoformat())
    r.set(top_key, json.dumps(expected))
    with TestClient(app) as client:
        response = client.get(f"/urls/top/fail/{timespan}")
        
        assert response.status_code == 200
        assert response.headers['cached'] == 'true'
        assert response.json() == expected
        
@pytest.mark.parametrize('timespan,expected', [
    ('hour', [
        {'name': 'b', 'url': 'http://www.b.com', 'count': 2},
        {'name': 'a', 'url': 'http://www.a.com', 'count': 1},
    ]), 
    ('week', [
        {'name': 'a', 'url': 'http://www.a.com', 'count': 3},
        {'name': 'b', 'url': 'http://www.b.com', 'count': 2},
    ]), 
    ('month', [
        {'name': 'c', 'url': 'http://www.c.com', 'count': 5},
        {'name': 'a', 'url': 'http://www.a.com', 'count': 3},
        {'name': 'b', 'url': 'http://www.b.com', 'count': 2},
    ])
])
@freeze_time('2020-01-01')
def test_top_fails_cache_outdated(timespan, expected, init_env, init_cache, add_data):
    last_modified_key = TOP_STATS_LAST_MODIFIED_KEY.format(timespan=timespan, status='fail')
    top_key = TOP_KEY.format(timespan=timespan, status='fail')
    
    r = redis.Redis()
    r.set(last_modified_key, (datetime.now() - timedelta(minutes=20)).isoformat())
    r.set(top_key, json.dumps({'fakedata': 'fakedata'}))
    with TestClient(app) as client:
        response = client.get(f"/urls/top/fail/{timespan}")
        
        assert response.status_code == 200
        assert response.headers['cached'] == 'false'
        assert response.json() == expected
        
        assert r.get(last_modified_key).decode("utf-8") == datetime.now().isoformat()
        assert json.loads(r.get(top_key).decode("utf-8")) == expected

@pytest.mark.parametrize('timespan,expected', [
    ('hour', [
        {'name': 'a', 'url': 'http://www.a.com', 'count': 2},
        {'name': 'b', 'url': 'http://www.b.com', 'count': 1},
    ]), 
    ('week', [
        {'name': 'c', 'url': 'http://www.c.com', 'count': 3},
        {'name': 'a', 'url': 'http://www.a.com', 'count': 2},
        {'name': 'b', 'url': 'http://www.b.com', 'count': 1},
    ]), 
    ('month', [
        {'name': 'b', 'url': 'http://www.b.com', 'count': 4},
        {'name': 'c', 'url': 'http://www.c.com', 'count': 3},
        {'name': 'a', 'url': 'http://www.a.com', 'count': 2},
    ])
])
@freeze_time('2020-01-01')
def test_top_success_cache_outdated(timespan, expected, init_env, init_cache, add_data):
    last_modified_key = TOP_STATS_LAST_MODIFIED_KEY.format(timespan=timespan, status='success')
    top_key = TOP_KEY.format(timespan=timespan, status='success')
    
    r = redis.Redis()
    r.set(last_modified_key, (datetime.now() - timedelta(minutes=20)).isoformat())
    r.set(top_key, json.dumps({'fakedata': 'fakedata'}))
    with TestClient(app) as client:
        response = client.get(f"/urls/top/success/{timespan}")
        
        assert response.status_code == 200
        assert response.headers['cached'] == 'false'
        assert response.json() == expected
        
        assert r.get(last_modified_key).decode("utf-8") == datetime.now().isoformat()
        assert json.loads(r.get(top_key).decode("utf-8")) == expected


def test_create_url(init_env, init_cache):
    with TestClient(app) as client:
        url = {'name': 'f', 'url': 'http://www.f.com'}
        response = client.post("/urls/", json=url)
        
        assert response.json() == 1
        
        cache = redis.Redis()
        
        for element in dequeue_new_urls(cache):
            assert json.loads(element) == url

@freeze_time('2020-01-01')
def test_summary_cache_outdated(init_env, init_cache, add_data):
    last_modified_key = SUMMARY_STATS_LAST_MODIFIED_KEY
    summary_key = SUMMARY_STATS_KEY
    
    r = redis.Redis()
    r.set(last_modified_key, (datetime.now() - timedelta(minutes=20)).isoformat())
    r.set(summary_key, json.dumps({'fakedata': 'fakedata'}))
    with TestClient(app) as client:
        response = client.get("/urls/summary/")
        
        expected = [{'status': 'fail', 'count': 10}, {'status': 'success', 'count': 9}]
        assert response.status_code == 200
        assert response.headers['cached'] == 'false'
        assert response.json() == expected
        
        assert r.get(last_modified_key).decode("utf-8") == datetime.now().isoformat()
        assert json.loads(r.get(summary_key).decode("utf-8")) == expected

@freeze_time('2020-01-01')
def test_summary_cache_latest(init_env, init_cache, add_data):
    last_modified_key = SUMMARY_STATS_LAST_MODIFIED_KEY
    summary_key = SUMMARY_STATS_KEY
    
    expected = [{'status': 'fail', 'count': 10}, {'status': 'success', 'count': 9}]
    r = redis.Redis()
    r.set(last_modified_key, datetime.now().isoformat())
    r.set(summary_key, json.dumps(expected))
    with TestClient(app) as client:
        response = client.get("/urls/summary/")
        
        assert response.status_code == 200
        assert response.headers['cached'] == 'true'
        assert response.json() == expected


    
    
    
    