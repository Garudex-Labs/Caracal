#!/bin/bash
# Script to generate TLS certificates and SASL/SCRAM credentials for Kafka
# Requirements: 25.1, 25.2
#
# This script:
# 1. Generates CA certificate and key
# 2. Generates Kafka broker certificates signed by CA
# 3. Creates Java keystores and truststores
# 4. Generates SASL/SCRAM credentials
#
# Usage:
#   ./scripts/setup-kafka-security.sh
#
# Prerequisites:
#   - OpenSSL installed
#   - Java keytool installed (part of JDK)
#   - Docker and docker-compose installed

set -e

# Configuration
CERTS_DIR="./kafka-certs"
VALIDITY_DAYS=365
KEYSTORE_PASSWORD="changeit"
TRUSTSTORE_PASSWORD="changeit"
KEY_PASSWORD="changeit"

# SASL/SCRAM credentials
KAFKA_ADMIN_USER="admin"
KAFKA_ADMIN_PASSWORD="admin-secret"
KAFKA_PRODUCER_USER="producer"
KAFKA_PRODUCER_PASSWORD="producer-secret"
KAFKA_CONSUMER_USER="consumer"
KAFKA_CONSUMER_PASSWORD="consumer-secret"
KAFKA_SCHEMA_REGISTRY_USER="schema-registry"
KAFKA_SCHEMA_REGISTRY_PASSWORD="schema-registry-secret"

echo "========================================="
echo "Kafka Security Setup Script"
echo "========================================="
echo ""

# Create certificates directory
echo "Creating certificates directory..."
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# Step 1: Generate CA certificate
echo ""
echo "Step 1: Generating CA certificate..."
if [ ! -f ca-key.pem ]; then
    openssl req -new -x509 -keyout ca-key.pem -out ca-cert.pem -days $VALIDITY_DAYS -nodes \
        -subj "/C=US/ST=CA/L=San Francisco/O=Caracal/OU=Engineering/CN=Caracal CA"
    echo "✓ CA certificate generated"
else
    echo "✓ CA certificate already exists"
fi

# Step 2: Generate Kafka broker certificate
echo ""
echo "Step 2: Generating Kafka broker certificate..."
if [ ! -f kafka-server-key.pem ]; then
    # Generate private key
    openssl genrsa -out kafka-server-key.pem 2048
    
    # Generate certificate signing request
    openssl req -new -key kafka-server-key.pem -out kafka-server.csr -nodes \
        -subj "/C=US/ST=CA/L=San Francisco/O=Caracal/OU=Engineering/CN=kafka"
    
    # Sign certificate with CA
    openssl x509 -req -CA ca-cert.pem -CAkey ca-key.pem -in kafka-server.csr \
        -out kafka-server-cert.pem -days $VALIDITY_DAYS -CAcreateserial \
        -extfile <(printf "subjectAltName=DNS:kafka-1,DNS:kafka-2,DNS:kafka-3,DNS:localhost")
    
    # Clean up CSR
    rm kafka-server.csr
    
    echo "✓ Kafka broker certificate generated"
else
    echo "✓ Kafka broker certificate already exists"
fi

# Step 3: Create Java keystores and truststores
echo ""
echo "Step 3: Creating Java keystores and truststores..."

# Create PKCS12 keystore from PEM files
if [ ! -f kafka.keystore.p12 ]; then
    openssl pkcs12 -export -in kafka-server-cert.pem -inkey kafka-server-key.pem \
        -out kafka.keystore.p12 -name kafka -password pass:$KEYSTORE_PASSWORD
    echo "✓ PKCS12 keystore created"
else
    echo "✓ PKCS12 keystore already exists"
fi

# Convert PKCS12 to JKS keystore
if [ ! -f kafka.keystore.jks ]; then
    keytool -importkeystore -srckeystore kafka.keystore.p12 -srcstoretype PKCS12 \
        -srcstorepass $KEYSTORE_PASSWORD -destkeystore kafka.keystore.jks \
        -deststoretype JKS -deststorepass $KEYSTORE_PASSWORD -noprompt
    echo "✓ JKS keystore created"
else
    echo "✓ JKS keystore already exists"
fi

# Create truststore with CA certificate
if [ ! -f kafka.truststore.jks ]; then
    keytool -keystore kafka.truststore.jks -alias CARoot -import -file ca-cert.pem \
        -storepass $TRUSTSTORE_PASSWORD -noprompt
    echo "✓ Truststore created"
else
    echo "✓ Truststore already exists"
fi

# Create credential files for Docker
echo "$KEYSTORE_PASSWORD" > keystore_creds
echo "$KEY_PASSWORD" > key_creds
echo "$TRUSTSTORE_PASSWORD" > truststore_creds

echo "✓ Credential files created"

# Step 4: Generate SASL/SCRAM credentials
echo ""
echo "Step 4: Generating SASL/SCRAM credentials..."

# Create JAAS configuration file
cat > kafka_server_jaas.conf <<EOF
KafkaServer {
    org.apache.kafka.common.security.scram.ScramLoginModule required
    username="$KAFKA_ADMIN_USER"
    password="$KAFKA_ADMIN_PASSWORD";
};

Client {
    org.apache.kafka.common.security.plain.PlainLoginModule required
    username="$KAFKA_ADMIN_USER"
    password="$KAFKA_ADMIN_PASSWORD";
};
EOF

echo "✓ JAAS configuration created"

# Create client properties file for CLI tools
cat > client.properties <<EOF
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \\
    username="$KAFKA_ADMIN_USER" \\
    password="$KAFKA_ADMIN_PASSWORD";

