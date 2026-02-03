# Redis Spending Cache

Redis spending cache for Caracal Core v0.3 provides fast, real-time spending queries and metrics aggregation.

## Overview

The Redis spending cache enables sub-millisecond spending queries for recent data (last 24 hours) while maintaining backward compatibility with file-based and PostgreSQL ledgers for historical data.

**Requirements**: 20.3, 20.4, 16.4, 21.4, 25.6

## Architecture

```
┌─────────────────┐
│  LedgerWriter   │
│                 │
│  append_event() │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         v                  v
┌─────────────────┐  ┌──────────────────┐
│  Ledger File    │  │  Redis Cache     │
│  (PostgreSQL)   │  │                  │
│                 │  │  - Total         │
│  - All events   │  │  - Events (24h)  │
│  - Historical   │  │  - Trends        │
└─────────────────┘  └──────────────────┘
         │                  │
         └──────────┬───────┘
                    │
                    v
         ┌─────────────────┐
         │  LedgerQuery    │
         │                 │
         │  sum_spending() │
         └─────────────────┘
```

## Components

### RedisClient

Low-level Redis client with connection pooling, authentication, and SSL/TLS support.

**Features**:
- Connection pooling (max 50 connections)
- Password authentication
- SSL/TLS encryption
- Automatic reconnection
- Sorted set operations for time-series data

**Configuration**:
```python
from caracal.redis.client import RedisClient

client = RedisClient(
    host='localhost',
    port=6379,
    password='your_password',
    db=0,
    ssl=True,
    ssl_ca_certs='/path/to/ca.pem'
)
```

### RedisSpendingCache

High-level spending cache with time-range queries and TTL management.

**Features**:
- Real-time spending totals per agent
- Time-range spending queries using sorted sets
- Spending trend calculation (hourly, daily, weekly)
- Automatic TTL expiration (24 hours default)
- Event count tracking

**Key Prefixes**:
- `caracal:spending:total:{agent_id}` - Total spending
- `caracal:spending:events:{agent_id}` - Event sorted set (score = timestamp)
- `caracal:spending:trend:{agent_id}:{window}` - Spending trends
- `caracal:events:count:{agent_id}` - Event count

**Usage**:
```python
from caracal.redis.client import RedisClient
from caracal.redis.spending_cache import RedisSpendingCache

# Initialize
redis_client = RedisClient(host='localhost', port=6379)
cache = RedisSpendingCache(redis_client, ttl_seconds=86400)

# Update spending
cache.update_spending(
    agent_id='agent-123',
    cost=Decimal('10.50'),
    timestamp=datetime.utcnow(),
    event_id='event-001'
)

# Get total spending
total = cache.get_total_spending('agent-123')

# Get spending in time range
spending = cache.get_spending_in_range(
    agent_id='agent-123',
    start_time=datetime.utcnow() - timedelta(hours=1),
    end_time=datetime.utcnow()
)

# Store spending trend
cache.store_spending_trend(
    agent_id='agent-123',
    window='hourly',
    timestamp=datetime.utcnow(),
    spending=Decimal('100.00')
)

# Get spending trend
trends = cache.get_spending_trend(
    agent_id='agent-123',
    window='hourly',
    start_time=datetime.utcnow() - timedelta(hours=24),
    end_time=datetime.utcnow()
)
```

### LedgerWriter Integration

LedgerWriter automatically updates Redis cache when writing events.

**Usage**:
```python
from caracal.core.ledger import LedgerWriter
from caracal.redis.client import RedisClient
from caracal.redis.spending_cache import RedisSpendingCache

# Initialize with cache
redis_client = RedisClient(host='localhost', port=6379)
cache = RedisSpendingCache(redis_client)
writer = LedgerWriter('/path/to/ledger.jsonl', redis_cache=cache)

# Write event (automatically updates cache)
event = writer.append_event(
    agent_id='agent-123',
    resource_type='api_call',
    quantity=Decimal('1'),
    cost=Decimal('10.50'),
    currency='USD'
)
```

