"""
Global ContextEngine Manager

This module provides a singleton ContextEngine instance that can be shared
across all components in the application. It follows the same pattern as
the Redis client initialization in aiecs.infrastructure.persistence.redis_client.

Usage:
    # In main.py startup:
    await initialize_context_engine()

    # In any component:
    from aiecs.infrastructure.persistence.context_engine_client import get_context_engine
    context_engine = get_context_engine()
"""

import logging
from typing import Optional, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from aiecs.domain.context.context_engine import ContextEngine

logger = logging.getLogger(__name__)

# Global singleton instance
_global_context_engine: Optional["ContextEngine"] = None
_initialization_lock = asyncio.Lock()
_initialized = False


def _get_context_engine_class():
    """Lazy import of ContextEngine to avoid circular dependencies."""
    try:
        from aiecs.domain.context.context_engine import ContextEngine

        return ContextEngine
    except ImportError as e:
        logger.warning(f"ContextEngine not available - {e}")
        return None


async def initialize_context_engine(
    use_existing_redis: bool = True,
) -> Optional["ContextEngine"]:
    """
    Initialize the global ContextEngine instance.

    This should be called once during application startup (in main.py lifespan).

    Args:
        use_existing_redis: Whether to use existing Redis client (default: True)

    Returns:
        The initialized ContextEngine instance or None if initialization fails

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await initialize_redis_client()
            await initialize_context_engine()  # Initialize after Redis
            yield
            # Shutdown
            await close_context_engine()
            await close_redis_client()
    """
    global _global_context_engine, _initialized

    if _initialized and _global_context_engine:
        logger.info("ContextEngine already initialized")
        return _global_context_engine

    async with _initialization_lock:
        # Double-check after acquiring lock
        if _initialized and _global_context_engine:
            return _global_context_engine

        ContextEngine = _get_context_engine_class()
        if not ContextEngine:
            logger.error("ContextEngine class not available - cannot initialize")
            return None

        try:
            logger.info("Initializing global ContextEngine...")
            _global_context_engine = ContextEngine(use_existing_redis=use_existing_redis)
            await _global_context_engine.initialize()
            _initialized = True
            logger.info("✅ Global ContextEngine initialized successfully")
            return _global_context_engine

        except Exception as e:
            logger.error(f"❌ Failed to initialize global ContextEngine: {e}")
            logger.warning("Application will continue without ContextEngine (degraded mode)")
            _global_context_engine = None
            _initialized = False
            return None


def get_context_engine() -> Optional["ContextEngine"]:
    """
    Get the global ContextEngine instance.

    Returns:
        The global ContextEngine instance or None if not initialized

    Example:
        from aiecs.infrastructure.persistence.context_engine_client import get_context_engine

        context_engine = get_context_engine()
        if context_engine:
            await context_engine.add_conversation_message(...)
        else:
            # Fallback to local storage
            logger.warning("ContextEngine not available")
    """
    if not _initialized:
        logger.warning("ContextEngine not initialized. Call initialize_context_engine() " "during application startup.")
    return _global_context_engine


async def close_context_engine() -> None:
    """
    Close and cleanup the global ContextEngine instance.

    This should be called during application shutdown (in main.py lifespan).

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await initialize_context_engine()
            yield
            # Shutdown
            await close_context_engine()
    """
    global _global_context_engine, _initialized

    async with _initialization_lock:
        if _global_context_engine:
            try:
                logger.info("Closing global ContextEngine...")
                # ContextEngine cleanup if needed
                if hasattr(_global_context_engine, "close"):
                    await _global_context_engine.close()
                logger.info("✅ Global ContextEngine closed successfully")
            except Exception as e:
                logger.error(f"Error closing ContextEngine: {e}")
            finally:
                _global_context_engine = None
                _initialized = False


def is_context_engine_initialized() -> bool:
    """
    Check if the global ContextEngine is initialized.

    Returns:
        True if ContextEngine is initialized and available, False otherwise
    """
    return _initialized and _global_context_engine is not None


# Convenience function for testing
async def reset_context_engine() -> None:
    """
    Reset the global ContextEngine instance.

    This is primarily for testing purposes to allow re-initialization.
    Should NOT be used in production code.
    """
    global _global_context_engine, _initialized

    async with _initialization_lock:
        if _global_context_engine:
            try:
                if hasattr(_global_context_engine, "close"):
                    await _global_context_engine.close()
            except Exception as e:
                logger.warning(f"Error during ContextEngine reset: {e}")

        _global_context_engine = None
        _initialized = False
        logger.info("ContextEngine reset completed")
