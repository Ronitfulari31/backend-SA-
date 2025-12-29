from pymongo import MongoClient
import os

def fix_indexes():
    # Load connection info (mirroring logic in app/database.py)
    mongodb_uri = 'mongodb://localhost:27017/'
    db_name = 'news_sentiment_intelligence_db'
    
    print(f"Connecting to {mongodb_uri}...")
    client = MongoClient(mongodb_uri)
    db = client[db_name]
    
    collection = db.documents
    
    index_name = "metadata.source_url_hash_1"
    
    print(f"Checking for index '{index_name}' on 'documents' collection...")
    
    indexes = collection.index_information()
    if index_name in indexes:
        print(f"Index found. Dropping '{index_name}'...")
        collection.drop_index(index_name)
        print("Index dropped successfully.")
    else:
        print("Index not found.")
        
    print("Re-creating index as SPARSE to allow multiple null hashes...")
    collection.create_index(
        "metadata.source_url_hash",
        unique=True,
        sparse=True,
        background=True
    )
    print("Index re-created successfully as unique+sparse.")
    
    # Also fix any other problematic indexes if necessary
    # For example, if 'original_url' inside metadata is also unique
    
    client.close()
    print("Maitenance complete.")

if __name__ == "__main__":
    fix_indexes()
