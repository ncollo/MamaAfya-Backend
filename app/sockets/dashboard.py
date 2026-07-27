import socketio
import logging

logger = logging.getLogger(__name__)

def register_socket_events(sio: socketio.AsyncServer):
    """
    Registers real-time Socket.IO events for CHW Triage Dashboard
    """
    
    @sio.event
    async def connect(sid, environ):
        # Clean parameter retrieval from query string
        query_params = environ.get("QUERY_STRING", "")
        chw_id = None
        
        # Super-simple parse token from query parameters: e.g. ?chw_id=12
        for param in query_params.split("&"):
            if param.startswith("chw_id="):
                chw_id = param.split("=")[1]
                break
                
        logger.info(f"Socket Client connected: {sid}")
        
        if chw_id:
            room = f"chw_{chw_id}"
            await sio.enter_room(sid, room)
            logger.info(f"Client {sid} (CHW {chw_id}) joined room {room}")

    @sio.event
    async def disconnect(sid):
        logger.info(f"Socket Client disconnected: {sid}")

    @sio.event
    async def join_dashboard(sid, data):
        """CHW client requests to join their notification room manually"""
        chw_id = data.get("chw_id")
        if chw_id:
            room = f"chw_{chw_id}"
            await sio.enter_room(sid, room)
            logger.info(f"Client {sid} manually joined room {room}")
            return {"status": "success", "room": room}
        return {"status": "error", "message": "Missing chw_id"}

    @sio.event
    async def request_refresh(sid, data):
        """CHW requests a client-side update check"""
        chw_id = data.get("chw_id")
        logger.info(f"Refresh requested by CHW {chw_id} via {sid}")
        from datetime import datetime
        await sio.emit("dashboard_refresh", {"timestamp": datetime.now().isoformat()}, room=f"chw_{chw_id}")
