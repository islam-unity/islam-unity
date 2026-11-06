from typing import Dict, Set, Any
import json
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        # Maps channel_name -> Set of WebSockets
        self.channel_subscribers: Dict[str, Set[WebSocket]] = {}
        # Maps WebSocket -> Set of subscribed channels
        self.client_channels: Dict[WebSocket, Set[str]] = {}
        # Maps user_id -> Set of WebSockets
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        self.client_channels[websocket] = set()

    def disconnect(self, websocket: WebSocket, user_id: str):
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Remove from all subscribed channels
        if websocket in self.client_channels:
            for channel in self.client_channels[websocket]:
                if channel in self.channel_subscribers:
                    self.channel_subscribers[channel].discard(websocket)
                    if not self.channel_subscribers[channel]:
                        del self.channel_subscribers[channel]
            del self.client_channels[websocket]

    def subscribe(self, websocket: WebSocket, channel: str):
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        self.channel_subscribers[channel].add(websocket)
        if websocket in self.client_channels:
            self.client_channels[websocket].add(channel)

    def unsubscribe(self, websocket: WebSocket, channel: str):
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(websocket)
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]
        if websocket in self.client_channels:
            self.client_channels[websocket].discard(channel)

    async def broadcast_to_channel(self, channel: str, event_type: str, payload: Any):
        message = json.dumps({
            "channel": channel,
            "event": event_type,
            "data": payload
        }, ensure_ascii=False)
        subscribers = self.channel_subscribers.get(channel, set()).copy()
        for ws in subscribers:
            try:
                await ws.send_text(message)
            except Exception:
                # Broken connection will be cleaned up on disconnect
                pass

    async def send_to_user(self, user_id: str, event_type: str, payload: Any):
        message = json.dumps({
            "event": event_type,
            "data": payload
        }, ensure_ascii=False)
        connections = self.user_connections.get(user_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                pass


ws_manager = WebSocketManager()
