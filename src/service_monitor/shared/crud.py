import json
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, insert

from service_monitor.shared import models

TOP_KEY = 'top_{timespan}_{status}'
TOP_STATS_LAST_MODIFIED_KEY = 'top_last_modified_{timespan}_{status}'
SUMMARY_STATS_LAST_MODIFIED_KEY = 'summary_last_modified'
SUMMARY_STATS_KEY = 'summary'
NEW_URLS_KEY = 'new_urls'

async def get_top_stats_db(db, start_datetime, status):
    """
    Fetch the top 10 entries since {start_datetime} with the 
    highest number of {status} requests from database

    Args:
        db: database client
        start_datetime: Start datetime
        status: success or fail
    """
    query = select(models.URL.name, models.URL.url, func.count())\
            .where(and_(models.URL.status == status, models.URL.creation_date >= start_datetime))\
            .group_by(models.URL.name, models.URL.url)\
            .order_by(func.count().desc())\
            .limit(10)
    
    return await db.fetch_all(query=query)

def get_top_stats_cache(cache, timespan, status):
    """
    Fetch the top 10 entries since {start_datetime} with the 
    highest number of {status} requests from cache if it is not outdated

    Args:
        cache: cache client
        start_datetime: Start datetime
        status: success or fail
    """
    last_modified_key = TOP_STATS_LAST_MODIFIED_KEY.format(timespan=timespan, status=status)
    top_key = TOP_KEY.format(timespan=timespan, status=status)

    if cache.exists(top_key) and cache.exists(last_modified_key):
        last_modified = datetime.fromisoformat(cache.get(last_modified_key).decode("utf-8"))
        if last_modified >= datetime.now() - timedelta(minutes=10):
            return cache.get(top_key).decode("utf-8")
    return None

async def get_status_summary_db(db):
    """
    Get summary of requests during the past month from database
    if not outdated. Returns the number of successful requests and number of failed requests

    Args:
        db: database client
    """
    start_datetime = datetime.now() - timedelta(days=30)    
    query = select(models.URL.status, func.count())\
            .where(models.URL.creation_date >= start_datetime)\
            .group_by(models.URL.status)\
            .order_by(func.count().desc())
    return await db.fetch_all(query=query) 

def get_status_summary_cache(cache):
    """
    Get summary of requests during the past month from cache 
    if not outdated. Returns the number of successful requests and number of failed requests

    Args:
        cache: cache client
    """
    last_modified_key = SUMMARY_STATS_LAST_MODIFIED_KEY
    summary_stats_key = SUMMARY_STATS_KEY

    if cache.exists(summary_stats_key) and cache.exists(last_modified_key):
        last_modified = datetime.fromisoformat(cache.get(last_modified_key).decode("utf-8"))
        if last_modified >= datetime.now() - timedelta(minutes=10):
            return cache.get(summary_stats_key).decode("utf-8")
    return None


def update_cache(cache, data, last_modified_key, data_key):
    pipeline = cache.pipeline()
    pipeline.set(last_modified_key, datetime.now().isoformat())
    pipeline.set(data_key, json.dumps(data))
    pipeline.execute()  
    
def update_top_stats_cache(cache, top_stats, timespan, status):
    last_modified_key = TOP_STATS_LAST_MODIFIED_KEY.format(timespan=timespan, status=status)
    top_key = TOP_KEY.format(timespan=timespan, status=status)
    update_cache(cache, top_stats, last_modified_key, top_key)
    
def update_summary_cache(cache, summary):
    last_modified_key = SUMMARY_STATS_LAST_MODIFIED_KEY
    summary_stats_key = SUMMARY_STATS_KEY
    update_cache(cache, summary, last_modified_key, summary_stats_key)

def enqueue_new_url(cache, url):
    return cache.lpush(NEW_URLS_KEY, url)

def dequeue_new_urls(cache):
    if cache.exists(NEW_URLS_KEY):
        for _ in range(0, cache.llen(NEW_URLS_KEY)):
            yield cache.lpop(NEW_URLS_KEY).decode("utf-8")

async def add_url_db(db, name, url, status, creation_date):
    query = insert(models.URL)\
            .values(name=name, url=url, status=status, creation_date=creation_date)
    await db.execute(query)