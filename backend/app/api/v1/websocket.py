import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_access_token
from app.core.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        # Invalid or expired token
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = payload["sub"]
    await ws_manager.connect(websocket, user_id)

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action")
                channel = data.get("channel")

                if action == "subscribe" and channel:
                    ws_manager.subscribe(websocket, channel)
                    await websocket.send_text(json.dumps({
                        "event": "SUBSCRIBED",
                        "channel": channel
                    }, ensure_ascii=False))

                elif action == "unsubscribe" and channel:
                    ws_manager.unsubscribe(websocket, channel)
                    await websocket.send_text(json.dumps({
                        "event": "UNSUBSCRIBED",
                        "channel": channel
                    }, ensure_ascii=False))

                elif action == "ping":
                    await websocket.send_text(json.dumps({"event": "PONG"}))

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
