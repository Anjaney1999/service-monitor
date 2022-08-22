from datetime import datetime
import os
import asyncio
import mysql.connector
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import argparse
import threading
import httpx
import pandas as pd
import json
import redis
from databases import Database
import logging
import mysql.connector

from service_monitor.shared.crud import add_url_db, dequeue_new_urls
from service_monitor.shared.utils import init_database


logging.basicConfig()
logger = logging.getLogger('compute')
logger.setLevel(level=logging.DEBUG)

def add_new_urls(cache, data):
    # dequeue all new URLs from cache and add them to dataframe of URLs
    for url in dequeue_new_urls(cache):
        data.loc[len(data)] = json.loads(url)

async def fetch(db, row, sem, client, timestamp):
    # send request to URL and based on response add entry to database (success/fail)
    async with sem: 
        status = 'fail'
        try:
            response = await client.get(row['url'])
            # raise exception for 4xx, 5xx status codes
            response.raise_for_status()
            # set status to "success" if request returned proper response
            status = 'success'
        except Exception as e:
            logger.info(f"Request to {row['url']} failed: {str(e)}")
        
        # add new entry to database                
        await add_url_db(db, row['name'], row['url'], status, timestamp)
        
async def compute(db, sem, data, timestamp):
    timeout = httpx.Timeout(timeout=int(os.getenv('TIMEOUT')))
    limits = httpx.Limits(max_connections=int(os.getenv('MAX_POOL')), 
                          max_keepalive_connections=int(os.getenv('MIN_POOL')))
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        coroutines = []
        # iterate over each URL to process
        for _, row in data.iterrows():
            coroutines.append(fetch(db, row, sem, client, timestamp))
        await asyncio.gather(*coroutines)
    

async def process(data): 
    timestamp = datetime.now()
    logger.info(f"Running process at {timestamp}")
    
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    DB_ADDRESS = os.getenv('DB_ADDRESS')
    DB_PORT = os.getenv('DB_PORT')
    MAX_POOL = os.getenv('MAX_POOL')
    MIN_POOL = os.getenv('MIN_POOL')
    CACHE_ADDRESS = os.getenv('CACHE_ADDRESS')
    CACHE_PORT = os.getenv('CACHE_PORT')
    
    # init database with expected table
    db = mysql.connector.connect(
        host=os.getenv('DB_ADDRESS'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    init_database(db)
    db.close()

    #init async client
    url = f'mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_ADDRESS}:{DB_PORT}/{DB_NAME}?min_size={MIN_POOL}&max_size={MAX_POOL}'
    database = Database(url)
    await database.connect() 
    #init cache
    cache = redis.Redis(host=CACHE_ADDRESS, port=int(CACHE_PORT), db=0)
    
    # init semaphore to ensure too many connections are not created at the same time
    sem = asyncio.Semaphore(int(MAX_POOL))
    try:
        # add new URLs to dataframe of URLs
        add_new_urls(cache, data)
        # check status of each URL
        await compute(database, sem, data, timestamp)
    except Exception as e:
        logger.error(str(e))
    
    # disconnect from database
    await database.disconnect()
           
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    
    # if running local, the program starts a scheduler that runs every 10 minutes
    ap.add_argument("--run-local", action='store_true')
    ap.add_argument("--data-path", default='data/urls.csv', type=str)
    args = ap.parse_args()
    
    # read urls
    data = pd.read_csv(args.data_path)
    # run at regular intervals or run once
    if args.run_local:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(process, 'interval', args=(data,), seconds=2)
        scheduler.start()
        asyncio.get_event_loop().run_forever()
    else:
        asyncio.run(process(data))

    
    