---
sidebar_position: 8
title: Pricebook Commands
---

# Pricebook Commands

The `pricebook` command group manages resource pricing for cost calculation.

```
caracal pricebook COMMAND [OPTIONS]
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`list`](#list) | List all resource prices |
| [`get`](#get) | Get price for a specific resource |
| [`set`](#set) | Set price for a resource |
| [`import`](#import) | Import prices from CSV file |

---

## Pricing Structure

| Field | Description |
|-------|-------------|
| resource_type | Unique identifier (e.g., `openai.gpt-4.output_tokens`) |
| price | Price per unit |
| currency | Currency code (USD) |
| unit | Quantity unit (e.g., tokens, seconds) |

### Resource Type Naming Convention

```
provider.model.resource_type
```

| Example | Provider | Model | Resource |
|---------|----------|-------|----------|
| `openai.gpt-4.input_tokens` | OpenAI | GPT-4 | Input tokens |
| `openai.gpt-4.output_tokens` | OpenAI | GPT-4 | Output tokens |
| `anthropic.claude-3.input_tokens` | Anthropic | Claude 3 | Input tokens |
| `openai.whisper-1.seconds` | OpenAI | Whisper | Audio seconds |

---

## list

List all resource prices.

```
caracal pricebook list [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--provider` | `-p` | - | Filter by provider |
| `--format` | `-f` | table | Output format |

### Examples

<details>
<summary>List All Prices</summary>

```bash
caracal pricebook list
```

**Output:**
```
Resource Prices
===============

Resource Type                         Price         Currency    Unit
------------------------------------------------------------------------
openai.gpt-4.input_tokens             $0.00003      USD         token
openai.gpt-4.output_tokens            $0.00006      USD         token
openai.gpt-4-turbo.input_tokens       $0.00001      USD         token
openai.gpt-4-turbo.output_tokens      $0.00003      USD         token
openai.gpt-3.5-turbo.input_tokens     $0.0000005    USD         token
openai.gpt-3.5-turbo.output_tokens    $0.0000015    USD         token
anthropic.claude-3.input_tokens       $0.000008     USD         token
anthropic.claude-3.output_tokens      $0.000024     USD         token
openai.whisper-1.seconds              $0.0001       USD         second
openai.dall-e-3.images                $0.04         USD         image

Total: 10 resource types
```

</details>

<details>
<summary>Filter by Provider</summary>

```bash
caracal pricebook list --provider openai
```

</details>

<details>
<summary>JSON Output</summary>

```bash
caracal pricebook list --format json
```

**Output:**
```json
[
  {
    "resource_type": "openai.gpt-4.input_tokens",
    "price": "0.00003",
    "currency": "USD",
    "unit": "token"
  },
  {
    "resource_type": "openai.gpt-4.output_tokens",
    "price": "0.00006",
    "currency": "USD",
    "unit": "token"
  }
]
```

</details>

---

## get

Get price for a specific resource.

```
caracal pricebook get [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|:--------:|-------------|
| `--resource-type` | `-r` | Yes | Resource type identifier |
| `--format` | `-f` | No | Output format |

### Examples

<details>
<summary>Get Single Price</summary>

```bash
caracal pricebook get --resource-type openai.gpt-4.output_tokens
```

**Output:**
```
Resource: openai.gpt-4.output_tokens
Price:    $0.00006 USD per token
```

</details>

---

## set

Set price for a resource.

```
caracal pricebook set [OPTIONS]
```

### Options

| Option | Short | Required | Default | Description |
|--------|-------|:--------:|---------|-------------|
| `--resource-type` | `-r` | Yes | - | Resource type identifier |
| `--price` | `-p` | Yes | - | Price per unit |
| `--currency` | `-c` | No | USD | Currency code |
| `--unit` | `-u` | No | - | Unit description |

### Examples

<details>
<summary>Set New Price</summary>

```bash
caracal pricebook set \
  --resource-type openai.gpt-5.input_tokens \
  --price 0.0001 \
  --unit token
```

**Output:**
```
Price updated successfully!

Resource Type: openai.gpt-5.input_tokens
New Price:     $0.0001 USD per token
Previous:      (new entry)
```

</details>

<details>
<summary>Update Existing Price</summary>

```bash
caracal pricebook set \
  --resource-type openai.gpt-4.output_tokens \
  --price 0.00005
```

**Output:**
```
Price updated successfully!

Resource Type: openai.gpt-4.output_tokens
New Price:     $0.00005 USD per token
Previous:      $0.00006 USD per token
Change:        -16.7%
```

</details>

---

## import

Import prices from CSV file.

```
caracal pricebook import [OPTIONS] FILE
```

### Arguments

| Argument | Description |
|----------|-------------|
| FILE | Path to CSV file |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--overwrite` | | false | Overwrite existing prices |
| `--dry-run` | | false | Preview without importing |

### CSV Format

```csv
resource_type,price,currency,unit
openai.gpt-4.input_tokens,0.00003,USD,token
openai.gpt-4.output_tokens,0.00006,USD,token
anthropic.claude-3.input_tokens,0.000008,USD,token
```

### Examples

<details>
<summary>Import from CSV</summary>

```bash
caracal pricebook import prices.csv
```

**Output:**
```
Importing prices from: prices.csv

  [OK] openai.gpt-4.input_tokens: $0.00003
  [OK] openai.gpt-4.output_tokens: $0.00006
  [OK] anthropic.claude-3.input_tokens: $0.000008
  [SKIP] openai.gpt-3.5-turbo: already exists (use --overwrite)

Imported: 3 prices
Skipped: 1 (already exists)
```

</details>

<details>
<summary>Dry Run</summary>

```bash
caracal pricebook import prices.csv --dry-run
```

**Output:**
```
DRY RUN - No changes will be made

Would import:
  openai.gpt-4.input_tokens: $0.00003
  openai.gpt-4.output_tokens: $0.00006
  anthropic.claude-3.input_tokens: $0.000008

Would skip (already exists):
  openai.gpt-3.5-turbo
```

</details>

---

## See Also

- [Ledger Commands](./ledger) - View cost calculations
- [Policy Commands](./policy) - Set budget limits
