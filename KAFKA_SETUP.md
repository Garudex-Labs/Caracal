# Kafka Infrastructure Setup Guide

This guide explains how to set up the Kafka event streaming infrastructure for Caracal Core v0.3.

## Overview

Caracal Core v0.3 uses Apache Kafka for event-driven architecture with the following components:

- **Zookeeper Ensemble**: 3-node cluster for Kafka coordination
- **Kafka Brokers**: 3-node cluster with replication factor 3
- **Schema Registry**: Confluent Schema Registry for Avro schema management
- **Security**: TLS encryption and SASL/SCRAM authentication

## Prerequisites

- Docker and Docker Compose installed
- OpenSSL installed (for certificate generation)
- Java JDK installed (for keytool, certificate management)
- At least 8GB RAM available for Docker
- At least 20GB disk space for Kafka data

## Quick Start

### 1. Generate Security Credentials

Run the security setup script to generate TLS certificates and SASL credentials:

```bash
cd Caracal
chmod +x scripts/setup-kafka-security.sh
./scripts/setup-kafka-security.sh
```

This script will:
- Generate CA certificate and Kafka broker certificates
- Create Java keystores and truststores
- Generate SASL/SCRAM user credentials
- Create client configuration files
- Create `.env.kafka` environment file

### 2. Start Kafka Cluster

Start the Kafka infrastructure using Docker Compose:

```bash
docker-compose -f docker-compose.kafka.yml --env-file .env.kafka up -d
```

Wait for all services to be healthy (this may take 1-2 minutes):

```bash
docker-compose -f docker-compose.kafka.yml ps
```

You should see all services in "Up (healthy)" state.

### 3. Create SCRAM Credentials in Kafka

After Kafka is running, create SCRAM credentials for authentication:

```bash
# Admin user
docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \
  --alter --add-config 'SCRAM-SHA-512=[password=admin-secret]' \
  --entity-type users --entity-name admin

# Producer user
docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \
  --alter --add-config 'SCRAM-SHA-512=[password=producer-secret]' \
  --entity-type users --entity-name producer

# Consumer user
docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \
  --alter --add-config 'SCRAM-SHA-512=[password=consumer-secret]' \
  --entity-type users --entity-name consumer

# Schema Registry user
docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \
  --alter --add-config 'SCRAM-SHA-512=[password=schema-registry-secret]' \
  --entity-type users --entity-name schema-registry
```

Verify credentials were created:

```bash
docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \
  --describe --entity-type users
```

### 4. Verify Kafka Cluster

Check Kafka broker status:

```bash
docker exec -it caracal-kafka-1 kafka-broker-api-versions \
  --bootstrap-server localhost:9092 \
  --command-config /etc/kafka/secrets/client.properties
```

Check Schema Registry:

```bash
curl http://localhost:8081/
```

You should see: `{}`

## Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Caracal Kafka Network                     │
│                      (172.29.0.0/16)                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Zookeeper 1  │  │ Zookeeper 2  │  │ Zookeeper 3  │      │
│  │   :2181      │  │   :2181      │  │   :2181      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│  ┌─────────────────────────┴──────────────────────────┐     │
│  │                                                      │     │
│  │  ┌──────────┐      ┌──────────┐      ┌──────────┐ │     │
│  │  │ Kafka 1  │◄────►│ Kafka 2  │◄────►│ Kafka 3  │ │     │
│  │  │  :9092   │      │  :9092   │      │  :9092   │ │     │
│  │  │  :9093   │      │  :9093   │      │  :9093   │ │     │
│  │  └────┬─────┘      └────┬─────┘      └────┬─────┘ │     │
│  │       │                 │                 │        │     │
│  │       └─────────────────┴─────────────────┘        │     │
│  │                         │                           │     │
│  │                ┌────────▼────────┐                  │     │
│  │                │ Schema Registry │                  │     │
│  │                │      :8081      │                  │     │
│  │                └─────────────────┘                  │     │
│  │                                                      │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Port Mapping

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| Zookeeper 1-3 | 2181 | - | TCP |
| Kafka 1 (Internal) | 9092 | - | SASL_SSL |
| Kafka 1 (External) | 9093 | 9093 | SASL_SSL |
| Kafka 2 (Internal) | 9092 | - | SASL_SSL |
| Kafka 2 (External) | 9093 | 9095 | SASL_SSL |
| Kafka 3 (Internal) | 9092 | - | SASL_SSL |
| Kafka 3 (External) | 9093 | 9097 | SASL_SSL |
| Schema Registry | 8081 | 8081 | HTTP |

### Security Configuration

#### TLS Encryption

All Kafka broker communication is encrypted using TLS 1.2+:

- **Inter-broker communication**: SASL_SSL (TLS + SASL/SCRAM)
- **Client-broker communication**: SASL_SSL (TLS + SASL/SCRAM)
- **Certificate validation**: Required (mutual TLS)

#### SASL/SCRAM Authentication

Kafka uses SCRAM-SHA-512 for authentication:

- **Admin user**: Full cluster administration
- **Producer user**: Write access to topics
- **Consumer user**: Read access to topics
- **Schema Registry user**: Schema management

