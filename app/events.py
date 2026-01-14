from flask import request
from flask_socketio import join_room, leave_room
from app import socketio

@socketio.on('join')
def on_join(data):
    """Join a room"""
    room = data.get('room')
    if room:
        join_room(room)
        print(f"Client {request.sid} joined room: {room}")

@socketio.on('leave')
def on_leave(data):
    """Leave a room"""
    room = data.get('room')
    if room:
        leave_room(room)
        print(f"Client {request.sid} left room: {room}")

@socketio.on('connect')
def on_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    print(f"Client disconnected: {request.sid}")
