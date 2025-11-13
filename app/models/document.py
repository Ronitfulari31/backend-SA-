# app/models/document.py
from datetime import datetime
from bson import ObjectId

class Document:
    @staticmethod
    def create(db, user_id, filename, file_path, file_type, content=None, metadata=None):
        """Create a new document record"""
        doc = {
            'user_id': user_id,
            'filename': filename,
            'file_path': file_path,
            'file_type': file_type,
            'content': content,
            'metadata': metadata or {},
            'uploaded_at': datetime.utcnow(),
            'processed': False
        }
        result = db.documents.insert_one(doc)
        return str(result.inserted_id)

    @staticmethod
    def get_by_id(db, doc_id):
        """Get document by ID"""
        return db.documents.find_one({'_id': ObjectId(doc_id)})

    @staticmethod
    def get_by_user(db, user_id):
        """Get all documents for a user"""
        return list(db.documents.find({'user_id': user_id}))

    @staticmethod
    def update_status(db, doc_id, processed=True):
        """Update document processing status"""
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {'processed': processed}}
        )