#### Replication and Durability

- **Replication factor**: 3 (all data replicated to 3 brokers)
- **Min in-sync replicas**: 2 (requires 2 replicas to acknowledge writes)
- **Transaction log replication**: 3 (for exactly-once semantics)

## Configuration

### Kafka Broker Configuration

Key configuration parameters:

```yaml
# Replication
default.replication.factor: 3
min.insync.replicas: 2
offsets.topic.replication.factor: 3
transaction.state.log.replication.factor: 3
transaction.state.log.min.isr: 2

# Retention
log.retention.hours: 720  # 30 days
log.segment.bytes: 1073741824  # 1GB
compression.type: snappy

# Performance
num.network.threads: 8
num.io.threads: 8
socket.send.buffer.bytes: 102400
socket.receive.buffer.bytes: 102400
socket.request.max.bytes: 104857600  # 100MB
```

### Schema Registry Configuration

```yaml
schema.compatibility.level: backward
kafkastore.topic.replication.factor: 3
```

## Operations

### View Logs

View logs for all services:

```bash
docker-compose -f docker-compose.kafka.yml logs -f
```

View logs for specific service:

```bash
docker-compose -f docker-compose.kafka.yml logs -f kafka-1
docker-compose -f docker-compose.kafka.yml logs -f schema-registry
```

### Stop Kafka Cluster

Stop all services:

```bash
docker-compose -f docker-compose.kafka.yml down
```

Stop and remove all data (WARNING: deletes all Kafka data):

```bash
docker-compose -f docker-compose.kafka.yml down -v
```

### Restart Services

Restart specific service:

```bash
docker-compose -f docker-compose.kafka.yml restart kafka-1
```

Restart all services:

```bash
docker-compose -f docker-compose.kafka.yml restart
```

### Health Checks

Check Zookeeper health:

```bash
docker exec -it caracal-zookeeper-1 bash -c "echo ruok | nc localhost 2181"
# Should output: imok
```

Check Kafka broker health:

```bash
docker exec -it caracal-kafka-1 kafka-broker-api-versions \
  --bootstrap-server localhost:9092
```

Check Schema Registry health:

```bash
curl http://localhost:8081/
```

### Monitoring

View Kafka metrics:

```bash
docker exec -it caracal-kafka-1 kafka-run-class kafka.tools.JmxTool \
  --object-name kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec
```

View consumer group lag:

```bash
docker exec -it caracal-kafka-1 kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --command-config /etc/kafka/secrets/client.properties \
  --describe --all-groups
```

## Troubleshooting

### Kafka broker won't start

1. Check Zookeeper is healthy:
   ```bash
   docker-compose -f docker-compose.kafka.yml ps zookeeper-1 zookeeper-2 zookeeper-3
   ```

2. Check Kafka logs:
   ```bash
   docker-compose -f docker-compose.kafka.yml logs kafka-1
   ```

3. Verify certificates are present:
   ```bash
   ls -la kafka-certs/
   ```

### Authentication failures

1. Verify SCRAM credentials were created:
   ```bash
   docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \
     --describe --entity-type users
   ```

2. Check client configuration:
   ```bash
   cat kafka-certs/client.properties
   ```

### Schema Registry connection issues

1. Check Schema Registry logs:
   ```bash
   docker-compose -f docker-compose.kafka.yml logs schema-registry
   ```

2. Verify Schema Registry can connect to Kafka:
   ```bash
   docker exec -it caracal-schema-registry curl http://localhost:8081/subjects
   ```

### Out of memory errors

Increase Docker memory allocation:

1. Docker Desktop: Settings → Resources → Memory (increase to 8GB+)
2. Docker Engine: Edit `/etc/docker/daemon.json`:
   ```json
   {
     "default-ulimits": {
       "memlock": {
         "Hard": -1,
         "Name": "memlock",
         "Soft": -1
       }
     }
   }
   ```

## Security Best Practices

1. **Change default passwords**: Update passwords in `setup-kafka-security.sh` before running
2. **Rotate certificates**: Regenerate certificates annually
3. **Secure credential files**: Set restrictive permissions on `kafka-certs/` directory:
   ```bash
   chmod 700 kafka-certs/
   chmod 600 kafka-certs/*.pem kafka-certs/*.jks
   ```
4. **Don't commit secrets**: Add `kafka-certs/` and `.env.kafka` to `.gitignore`
5. **Use separate credentials**: Use different credentials for each service/environment
6. **Enable audit logging**: Configure Kafka audit logs for compliance

## Next Steps

After Kafka is running, proceed to:

1. **Create Kafka topics**: See task 1.2 in the implementation plan
2. **Configure Caracal Core**: Update `config.yaml` with Kafka connection settings
3. **Deploy event consumers**: Deploy LedgerWriter, MetricsAggregator, and AuditLogger consumers

## References

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Confluent Platform Documentation](https://docs.confluent.io/)
- [Kafka Security](https://kafka.apache.org/documentation/#security)
- [Schema Registry Documentation](https://docs.confluent.io/platform/current/schema-registry/index.html)