ssl.truststore.location=$PWD/kafka.truststore.jks
ssl.truststore.password=$TRUSTSTORE_PASSWORD
ssl.keystore.location=$PWD/kafka.keystore.jks
ssl.keystore.password=$KEYSTORE_PASSWORD
ssl.key.password=$KEY_PASSWORD
EOF

echo "✓ Client properties file created"

# Create producer properties file
cat > producer.properties <<EOF
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \\
    username="$KAFKA_PRODUCER_USER" \\
    password="$KAFKA_PRODUCER_PASSWORD";

ssl.truststore.location=$PWD/kafka.truststore.jks
ssl.truststore.password=$TRUSTSTORE_PASSWORD
ssl.keystore.location=$PWD/kafka.keystore.jks
ssl.keystore.password=$KEYSTORE_PASSWORD
ssl.key.password=$KEY_PASSWORD
EOF

echo "✓ Producer properties file created"

# Create consumer properties file
cat > consumer.properties <<EOF
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \\
    username="$KAFKA_CONSUMER_USER" \\
    password="$KAFKA_CONSUMER_PASSWORD";

ssl.truststore.location=$PWD/kafka.truststore.jks
ssl.truststore.password=$TRUSTSTORE_PASSWORD
ssl.keystore.location=$PWD/kafka.keystore.jks
ssl.keystore.password=$KEYSTORE_PASSWORD
ssl.key.password=$KEY_PASSWORD

group.id=caracal-consumer-group
EOF

echo "✓ Consumer properties file created"

# Step 5: Create environment file for Docker Compose
echo ""
echo "Step 5: Creating environment file..."
cd ..

cat > .env.kafka <<EOF
# Kafka Security Configuration
# Generated by setup-kafka-security.sh

# Keystore and Truststore Passwords
KAFKA_KEYSTORE_PASSWORD=$KEYSTORE_PASSWORD
KAFKA_TRUSTSTORE_PASSWORD=$TRUSTSTORE_PASSWORD
KAFKA_KEY_PASSWORD=$KEY_PASSWORD

# SASL/SCRAM Credentials
KAFKA_ADMIN_USER=$KAFKA_ADMIN_USER
KAFKA_ADMIN_PASSWORD=$KAFKA_ADMIN_PASSWORD
KAFKA_PRODUCER_USER=$KAFKA_PRODUCER_USER
KAFKA_PRODUCER_PASSWORD=$KAFKA_PRODUCER_PASSWORD
KAFKA_CONSUMER_USER=$KAFKA_CONSUMER_USER
KAFKA_CONSUMER_PASSWORD=$KAFKA_CONSUMER_PASSWORD
KAFKA_SCHEMA_REGISTRY_USER=$KAFKA_SCHEMA_REGISTRY_USER
KAFKA_SCHEMA_REGISTRY_PASSWORD=$KAFKA_SCHEMA_REGISTRY_PASSWORD
EOF

echo "✓ Environment file created: .env.kafka"

# Step 6: Instructions for creating SCRAM credentials in Kafka
echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start Kafka cluster:"
echo "   docker-compose -f docker-compose.kafka.yml up -d"
echo ""
echo "2. Wait for Kafka to be ready (check with 'docker-compose -f docker-compose.kafka.yml logs -f')"
echo ""
echo "3. Create SCRAM credentials in Kafka:"
echo "   docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \\"
echo "     --alter --add-config 'SCRAM-SHA-512=[password=$KAFKA_ADMIN_PASSWORD]' \\"
echo "     --entity-type users --entity-name $KAFKA_ADMIN_USER"
echo ""
echo "   docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \\"
echo "     --alter --add-config 'SCRAM-SHA-512=[password=$KAFKA_PRODUCER_PASSWORD]' \\"
echo "     --entity-type users --entity-name $KAFKA_PRODUCER_USER"
echo ""
echo "   docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \\"
echo "     --alter --add-config 'SCRAM-SHA-512=[password=$KAFKA_CONSUMER_PASSWORD]' \\"
echo "     --entity-type users --entity-name $KAFKA_CONSUMER_USER"
echo ""
echo "   docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \\"
echo "     --alter --add-config 'SCRAM-SHA-512=[password=$KAFKA_SCHEMA_REGISTRY_PASSWORD]' \\"
echo "     --entity-type users --entity-name $KAFKA_SCHEMA_REGISTRY_USER"
echo ""
echo "4. Verify SCRAM credentials:"
echo "   docker exec -it caracal-kafka-1 kafka-configs --zookeeper zookeeper-1:2181 \\"
echo "     --describe --entity-type users"
echo ""
echo "Generated files:"
echo "  - $CERTS_DIR/ca-cert.pem (CA certificate)"
echo "  - $CERTS_DIR/ca-key.pem (CA private key)"
echo "  - $CERTS_DIR/kafka-server-cert.pem (Kafka broker certificate)"
echo "  - $CERTS_DIR/kafka-server-key.pem (Kafka broker private key)"
echo "  - $CERTS_DIR/kafka.keystore.jks (Java keystore)"
echo "  - $CERTS_DIR/kafka.truststore.jks (Java truststore)"
echo "  - $CERTS_DIR/client.properties (Kafka client configuration)"
echo "  - $CERTS_DIR/producer.properties (Kafka producer configuration)"
echo "  - $CERTS_DIR/consumer.properties (Kafka consumer configuration)"
echo "  - .env.kafka (Docker Compose environment file)"
echo ""
echo "IMPORTANT: Keep these files secure and do not commit them to version control!"
echo ""