**Backward Compatibility**: LedgerWriter works without Redis cache (v0.1/v0.2 mode):
```python
# Without cache (v0.1/v0.2 mode)
writer = LedgerWriter('/path/to/ledger.jsonl', redis_cache=None)
```

### LedgerQuery Integration

LedgerQuery uses Redis cache for recent data (last 24 hours) and falls back to database for older data.

**Query Strategies**:

1. **Cache Hit** (query within last 24 hours):
   - Query Redis cache only
   - Sub-millisecond response time

2. **Cache Miss** (query older than 24 hours):
   - Query database only
   - Standard database query time

3. **Hybrid** (query spans cache and database):
   - Query Redis for recent data (last 24 hours)
   - Query database for older data
   - Combine results

**Usage**:
```python
from caracal.core.ledger import LedgerQuery
from caracal.redis.client import RedisClient
from caracal.redis.spending_cache import RedisSpendingCache

# Initialize with cache
redis_client = RedisClient(host='localhost', port=6379)
cache = RedisSpendingCache(redis_client)
query = LedgerQuery('/path/to/ledger.jsonl', redis_cache=cache)

# Query recent data (uses cache)
spending = query.sum_spending(
    agent_id='agent-123',
    start_time=datetime.utcnow() - timedelta(hours=2),
    end_time=datetime.utcnow()
)

# Query old data (uses database)
spending = query.sum_spending(
    agent_id='agent-123',
    start_time=datetime.utcnow() - timedelta(days=30),
    end_time=datetime.utcnow() - timedelta(days=29)
)

# Query spanning cache and database (hybrid)
spending = query.sum_spending(
    agent_id='agent-123',
    start_time=datetime.utcnow() - timedelta(days=2),
    end_time=datetime.utcnow()
)
```

**Backward Compatibility**: LedgerQuery works without Redis cache (v0.1/v0.2 mode):
```python
# Without cache (v0.1/v0.2 mode)
query = LedgerQuery('/path/to/ledger.jsonl', redis_cache=None)
```

## Configuration

### Docker Compose

Redis is configured in `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --requirepass ${REDIS_PASSWORD}
    --appendonly yes
    --appendfsync everysec
    --save 900 1
    --save 300 10
    --save 60 10000
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

### Environment Variables

Configure Redis in `.env`:

```bash
# Redis Configuration
REDIS_PASSWORD=your_redis_password
REDIS_PORT=6379
REDIS_DB=0
REDIS_SSL=false
REDIS_SPENDING_CACHE_TTL=86400  # 24 hours
REDIS_METRICS_CACHE_TTL=3600    # 1 hour
```

### Application Configuration

```python
from caracal.redis.client import RedisClient
from caracal.redis.spending_cache import RedisSpendingCache

# Initialize Redis client
redis_client = RedisClient(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD'),
    db=int(os.getenv('REDIS_DB', 0)),
    ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true'
)

# Initialize spending cache
cache = RedisSpendingCache(
    redis_client,
    ttl_seconds=int(os.getenv('REDIS_SPENDING_CACHE_TTL', 86400))
)
```

## Performance

### Cache Hit Performance

- **Query time**: < 1ms (p99)
- **Throughput**: > 10,000 queries/second
- **Memory**: ~1KB per agent per day

### Cache Miss Performance

- **Query time**: Same as database (10-100ms)
- **Fallback**: Automatic on cache failure

### Hybrid Query Performance

- **Query time**: Cache time + Database time
- **Optimization**: Parallel queries (future enhancement)

## Data Structures

### Spending Total

```
Key: caracal:spending:total:{agent_id}
Type: String
Value: "123.45" (Decimal as string)
TTL: 24 hours
```

### Spending Events

```
Key: caracal:spending:events:{agent_id}
Type: Sorted Set
Members: "event_id:cost" (e.g., "event-001:10.50")
Scores: Unix timestamp (float)
TTL: 24 hours
```

### Spending Trends

```
Key: caracal:spending:trend:{agent_id}:{window}
Type: Sorted Set
Members: "timestamp:spending" (e.g., "2024-01-01T12:00:00:100.50")
Scores: Unix timestamp (float)
TTL: 24 hours
```

### Event Count

```
Key: caracal:events:count:{agent_id}
Type: String
Value: "42" (Integer as string)
TTL: 24 hours
```

## Error Handling

### Cache Failures

Cache failures do not prevent ledger operations:

1. **Write Failures**: Event is written to ledger, cache update is logged as warning
2. **Read Failures**: Query falls back to database, cache failure is logged as warning

### Connection Failures

Redis connection failures are handled gracefully:

1. **Automatic Reconnection**: Connection pool retries on transient failures
2. **Fallback to Database**: Queries fall back to database on persistent failures
3. **Degraded Mode**: System continues operating without cache

## Monitoring

### Metrics

Monitor Redis cache performance:

- Cache hit rate
- Cache miss rate
- Query latency (p50, p95, p99)
- Memory usage
- Connection pool utilization

### Health Checks

```python
# Check Redis connectivity
if redis_client.ping():
    print("Redis is healthy")
