import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import redis
import mysql.connector
from databases import Database

from service_monitor.shared import schemas
from service_monitor.shared.utils import construct_output, init_database
from service_monitor.shared.crud import (
    update_top_stats_cache, get_top_stats_cache, get_top_stats_db, 
    enqueue_new_url, get_status_summary_cache, get_status_summary_db,
    update_summary_cache
)

app = FastAPI()


@app.on_event("startup")
async def startup():
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    DB_ADDRESS = os.getenv('DB_ADDRESS')
    DB_PORT = os.getenv('DB_PORT')
    MAX_POOL = os.getenv('MAX_POOL')
    MIN_POOL = os.getenv('MIN_POOL')
    CACHE_ADDRESS = os.getenv('CACHE_ADDRESS')
    CACHE_PORT = os.getenv('CACHE_PORT')

    db = mysql.connector.connect(
        host=os.getenv('DB_ADDRESS'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    # init database with the required table
    init_database(db)
    db.close()
    
    # init async database client
    url = f'mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_ADDRESS}:{DB_PORT}/{DB_NAME}?min_size={MIN_POOL}&max_size={MAX_POOL}'
    app.state.database = Database(url)
    await app.state.database.connect()
    
    # init redis client
    app.state.redis = redis.Redis(host=CACHE_ADDRESS, port=int(CACHE_PORT), db=0)


@app.on_event("shutdown")
async def shutdown():
    await app.state.database.disconnect()
    
@app.get("/urls/summary")
async def summary(cache: bool = True): 
    # if cache query param true, ignore cache
    if cache: 
        summary = get_status_summary_cache(app.state.redis)
        if summary:
            return JSONResponse(content=json.loads(summary), headers={'cached': 'true'})
    
    # get summary from database
    result = await get_status_summary_db(app.state.database)
    summary = construct_output(result, ['status', 'count'])
    
    # update cache
    update_summary_cache(app.state.redis, summary)
    
    return JSONResponse(content=summary, headers={'cached': 'false'})

@app.post('/urls/')
async def create_url(url: schemas.URL):
    # push new URL to redis
    return enqueue_new_url(app.state.redis, url.json())

@app.get("/urls/top/{status}/{timespan}")
async def top_errors(status, timespan, cache: bool = True):
    # if cache query param true, ignore cache  
    if cache:  
        top_stats = get_top_stats_cache(app.state.redis, timespan, status)
        if top_stats:
            return JSONResponse(content=json.loads(top_stats), headers={'cached': 'true'})
    
    # get start datetime based on supplied timespan  
    start_datetime = None
    if timespan == 'hour':
        start_datetime = datetime.now() - timedelta(hours=1)
    elif timespan == 'week':
        start_datetime = datetime.now() - timedelta(days=7)
    elif timespan == 'month':
        start_datetime = datetime.now() - timedelta(days=30)
    else:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    # get URLs with the highest number of either success or fail requests
    # depending on supplied status
    result = await get_top_stats_db(app.state.database, start_datetime, status)
    top_stats = construct_output(result, ['name', 'url', 'count'])
    
    # update cache
    update_top_stats_cache(app.state.redis, top_stats, timespan, status)
    
    return JSONResponse(content=top_stats, headers={'cached': 'false'}) 

@app.get("/status", status_code=200)
async def status():
    # healthcheck
    return "healthy"


