import sys
import os
sys.path.append(os.getcwd())

from app.services.news_fetcher import fetch_news
from app.database import init_db
from flask import Flask

app = Flask(__name__)
app.config["MONGODB_URI"] = "mongodb://localhost:27017/"
app.config["MONGODB_DB_NAME"] = "news_sentiment_intelligence_db"

with app.app_context():
    init_db(app)
    from app.services.news_fetcher import fetch_news
    context = {
        'limit': 10,
        'city': 'unknown',
        'state': 'unknown',
        'country': 'unknown',
        'continent': 'unknown',
        'category': 'unknown',
        'source': 'unknown',
        'analyzed': 'false'
    }
    res = fetch_news(context, query_language=['hi'])
    print(f"Status: {res.get('status')}")
    print(f"Count: {res.get('count')}")
    print(f"Total: {res.get('total')}")
    print(f"HasMore: {res.get('has_more')}")
    print(f"NextCursor: {res.get('next_cursor') is not None}")
    if res.get('articles'):
        print(f"First Article: {res['articles'][0]['title']}")
    else:
        print("No articles found.")
