from datetime import datetime, timedelta
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
import httpx
import pytest
import pandas as pd
import asyncio
import os
import json
import redis
from service_monitor.shared.crud import enqueue_new_url
from service_monitor.compute.scheduler import process

@pytest.mark.asyncio
@freeze_time('2020-01-01')
async def test_process_no_new_urls(httpx_mock: HTTPXMock, db, init_env, init_cache):

    def custom_response(request: httpx.Request):
        if request.url == 'http://www.a.com':
            return httpx.Response(status_code=200, json={})
        if request.url == 'http://www.b.com':
            return httpx.Response(status_code=400, json={})
    httpx_mock.add_callback(custom_response)
    httpx_mock.add_exception(exception=httpx.TimeoutException('timeout'), url='http://www.c.com')
    
    data = pd.DataFrame([
        ('a', 'http://www.a.com'),
        ('b', 'http://www.b.com'),
        ('c', 'http://www.c.com'),
    ], columns=['name', 'url'])
    
    await process(data)
    
    cursor = db.cursor()
    cursor.execute(f"SELECT name, url, creation_date FROM {os.environ['DB_NAME']}.urls")
    result = cursor.fetchall()     
    cursor.execute(f"TRUNCATE TABLE {os.environ['DB_NAME']}.urls")
    cursor.close()
    
    expected = [
        ('a', 'http://www.a.com', datetime.now()),
        ('b', 'http://www.b.com', datetime.now()),
        ('c', 'http://www.c.com', datetime.now())
    ]
    
    assert set(result) == set(expected)

@pytest.mark.asyncio
@freeze_time('2020-01-01')
async def test_process_add_new_urls(httpx_mock: HTTPXMock, db, init_env, init_cache):

    def custom_response(request: httpx.Request):
        if request.url == 'http://www.a.com':
            return httpx.Response(status_code=200, json={})
        if request.url == 'http://www.b.com':
            return httpx.Response(status_code=400, json={})
        if request.url == 'http://www.d.com':
            return httpx.Response(status_code=200, json={})
        if request.url == 'http://www.e.com':
            return httpx.Response(status_code=400, json={})
    
    httpx_mock.add_callback(custom_response)
    httpx_mock.add_exception(exception=httpx.TimeoutException('timeout'), url='http://www.c.com')
    
    data = pd.DataFrame([
        ('a', 'http://www.a.com'),
        ('b', 'http://www.b.com'),
        ('c', 'http://www.c.com'),
    ], columns=['name', 'url'])
    
    cache = redis.Redis()
    enqueue_new_url(cache, json.dumps({'name': 'd', 'url': 'http://www.d.com'}))
    enqueue_new_url(cache, json.dumps({'name': 'e', 'url': 'http://www.e.com'}))
    
    await process(data)
    
    cursor = db.cursor()
    cursor.execute(f"SELECT name, url, status, creation_date FROM {os.environ['DB_NAME']}.urls")
    result = cursor.fetchall()     
    cursor.execute(f"TRUNCATE TABLE {os.environ['DB_NAME']}.urls")
    cursor.close()
    
    expected = [
        ('a', 'http://www.a.com', 'success', datetime.now()),
        ('b', 'http://www.b.com', 'fail', datetime.now()),
        ('c', 'http://www.c.com', 'fail', datetime.now()),
        ('d', 'http://www.d.com', 'success', datetime.now()),
        ('e', 'http://www.e.com', 'fail', datetime.now()),
    ]
    
    assert set(result) == set(expected)
    
    
    