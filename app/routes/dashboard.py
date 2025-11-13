from flask import Blueprint, jsonify
from app.database import get_db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard/stats', methods=['GET'])
def get_stats():
    db = get_db()  # ✅ get the active db connection inside the route
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    stats = {
        'total_documents': db.documents.count_documents({}),
        'total_reports': db.reports.count_documents({})
    }
    return jsonify(stats)

@dashboard_bp.route('/dashboard/charts', methods=['GET'])
def get_charts():
    db = get_db()  # ✅ again, get it here
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    sentiments = list(db.documents.aggregate([
        {'$group': {'_id': '$sentiment', 'count': {'$sum': 1}}}
    ]))
    return jsonify(sentiments)
