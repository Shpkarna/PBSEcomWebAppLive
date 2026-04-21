"""
Database connection and utilities for MongoDB
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.config import settings
from typing import Optional

# Global database client
_client: Optional[MongoClient] = None
_db = None


def connect_to_mongo():
    """Connect to MongoDB"""
    global _client, _db
    try:
        _client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
        # Verify connection
        _client.admin.command('ping')
        _db = _client[settings.mongodb_database]
        print(f"Connected to MongoDB at {settings.mongodb_url}")
        return _db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise


def close_mongo_connection():
    """Close MongoDB connection"""
    global _client
    if _client:
        _client.close()
        print("MongoDB connection closed")


def get_database():
    """Get the database instance"""
    global _db
    if _db is None:
        _db = connect_to_mongo()
    return _db


def get_collection(collection_name: str):
    """Get a specific collection"""
    db = get_database()
    return db[collection_name]
