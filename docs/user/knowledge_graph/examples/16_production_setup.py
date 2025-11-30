"""
Production Setup Example: PostgreSQL with Full Features

This example demonstrates a complete production setup with:
- PostgreSQL backend
- Redis caching
- Performance monitoring
- Health checks
- Graceful degradation
- Metrics collection
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

from aiecs.infrastructure.graph_storage import PostgresGraphStore
from aiecs.infrastructure.graph_storage.cache import GraphStoreCache, GraphStoreCacheConfig
from aiecs.infrastructure.graph_storage.performance_monitoring import PerformanceMonitor
from aiecs.infrastructure.graph_storage.health_checks import HealthChecker, HealthMonitor
from aiecs.infrastructure.graph_storage.metrics import MetricsCollector, MetricsExporter
from aiecs.infrastructure.graph_storage.graceful_degradation import GracefulDegradationStore
from aiecs.infrastructure.graph_storage.error_handling import configure_graph_storage_logging
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

# Configure logging
logging.basicConfig(level=logging.INFO)
configure_graph_storage_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_production_store():
    """Setup production graph store with all features"""
    
    # Load environment variables
    load_dotenv()
    
    # 1. Initialize primary PostgreSQL store
    logger.info("Initializing PostgreSQL store...")
    primary_store = PostgresGraphStore(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'aiecs_knowledge_graph'),
        min_pool_size=5,
        max_pool_size=20,
        enable_pgvector=os.getenv('ENABLE_PGVECTOR', 'false').lower() == 'true'
    )
    
    # 2. Add graceful degradation
    logger.info("Enabling graceful degradation...")
    store = GracefulDegradationStore(primary_store, enable_fallback=True)
    await store.initialize()
    
    # 3. Enable caching
    logger.info("Initializing cache...")
    cache = GraphStoreCache(GraphStoreCacheConfig(
        enabled=True,
        redis_url=os.getenv('REDIS_URL', None),
        ttl=int(os.getenv('REDIS_TTL', '300')),
        max_cache_size_mb=1000
    ))
    await cache.initialize()
    
    # 4. Enable performance monitoring
    logger.info("Initializing performance monitoring...")
    monitor = PerformanceMonitor(
        enabled=True,
        slow_query_threshold_ms=100.0,
        log_slow_queries=True
    )
    await monitor.initialize()
    
    # 5. Setup health checks
    logger.info("Setting up health checks...")
    checker = HealthChecker(store, timeout_seconds=5.0)
    health_monitor = HealthMonitor(checker, interval_seconds=30)
    await health_monitor.start()
    
    # 6. Setup metrics collection
    logger.info("Initializing metrics collection...")
    collector = MetricsCollector()
    exporter = MetricsExporter(collector)
    
    return {
        'store': store,
        'cache': cache,
        'monitor': monitor,
        'health_monitor': health_monitor,
        'collector': collector,
        'exporter': exporter
    }


async def example_usage(components):
    """Example usage of production setup"""
    
    store = components['store']
    collector = components['collector']
    
    # Add entities
    logger.info("Adding entities...")
    entity1 = Entity(
        id="person_1",
        entity_type="Person",
        properties={"name": "Alice", "age": 30}
    )
    entity2 = Entity(
        id="person_2",
        entity_type="Person",
        properties={"name": "Bob", "age": 25}
    )
    
    start = asyncio.get_event_loop().time()
    await store.add_entity(entity1)
    await store.add_entity(entity2)
    duration = (asyncio.get_event_loop().time() - start) * 1000
    
    collector.record_latency("add_entity", duration)
    logger.info(f"Added entities in {duration:.2f}ms")
    
    # Add relation
    relation = Relation(
        id="rel_1",
        source_id="person_1",
        target_id="person_2",
        relation_type="KNOWS",
        properties={"since": "2020"}
    )
    
    start = asyncio.get_event_loop().time()
    await store.add_relation(relation)
    duration = (asyncio.get_event_loop().time() - start) * 1000
    
    collector.record_latency("add_relation", duration)
    logger.info(f"Added relation in {duration:.2f}ms")
    
    # Query with caching
    logger.info("Querying entities...")
    start = asyncio.get_event_loop().time()
    retrieved = await store.get_entity("person_1")
    duration = (asyncio.get_event_loop().time() - start) * 1000
    
    collector.record_latency("get_entity", duration)
    collector.record_cache_hit()  # If cached
    logger.info(f"Retrieved entity: {retrieved.properties['name']} in {duration:.2f}ms")
    
    # Get neighbors
    neighbors = await store.get_neighbors("person_1", direction="outgoing")
    logger.info(f"Found {len(neighbors)} neighbors")
    
    # Get stats
    stats = await store.get_stats()
    logger.info(f"Graph stats: {stats}")


async def monitor_health(components):
    """Monitor health status"""
    
    health_monitor = components['health_monitor']
    
    # Wait a bit for health checks
    await asyncio.sleep(35)
    
    # Get current status
    status = health_monitor.get_current_status()
    if status:
        logger.info(f"Health status: {status.status.value}")
        logger.info(f"Response time: {status.response_time_ms:.2f}ms")
        logger.info(f"Uptime: {health_monitor.get_uptime_percentage(window_minutes=1):.1f}%")


async def export_metrics(components):
    """Export metrics for monitoring"""
    
    exporter = components['exporter']
    
    # Export to Prometheus format
    prometheus_metrics = exporter.to_prometheus()
    logger.info("Prometheus metrics:")
    print(prometheus_metrics[:500] + "..." if len(prometheus_metrics) > 500 else prometheus_metrics)
    
    # Export to dictionary (for JSON APIs)
    metrics_dict = exporter.to_dict()
    logger.info(f"Cache hit rate: {metrics_dict['cache']['hit_rate']:.2%}")
    logger.info(f"Total queries: {sum(s['count'] for s in metrics_dict['latency'].values())}")


async def cleanup(components):
    """Cleanup resources"""
    
    logger.info("Cleaning up...")
    
    # Stop health monitoring
    await components['health_monitor'].stop()
    
    # Close cache
    await components['cache'].close()
    
    # Close store
    await components['store'].close()
    
    logger.info("Cleanup complete")


async def main():
    """Main function"""
    
    logger.info("="*60)
    logger.info("Production Setup Example")
    logger.info("="*60)
    
    try:
        # Setup production components
        components = await setup_production_store()
        logger.info("✅ Production setup complete")
        
        # Example usage
        await example_usage(components)
        
        # Monitor health
        await monitor_health(components)
        
        # Export metrics
        await export_metrics(components)
        
        # Cleanup
        await cleanup(components)
        
        logger.info("="*60)
        logger.info("Example completed successfully")
        logger.info("="*60)
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

