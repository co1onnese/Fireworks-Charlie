#!/usr/bin/env python3
"""Check news availability in 2024"""
import os
import sys

sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config
from data_collection.database_manager import DatabaseManager, Ticker, News
from sqlalchemy import func

db_manager = DatabaseManager(config.DB_URL)
session = db_manager.get_session()

# Check NFLX news in 2024
ticker = session.query(Ticker).filter_by(symbol='NFLX').first()
all_nflx_news = session.query(News).filter(News.ticker_id == ticker.ticker_id).all()

print(f"NFLX News in database: {len(all_nflx_news)} articles")
if all_nflx_news:
    print(f"Date range: {all_nflx_news[0].published_at} to {all_nflx_news[-1].published_at}")

# Check 2024 news across all tickers
print("\n" + "="*80)
print("News by ticker in 2024:")
result = session.query(
    Ticker.symbol,
    func.count(News.news_id).label('count')
).join(
    News, Ticker.ticker_id == News.ticker_id
).filter(
    News.published_at >= '2024-01-01',
    News.published_at < '2025-01-01'
).group_by(
    Ticker.symbol
).order_by(
    func.count(News.news_id).desc()
).limit(10)

for row in result:
    print(f"  {row.symbol}: {row.count} articles")

session.close()
