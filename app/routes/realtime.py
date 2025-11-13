from flask import Blueprint, jsonify
from flask_socketio import emit

# Create a Flask blueprint
realtime_bp = Blueprint('realtime', __name__, url_prefix='/realtime')

@realtime_bp.route('/ping')
def ping():
    """Simple health check route"""
    return jsonify({"message": "Realtime API is alive"}), 200


def register_realtime_events(socketio):
    """Register all Socket.IO event handlers"""

    @socketio.on('connect')
    def handle_connect():
        emit('status', {'message': 'Connected to real-time updates'})
        print('Client connected')

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    @socketio.on('send_update')
    def handle_update(data):
        """Broadcast data to all connected clients"""
        emit('update', data, broadcast=True)
