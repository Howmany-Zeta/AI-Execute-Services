from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import socketio
from app.api import stream_router, graph_router
from app.api.user_token import router as user_token_router
# Import services to ensure they are registered
import app.services.scholar.services
import app.services.general.services
import app.services.multi_task.services

# Import tool registry functions from tools package
from app.tools import discover_tools, list_tools
from app.tools.tool_executor import get_executor

# ✅ 导入初始化和关闭函数
from app.infrastructure.persistence.redis_client import initialize_redis_client, close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # 调用初始化函数
    await initialize_redis_client()
    print("Lifespan startup: Redis client has been initialized.")

    # Initialize the tool executor with default configuration
    executor = get_executor()

    # Discover and register all tools
    discover_tools()

    # Log registered tools
    tool_names = list_tools()
    print(f"Registered tools: {', '.join(tool_names)}")

    yield

    # --- Shutdown ---
    # 调用关闭函数
    await close_redis_client()
    print("Lifespan shutdown: Redis client has been closed.")

    # Add any other cleanup code here


# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

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

# Include exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # log exception here
    return JSONResponse(status_code=500, content={"error": str(exc)})

# Add root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome! The API is running."}

# Mount API routers
app.include_router(stream_router.router, prefix="/stream")
app.include_router(graph_router.router, prefix="/graph")
app.include_router(user_token_router)

# Export the combined ASGI app for Uvicorn to use
# This is what should be referenced when running the server
# e.g., uvicorn app.main:app
app = sio_asgi_app
