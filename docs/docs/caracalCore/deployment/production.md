---
sidebar_position: 4
title: Production Guide
---

# Production Deployment Guide

This guide covers production-specific considerations for deploying Caracal Core.

## Production Architecture

### Recommended Architecture

```
                    Load Balancer (AWS ALB/NLB)
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+---------------+   +---------------+   +---------------+
| Gateway       |   | Gateway       |   | Gateway       |
| (AZ-1)        |   | (AZ-2)        |   | (AZ-3)        |
+-------+-------+   +-------+-------+   +-------+-------+
         |                   |                   |
         +---------+---------+---------+---------+
                             |
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+---------------+   +---------------+   +---------------+
| RDS PostgreSQL|   | ElastiCache   |   | RDS PostgreSQL|
| (Multi-AZ)    |   | Redis         |   |               |
+---------------+   +---------------+   +---------------+
```

## Infrastructure Requirements

### Minimum Production Requirements

**Kubernetes Cluster**:
- 3+ worker nodes across 3 availability zones
- Node size: 8 vCPU, 32 GB RAM minimum
- Total cluster capacity: 24+ vCPU, 96+ GB RAM

**Managed Services**:
- PostgreSQL: db.r5.xlarge or equivalent (4 vCPU, 32 GB RAM)
- Redis: cache.r5.large or equivalent (2 vCPU, 13 GB RAM)

**Storage**:
- PostgreSQL: 500 GB SSD (gp3), auto-scaling enabled
- Redis: 50 GB memory

### Recommended Configuration

**Gateway Proxy**:
- Replicas: 5-10 (autoscaling)
- CPU: 1000m request, 4000m limit
- Memory: 1Gi request, 4Gi limit

## Security Best Practices

### Network Security

Deploy all services in private subnets with properly configured security groups:

```yaml
securityGroups:
  gateway:
    ingress:
      - port: 8443
        source: load-balancer-sg
    egress:
      - port: 5432
        destination: postgres-sg
  
  postgres:
    ingress:
      - port: 5432
        source: gateway-sg, consumer-sg
```

### Secrets Management

Use external secrets management:

**AWS Secrets Manager**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: caracal-secrets
spec:
  secretStoreRef:
    name: aws-secrets-manager
  target:
    name: caracal-secrets
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: caracal/production/db-password
```

**HashiCorp Vault**:
```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: caracal-vault-secrets
spec:
  provider: vault
  parameters:
    vaultAddress: "https://vault.example.com"
    roleName: "caracal-role"
```

### Encryption

- **At Rest**: Enable encryption for PostgreSQL, Redis, and Kubernetes volumes
- **In Transit**: All services communicate over TLS

## High Availability

### Multi-AZ Deployment

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/component
              operator: In
              values:
                - gateway
        topologyKey: topology.kubernetes.io/zone
```

### Pod Disruption Budgets

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: caracal-gateway-pdb
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app.kubernetes.io/component: gateway
```

### Database High Availability

- Enable Multi-AZ deployment for PostgreSQL
- Configure automatic failover
- Set up read replicas for read scaling
- Use connection pooling (PgBouncer)

## Performance Tuning

### Gateway Proxy Tuning

```yaml
gateway:
  config:
    dbPoolSize: 20
    dbMaxOverflow: 10
    dbPoolTimeout: 30
    maxConcurrentRequests: 1000
    requestTimeout: 30
    policyCacheTTL: 60
    policyCacheMaxSize: 50000
```

## Monitoring and Alerting

### Key Metrics

- Request rate (requests/sec)
- Request latency (p50, p95, p99)
- Error rate (%)
- Database connection count
- Merkle batch size and processing time

### Alerting Rules

```yaml
groups:
  - name: caracal-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(caracal_requests_total{status="error"}[5m]) > 0.05
        for: 5m
        
      - alert: MerkleVerificationFailure
        expr: caracal_merkle_verification_failures_total > 0
        for: 1m
```

## Disaster Recovery

### Backup Strategy

- PostgreSQL: Automated daily backups, 30-day retention
- Configuration: Store all manifests in Git

### Recovery Procedures

**Database Recovery**:
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier caracal-restored \
  --db-snapshot-identifier caracal-snapshot-latest
```

**Snapshot Recovery**:
```bash
caracal snapshot restore --snapshot-id snapshot-latest
caracal replay start --from-snapshot snapshot-latest
```

## Capacity Planning

### Sizing Guidelines

| Events/sec | Deployment Size | Resources |
|------------|-----------------|-----------|
| 1,000 | Small | Current config |
| 10,000 | Medium | 2x resources |
| 100,000 | Large | 10x resources |

### Storage Growth

- Ledger events: ~1 KB per event
- Monthly growth: events/sec x 2.6M x 3 KB
- Example: 10,000 events/sec = 78 GB/month

### Scaling Triggers

**Scale Up When**:
- CPU utilization > 70% for 10 minutes
- Memory utilization > 80% for 10 minutes
- Request latency p99 > 1 second

## Next Steps

- [Operational Runbook](./operationalRunbook) - Day-to-day operations
- [Docker Compose](./dockerCompose) - Local development
- [Kubernetes](./kubernetes) - Kubernetes deployment
