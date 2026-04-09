# Secure MQTT Setup with Mosquitto

## Overview

This document describes a secure configuration for an MQTT broker using Mosquitto. It covers:

* TLS encryption
* Client authentication
* Access control (ACL)
* Security best practices

---

# 1. Mosquitto Secure Configuration

## mosquitto.conf

```conf
# Disable anonymous access
allow_anonymous false

# Password authentication
password_file /etc/mosquitto/passwd

# ACL file for authorization
acl_file /etc/mosquitto/acl

# TLS listener (secure MQTT)
listener 8883
protocol mqtt

# TLS configuration
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key

# Require client certificate (mTLS)
require_certificate true
use_identity_as_username true

# Security hardening
tls_version tlsv1.2

# Limits
max_connections 100
message_size_limit 10240

# Logging
log_type error
log_type warning
log_type notice
log_type information
```

---

# 2. User Authentication

## Create Password File

```bash
mosquitto_passwd -c /etc/mosquitto/passwd user1
mosquitto_passwd /etc/mosquitto/passwd user2
```

Clients authenticate using:

* Username
* Password
* Client certificate (if enabled)

---

# 3. Authorization (ACL)

## ACL File Example

```
# User 1 can publish temperature data
user sensor1
topic write home/sensors/temperature

# User 2 can read all sensor data
user app1
topic read home/sensors/#

# Admin user (full access)
user admin
topic readwrite #
```

---

# 4. TLS Certificates

## Required Files

* `ca.crt` → Certificate Authority
* `server.crt` → Broker certificate
* `server.key` → Private key
* Client certificates (for mTLS)

## Generate Self-Signed Certificates (Example)

```bash
# CA
openssl req -new -x509 -days 365 -keyout ca.key -out ca.crt

# Server certificate
openssl req -new -out server.csr -keyout server.key
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365
```

Do not use self-signed certificates in a production enviroment.

---

# 5. Client Connection Examples

## Using mosquitto_pub

```bash
mosquitto_pub \
  -h broker.example.com \
  -p 8883 \
  --cafile ca.crt \
  --cert client.crt \
  --key client.key \
  -u user1 \
  -P password \
  -t home/sensors/temperature \
  -m "22.5"
```

## Using mosquitto_sub

```bash
mosquitto_sub \
  -h broker.example.com \
  -p 8883 \
  --cafile ca.crt \
  --cert client.crt \
  --key client.key \
  -u user2 \
  -P password \
  -t home/sensors/#
```

---

# 6. Security Architecture

## Transport Security

* TLS encryption (port 8883)
* Prevents eavesdropping and MITM attacks

## Authentication

* Username/password
* Optional mutual TLS (client certificates)

## Authorization

* ACL rules restrict topic access
* Fine-grained read/write permissions

---

# 7. Best Practices

### Disable Anonymous Access

```
allow_anonymous false
```

### Use Mutual TLS (mTLS)

* Strong identity verification
* Ideal for IoT deployments

### Apply Least Privilege

* Limit access per topic
* Avoid `topic #` unless necessary

### Use Unique Client IDs

* Prevent session hijacking

### Monitor Logs

```
log_type all
```

### Keep Software Updated

* Always use the latest Mosquitto version

---

# 8. Summary

A secure MQTT deployment requires:

| Layer          | Mechanism               |
| -------------- | ----------------------- |
| Transport      | TLS (port 8883)         |
| Authentication | Password / Certificates |
| Authorization  | ACL                     |



