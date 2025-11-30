# Production Deployment Guide for Knowledge Graph

Complete guide for deploying AIECS Knowledge Graph in production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Backend Selection](#backend-selection)
3. [PostgreSQL Setup](#postgresql-setup)
4. [Configuration](#configuration)
5. [Performance Optimization](#performance-optimization)
6. [Monitoring and Health Checks](#monitoring-and-health-checks)
7. [Security](#security)
8. [Backup and Recovery](#backup-and-recovery)
9. [Scaling](#scaling)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB SSD
- Network: 100Mbps

**Recommended** (for 1M+ entities):
- CPU: 4+ cores
- RAM: 16GB+
- Disk: 100GB+ SSD
- Network: 1Gbps

### Software Requirements

- Python 3.9+
- PostgreSQL 12+ (for PostgreSQL backend)
- Redis 6+ (optional, for caching)
- Docker (optional, for containerized deployment)

---

## Backend Selection

### When to Use Each Backend

**InMemoryGraphStore**:
- ❌ **NOT for production**
- ✅ Development and testing only
- ✅ Small datasets (< 10K entities)
- ✅ Temporary data

**SQLiteGraphStore**:
- ✅ Small to medium applications (< 1M entities)
- ✅ Single-user or low-concurrency
- ✅ Embedded systems
- ✅ Simple deployment
- ❌ Not for high-concurrency production

**PostgresGraphStore**:
- ✅ **Recommended for production**
- ✅ Large graphs (1M+ entities)
- ✅ High concurrency
- ✅ ACID transactions
- ✅ Advanced features (JSONB, pgvector)

---

## PostgreSQL Setup

### 1. Install PostgreSQL

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install postgresql-14 postgresql-contrib-14
```

**CentOS/RHEL**:
```bash
sudo yum install postgresql14-server postgresql14
```

**macOS**:
```bash
brew install postgresql@14
```

### 2. Configure PostgreSQL

**Create database**:
```bash
sudo -u postgres psql
CREATE DATABASE aiecs_knowledge_graph;
CREATE USER graph_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE aiecs_knowledge_graph TO graph_user;
\q
```

**Enable pgvector extension** (optional, for vector search):
```bash
sudo -u postgres psql -d aiecs_knowledge_graph
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### 3. Configure Connection Pooling

**PostgreSQL configuration** (`postgresql.conf`):
```ini
# Connection settings
max_connections = 200
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 20MB
min_wal_size = 1GB
max_wal_size = 4GB
```

**Restart PostgreSQL**:
```bash
sudo systemctl restart postgresql
```

### 4. Configure Firewall

```bash
# Allow PostgreSQL connections
sudo ufw allow 5432/tcp

# Or restrict to specific IPs
sudo ufw allow from 10.0.0.0/8 to any port 5432
```

---

## Configuration

### Environment Variables

Create `.env` file:

**For local PostgreSQL:**
```bash
# PostgreSQL Configuration (Local Mode)
DB_CONNECTION_MODE=local
DB_HOST=localhost
DB_PORT=5432
DB_USER=graph_user
DB_PASSWORD=secure_password
DB_NAME=aiecs_knowledge_graph
```

**For cloud PostgreSQL:**
```bash
# PostgreSQL Configuration (Cloud Mode)
DB_CONNECTION_MODE=cloud
POSTGRES_URL=postgresql://user:password@host:port/database?sslmode=require
```

**Common settings:**
```bash
# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0
REDIS_TTL=300

# Graph Store Configuration
GRAPH_STORE_BACKEND=postgres
GRAPH_STORE_POOL_MIN=5
GRAPH_STORE_POOL_MAX=20
GRAPH_STORE_ENABLE_CACHE=true
GRAPH_STORE_ENABLE_MONITORING=true
```

### Application Configuration

```python
from aiecs.infrastructure.graph_storage import PostgresGraphStore
from aiecs.infrastructure.graph_storage.cache import GraphStoreCache, GraphStoreCacheConfig
from aiecs.infrastructure.graph_storage.performance_monitoring import PerformanceMonitor

# Initialize store
store = PostgresGraphStore(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT', '5432')),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    min_pool_size=5,
    max_pool_size=20
)
await store.initialize()

# Enable caching
cache = GraphStoreCache(GraphStoreCacheConfig(
    redis_url=os.getenv('REDIS_URL'),
    ttl=int(os.getenv('REDIS_TTL', '300'))
))
await cache.initialize()

# Enable monitoring
monitor = PerformanceMonitor(
    enabled=True,
    slow_query_threshold_ms=100.0
)
await monitor.initialize()
```

---

## Performance Optimization

### 1. Enable Caching

```python
from aiecs.infrastructure.graph_storage.cache import GraphStoreCache, GraphStoreCacheConfig

cache = GraphStoreCache(GraphStoreCacheConfig(
    enabled=True,
    redis_url="redis://localhost:6379/0",
    ttl=300,  # 5 minutes
    max_cache_size_mb=1000  # 1GB in-memory fallback
))
await cache.initialize()
```

### 2. Optimize Indexes

```python
from aiecs.infrastructure.graph_storage.index_optimization import IndexOptimizer

optimizer = IndexOptimizer(store.pool)

# Get recommendations
recommendations = await optimizer.get_missing_index_recommendations()

# Apply high-priority recommendations
high_priority = [r for r in recommendations if r.estimated_benefit == "high"]
results = await optimizer.apply_recommendations(high_priority)
```

### 3. Use Batch Operations

```python
from aiecs.infrastructure.graph_storage.batch_operations import BatchOperationsMixin

class OptimizedStore(PostgresGraphStore, BatchOperationsMixin):
    pass

store = OptimizedStore(...)
await store.batch_add_entities(entities, batch_size=1000, use_copy=True)
```

### 4. Configure Connection Pooling

```python
store = PostgresGraphStore(
    ...,
    min_pool_size=10,  # Minimum connections
    max_pool_size=50   # Maximum connections
)
```

---

## Monitoring and Health Checks

### 1. Health Checks

```python
from aiecs.infrastructure.graph_storage.health_checks import HealthChecker, HealthMonitor

checker = HealthChecker(store, timeout_seconds=5.0)
result = await checker.check_health()

if result.is_healthy():
    print("Store is healthy")
else:
    print(f"Store is {result.status}: {result.message}")

# Continuous monitoring
monitor = HealthMonitor(checker, interval_seconds=30)
await monitor.start()
```

### 2. Metrics Collection

```python
from aiecs.infrastructure.graph_storage.metrics import MetricsCollector, MetricsExporter

collector = MetricsCollector()
collector.record_latency("get_entity", 12.5)
collector.record_cache_hit()

# Export to Prometheus
exporter = MetricsExporter(collector)
prometheus_metrics = exporter.to_prometheus()
```

### 3. Performance Monitoring

```python
from aiecs.infrastructure.graph_storage.performance_monitoring import PerformanceMonitor

monitor = PerformanceMonitor(
    enabled=True,
    slow_query_threshold_ms=100.0,
    log_slow_queries=True
)

# Track queries
async with monitor.track_query("get_entity", query):
    result = await conn.fetch(query)

# Get report
report = monitor.get_performance_report()
```

---

## Security

### 1. Database Security

**Use strong passwords**:
```bash
# Generate secure password
openssl rand -base64 32
```

**Limit database access**:
```sql
-- Revoke public access
REVOKE ALL ON DATABASE aiecs_knowledge_graph FROM PUBLIC;

-- Grant only to application user
GRANT CONNECT ON DATABASE aiecs_knowledge_graph TO graph_user;
```

**Enable SSL**:
```python
store = PostgresGraphStore(
    ...,
    ssl=True,
    sslmode='require'
)
```

### 2. Connection Security

**Use connection pooling**:
- Prevents connection exhaustion
- Reduces authentication overhead
- Improves security

**Rotate credentials**:
- Change passwords regularly
- Use secrets management (Vault, AWS Secrets Manager)

### 3. Input Validation

**Validate entity IDs**:
```python
import re

def validate_entity_id(entity_id: str) -> bool:
    # Only allow alphanumeric, underscore, hyphen
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', entity_id))
```

**Sanitize queries**:
- Use parameterized queries (already implemented)

---

## Backup and Recovery

### 1. PostgreSQL Backup

**Automated backup script**:
```bash
#!/bin/bash
# backup_graph.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/graph"
DB_NAME="aiecs_knowledge_graph"

# Create backup
pg_dump -U graph_user -F c -f "$BACKUP_DIR/graph_$DATE.dump" $DB_NAME

# Compress
gzip "$BACKUP_DIR/graph_$DATE.dump"

# Keep only last 7 days
find $BACKUP_DIR -name "*.dump.gz" -mtime +7 -delete
```

**Schedule with cron**:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup_graph.sh
```

### 2. Restore from Backup

```bash
# Restore
gunzip graph_20231109_020000.dump.gz
pg_restore -U graph_user -d aiecs_knowledge_graph graph_20231109_020000.dump
```

### 3. Streaming Backup

```python
from aiecs.infrastructure.graph_storage.streaming import GraphStreamExporter

exporter = GraphStreamExporter(store)
await exporter.export_to_file(
    "backup.jsonl.gz",
    format=StreamFormat.JSONL,
    compress=True
)
```

---

## Scaling

### Vertical Scaling

**Increase resources**:
- More RAM: Better caching
- More CPU: Faster queries
- SSD storage: Faster I/O

### Horizontal Scaling

**Read Replicas**:
```python
# Primary for writes
primary_store = PostgresGraphStore(host="primary.db", ...)

# Replicas for reads
replica_stores = [
    PostgresGraphStore(host="replica1.db", ...),
    PostgresGraphStore(host="replica2.db", ...)
]

# Route reads to replicas
def get_read_store():
    return random.choice(replica_stores)
```

**Connection Pooling**:
- Increase `max_pool_size` for more concurrent connections
- Monitor pool usage

---

## Troubleshooting

### Common Issues

**Connection Errors**:
```python
# Check connection
from aiecs.infrastructure.graph_storage.health_checks import HealthChecker

checker = HealthChecker(store)
result = await checker.check_health()
print(result.to_dict())
```

**Slow Queries**:
```python
# Analyze query plans
from aiecs.infrastructure.graph_storage.performance_monitoring import PerformanceMonitor

monitor = PerformanceMonitor()
plan = await monitor.analyze_query_plan(conn, query)
print(plan.get_warnings())
```

**Memory Issues**:
- Use streaming for large exports
- Enable pagination
- Use lazy loading

---

## Production Checklist

- [ ] PostgreSQL installed and configured
- [ ] Database and user created
- [ ] Indexes optimized
- [ ] Caching enabled (Redis)
- [ ] Health checks configured
- [ ] Monitoring metrics exported
- [ ] Backups scheduled
- [ ] SSL enabled for connections
- [ ] Firewall configured
- [ ] Connection pooling tuned
- [ ] Error handling enabled
- [ ] Logging configured
- [ ] Graceful degradation tested

---

## Next Steps

- See `PERFORMANCE_GUIDE.md` for performance tuning
- See `CUSTOM_BACKEND_GUIDE.md` for custom backends
- See `PHASE6_TASK6.5_COMPLETE.md` for complete implementation details

