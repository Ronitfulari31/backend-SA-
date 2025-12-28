"""
Cache clearing script for fixing language inference issues.

⚠️ PRODUCTION: Only clears metadata cache (country_languages)
⚠️ DEV/TEST: Can optionally clear old articles
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from app import create_app
from app.database import init_db, get_db
from app.services.metadata.country_language_service import CountryLanguageService
from datetime import datetime, timedelta

# Set environment to determine if we're in production
IS_PRODUCTION = os.getenv("FLASK_ENV") == "production"


def clear_cache(clear_articles=False):
    """
    Clear caches related to language inference.
    
    Args:
        clear_articles: If True, clears old articles (DEV/TEST ONLY)
    """
    # Initialize Flask app (this also initializes the database)
    app = create_app()
    
    # Get database connection
    db = app.db
    if db is None:
        print("❌ Error: Database connection failed. Check your MongoDB configuration.")
        return
    
    # 1. Clear MongoDB country_languages cache (metadata only, safe)
    print("Clearing country_languages cache...")
    result = db.country_languages.delete_many({})
    print(f"✅ Deleted {result.deleted_count} country language cache entries")
    
    # 2. Clear in-memory LRU cache (requires service instance)
    # This will reset on next app restart, but you can clear it now:
    service = CountryLanguageService(None)
    service._memory_cache.cache_clear()
    print("✅ Cleared in-memory LRU cache")
    
    # 3. Article deletion (DEV/TEST ONLY)
    if clear_articles and not IS_PRODUCTION:
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        result = db.articles.delete_many({"created_at": {"$lt": cutoff}})
        print(f"⚠️ [DEV ONLY] Deleted {result.deleted_count} old articles")
    else:
        print("ℹ️ Skipping article deletion (production-safe)")
        if clear_articles:
            print("   (Set FLASK_ENV != 'production' to enable article deletion)")


if __name__ == "__main__":
    clear_articles = "--clear-articles" in sys.argv
    clear_cache(clear_articles=clear_articles)