# Coin87 Information Reliability Core

## Core Philosophy

Coin87 is a **real-time crypto news reliability intelligence platform**.

The crypto market does not suffer from lack of information.
It suffers from lack of **trust in information**.

---

## What Coin87 Does NOT Do

❌ **Predict price** – Never attempt to forecast price movements
❌ **Generate trading signals** – No buy/sell recommendations
❌ **Evaluate market outcomes** – No correlation with price/volume
❌ **Use market metrics** – No price, volume, volatility, funding rates
❌ **Infer intent** – No buy/sell/alpha/win rate terminology

---

## What Coin87 DOES

✅ **Information Clustering** – Group related information signals into narrative clusters
✅ **Source Behavior Analysis** – Track source reliability over time
✅ **Temporal Persistence** – Monitor how long information remains valid
✅ **Cross-Source Confirmation** – Detect corroboration and contradiction
✅ **Reliability Scoring** – Evaluate information trustworthiness

---

## Core Concepts

### 1. Information Signal
A discrete piece of information or narrative that emerges across one or more sources.
Information signals are evaluated for **reliability**, not market impact.

### 2. Reliability Score
A measure of how trustworthy an information signal is, based on:
- Source behavior history
- Cross-source confirmation count
- Temporal persistence (lifespan)
- Contradiction rate

### 3. Source Trust Index
A dynamic score representing how reliable a source has been historically.
Updated based on:
- Confirmation rate (how often information is verified by others)
- Consistency score (reporting consistency over time)
- Contradiction penalty (penalty for contradicted information)
- Persistence score (durability of information)

### 4. Narrative Cluster
A persistent information theme that can reactivate over time.
Narratives are tracked for:
- Saturation level (1-5)
- Status (ACTIVE, FADING, DORMANT)
- Temporal bounds (first_seen_at, last_seen_at)

### 5. Cross-Source Confirmation
The number of independent sources confirming the same information.
Higher confirmation = higher reliability score.

### 6. Temporal Persistence
How long an information signal persists before:
- Being contradicted
- Fading from discourse
- Being corrected

---

## Trust Score Calculation

```python
trust_score = (
    confirmation_rate * 0.35 +     # Cross-source confirmation frequency
    persistence_score * 0.25 +     # Information lifespan and durability
    consistency_score * 0.20 +     # Reporting consistency over time
    contradiction_penalty * 0.15 + # Penalty for contradicted information
    source_reputation * 0.05      # Historical source reputation
)
```

---

## Reliability Levels

| Level | Description |
|-------|-------------|
| `high` | Multiple independent sources confirm; long persistence |
| `medium` | Some confirmation; moderate persistence |
| `low` | Limited confirmation; short persistence |
| `unverified` | No cross-source confirmation; unknown reliability |

---

## Information Categories

| Category | Description |
|----------|-------------|
| `narrative` | Persistent theme or storyline across sources |
| `event` | Discrete, verifiable occurrence |
| `correction` | Information that contradicts previous signals |
| `rumor` | Unconfirmed, single-source information |

---

## Data Flow

```
Sources (News, Social, On-chain)
        ↓
Ingestion & Normalization
        ↓
Information Clustering
        ↓
Cross-Source Confirmation Analysis
        ↓
Reliability Evaluation
        ↓
Source Trust Update
        ↓
UI / Alerts (Reliability-weighted ranking)
```

---

## Forbidden Terminology

The following terms MUST NOT appear in Coin87 codebase:

- `price`, `volume`, `volatility`
- `bullish`, `bearish`, `market bias`
- `buy`, `sell`, `trade`, `trading signal`
- `alpha`, `win rate`, `signal accuracy`
- `market impact`, `price prediction`
- `funding rate`, `open interest`

---

## Allowed Terminology

- `reliability score`, `reliability level`
- `confirmation count`, `confirmation rate`
- `persistence hours`, `temporal persistence`
- `contradiction rate`, `contradiction detected`
- `source trust`, `source behavior`
- `narrative cluster`, `saturation level`
- `information signal`, `information category`

---

## Design Principles

1. **No infinite feeds** – Surface only meaningful information
2. **No price charts** – Information reliability, not market data
3. **No trading calls** – Reliability assessment, not action recommendation
4. **No dopamine-driven UI** – Calm, sparse, decision-oriented
5. **Silence is a feature** – If nothing important, show nothing

---

## Guiding Rule

> If a feature makes Coin87 louder, faster, or more sensational,
> it does not belong in this project.

Coin87 exists to help users understand **which information deserves attention**,
not what action to take.
