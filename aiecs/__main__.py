"""
AIECS main entry point for command line execution
"""

import sys
import os


def main():
    """Main entry point for AIECS CLI"""
    # Add the parent directory to the Python path to ensure imports work
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # Import and run uvicorn
    import uvicorn
    from aiecs.main import app
    from aiecs.ws.socket_server import sio
    import socketio  # type: ignore[import-untyped]

    # Create the combined Socket.IO + FastAPI app
    socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))

    print(f"Starting AIECS server on port {port}...")

    # Run the application with Socket.IO support
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=bool(os.environ.get("RELOAD", False)),
    )


if __name__ == "__main__":
    main()