else:
    print("Redis is unavailable")
```

## Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/unit/test_ledger_redis_integration.py -v
```

### Integration Tests

```bash
# Run integration tests (requires Redis)
pytest tests/integration/test_redis_spending_cache_integration.py -v
```

## Migration from v0.2

Redis cache is optional and backward compatible:

1. **Without Redis** (v0.1/v0.2 mode):
   ```python
   writer = LedgerWriter('/path/to/ledger.jsonl', redis_cache=None)
   query = LedgerQuery('/path/to/ledger.jsonl', redis_cache=None)
   ```

2. **With Redis** (v0.3 mode):
   ```python
   redis_client = RedisClient(host='localhost', port=6379)
   cache = RedisSpendingCache(redis_client)
   writer = LedgerWriter('/path/to/ledger.jsonl', redis_cache=cache)
   query = LedgerQuery('/path/to/ledger.jsonl', redis_cache=cache)
   ```

## Security

### Authentication

Redis requires password authentication:

```bash
# Set Redis password
REDIS_PASSWORD=your_secure_password
```

### SSL/TLS

Enable SSL/TLS for encrypted connections:

```python
redis_client = RedisClient(
    host='redis.example.com',
    port=6379,
    password='your_password',
    ssl=True,
    ssl_ca_certs='/path/to/ca.pem',
    ssl_certfile='/path/to/client.pem',
    ssl_keyfile='/path/to/client-key.pem'
)
```

### Network Isolation

Run Redis in isolated network:

```yaml
networks:
  caracal-network:
    driver: bridge
    internal: true  # No external access
```

## Troubleshooting

### Redis Connection Failed

```
Error: Redis connection failed: Connection refused
```

**Solution**: Ensure Redis is running and accessible:
```bash
# Check Redis status
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

### Cache Update Failed

```
Warning: Failed to update Redis cache for event 123: Connection timeout
```

**Solution**: This is a warning, not an error. Event was written to ledger successfully. Check Redis connectivity and performance.

### Cache Query Failed

```
Warning: Redis cache query failed, falling back to database: Connection timeout
```

**Solution**: This is a warning, not an error. Query fell back to database successfully. Check Redis connectivity and performance.

## Best Practices

1. **Set Appropriate TTL**: Default 24 hours balances memory usage and cache hit rate
2. **Monitor Memory Usage**: Use `maxmemory` and `maxmemory-policy` to prevent OOM
3. **Enable Persistence**: Use RDB + AOF for durability
4. **Use Connection Pooling**: Reuse connections for better performance
5. **Handle Failures Gracefully**: Cache failures should not break the application
6. **Monitor Cache Hit Rate**: Optimize TTL based on query patterns
7. **Secure Redis**: Use password authentication and SSL/TLS in production

## Future Enhancements

- Parallel cache and database queries for hybrid queries
- Automatic cache warming on startup
- Cache invalidation on policy changes
- Multi-level caching (Redis + in-memory)
- Cache compression for large datasets
- Distributed caching with Redis Cluster
