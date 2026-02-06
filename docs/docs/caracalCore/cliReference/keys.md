---
sidebar_position: 11
title: Key Commands
---

# Key Commands

The `keys` command group manages cryptographic keys.

```
caracal keys COMMAND [OPTIONS]
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`list`](#list) | List all keys |
| [`rotate`](#rotate) | Rotate a key |
| [`export`](#export) | Export public key |

---

## Key Types

| Key Type | Algorithm | Purpose |
|----------|-----------|---------|
| `merkle-signing` | Ed25519 | Sign Merkle tree roots |
| `delegation` | Ed25519 | Sign delegation tokens |
| `config-encryption` | AES-256-GCM | Encrypt configuration secrets |

---

## list

List all keys.

```
caracal keys list [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--type` | `-t` | - | Filter by key type |
| `--format` | `-f` | table | Output format |

### Examples

<details>
<summary>List All Keys</summary>

```bash
caracal keys list
```

**Output:**
```
Cryptographic Keys
==================

Key ID                  Type              Algorithm    Created              Expires              Status
-----------------------------------------------------------------------------------------------------------
key-001-merkle          merkle-signing    Ed25519      2024-01-01T00:00     2025-01-01T00:00     [OK] Active
key-002-merkle          merkle-signing    Ed25519      2023-01-01T00:00     2024-01-01T00:00     Expired
key-001-delegation      delegation        Ed25519      2024-01-01T00:00     Never                [OK] Active
key-001-config          config-encryption AES-256-GCM  2024-01-01T00:00     Never                [OK] Active

Total: 4 keys (3 active, 1 expired)
```

</details>

<details>
<summary>Filter by Type</summary>

```bash
caracal keys list --type merkle-signing
```

</details>

---

## rotate

Rotate a key.

```
caracal keys rotate [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--key-type` | `-t` | Yes | Key type to rotate |
| `--expire-days` | | No | Days until new key expires |
| `--reason` | `-r` | No | Reason for rotation |

### Examples

<details>
<summary>Rotate Merkle Signing Key</summary>

```bash
caracal keys rotate \
  --key-type merkle-signing \
  --expire-days 365 \
  --reason "Annual key rotation"
```

**Output:**
```
Rotating merkle-signing key...

[WARNING] This will create a new signing key.
          The old key will be marked as expired.
          New Merkle proofs will use the new key.

Proceed? (yes/no): yes

Key Rotation Complete
---------------------

Old Key:
  Key ID:   key-001-merkle
  Status:   Expired (graceful)

New Key:
  Key ID:   key-003-merkle
  Algorithm: Ed25519
  Created:  2024-01-15T10:00:00Z
  Expires:  2025-01-15T10:00:00Z

[OK] Key rotation successful

Note: Verify new proofs with updated public key.
```

</details>

### Key Rotation Schedule

| Key Type | Recommended Rotation |
|----------|---------------------|
| `merkle-signing` | Annually or on security events |
| `delegation` | Never (per-agent keys) |
| `config-encryption` | On compromise only |

---

## export

Export public key.

```
caracal keys export [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--key-id` | `-k` | Yes | Key ID to export |
| `--output` | `-o` | No | Output file path |
| `--format` | `-f` | No | Format: pem, jwk, base64 |

### Examples

<details>
<summary>Export to PEM</summary>

```bash
caracal keys export \
  --key-id key-001-merkle \
  --format pem \
  --output merkle-public.pem
```

**Output:**
```
Exporting public key: key-001-merkle

Format:  PEM
Output:  merkle-public.pem

[OK] Public key exported successfully

Note: This is the PUBLIC key only.
      Private key is never exported.
```

**merkle-public.pem:**
```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA7mCqAq8kVg3GkLz3t5OnYThNqNYh3Vq9JH2k8LoQaAA=
-----END PUBLIC KEY-----
```

</details>

<details>
<summary>Export to JWK</summary>

```bash
caracal keys export \
  --key-id key-001-merkle \
  --format jwk
```

**Output:**
```json
{
  "kty": "OKP",
  "crv": "Ed25519",
  "x": "7mCqAq8kVg3GkLz3t5OnYThNqNYh3Vq9JH2k8LoQaAA",
  "kid": "key-001-merkle",
  "use": "sig",
  "alg": "EdDSA"
}
```

</details>

---

## Security Best Practices

| Practice | Description |
|----------|-------------|
| Regular rotation | Rotate merkle-signing keys annually |
| Secure storage | Store keys in HSM or secure enclave in production |
| Backup | Backup encrypted keys with master password |
| Audit | Log all key operations |
| Recovery | Document key recovery procedures |

---

## See Also

- [Merkle Commands](./merkle) - Uses signing keys for proofs
- [Delegation Commands](./delegation) - Uses agent keys for tokens
- [Backup Commands](./backup) - Include keys in backups
