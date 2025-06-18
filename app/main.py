from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import socketio
from app.api import stream_router, graph_router
# Import services to ensure they are registered
import app.services.domain.services
import app.services.general.services
import app.services.multi_task.services

# Import tool registry functions from tools package
from app.tools import discover_tools, list_tools
from app.core.tool_executor import get_executor

# Create FastAPI app
app = FastAPI()

# Import Socket.IO server instance (not the combined app)
from app.ws.socket_server import sio

# Mount Socket.IO server to our FastAPI app
# This creates a combined application that handles both FastAPI and Socket.IO
# Use socketio.ASGIApp with the correct parameter order for newer versions
sio_asgi_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path='socket.io'
)

# Initialize tools on startup
@app.on_event("startup")
async def startup_event():
    # Initialize the tool executor with default configuration
    executor = get_executor()

    # Discover and register all tools
    discover_tools()

    # Log registered tools
    tool_names = list_tools()
    print(f"Registered tools: {', '.join(tool_names)}")

# Include exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # log exception here
    return JSONResponse(status_code=500, content={"error": str(exc)})

# Mount API routers
app.include_router(stream_router.router, prefix="/stream")
app.include_router(graph_router.router, prefix="/graph")

# Export the combined ASGI app for Uvicorn to use
# This is what should be referenced when running the server
# e.g., uvicorn app.main:app
app = sio_asgi_app
