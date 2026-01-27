# Coin87 System Architecture

## 1. High-Level System Architecture

### Core Modules & Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                        COIN87 SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (PWA)          │  API Gateway (FastAPI)              │
│  ├── Mobile App          │  ├── Authentication                 │
│  ├── Web Dashboard       │  ├── Rate Limiting                  │
│  └── Admin Panel         │  └── Request Routing                │
├─────────────────────────────────────────────────────────────────┤
│                    CORE PROCESSING LAYER                       │
├─────────────────────────────────────────────────────────────────┤
│  Ingestion Engine        │  Evaluation Engine                  │
│  ├── Source Manager      │  ├── Content Analyzer              │
│  ├── RSS/Web Scrapers    │  ├── Impact Classifier             │
│  ├── Social Media APIs   │  ├── Sentiment Analyzer            │
│  └── Content Normalizer  │  └── Confidence Scorer             │
├─────────────────────────────────────────────────────────────────┤
│  Learning Engine         │  Publishing Engine                 │
│  ├── Trust Score ML      │  ├── Content Ranker                │
│  ├── Pattern Recognition │  ├── Notification System           │
│  ├── Feedback Loop       │  └── API Endpoints                 │
│  └── Model Retraining    │                                     │
├─────────────────────────────────────────────────────────────────┤
│                      DATA LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL              │  Redis Cache                        │
│  ├── News Articles       │  ├── Session Data                  │
│  ├── Sources & Scores    │  ├── Rate Limiting                 │
│  ├── User Data           │  ├── Processed Content             │
│  └── Analytics           │  └── ML Model Cache                │
├─────────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│  Task Queue (Celery)     │  Monitoring & Logging              │
│  ├── Ingestion Jobs      │  ├── Health Checks                 │
│  ├── ML Training Jobs    │  ├── Performance Metrics           │
│  └── Cleanup Tasks       │  └── Error Tracking                │
└─────────────────────────────────────────────────────────────────┘
```

### Module Breakdown

#### 1. **Ingestion Engine**
- **Source Manager**: Dynamic enable/disable of sources, source metadata management
- **Content Collectors**: RSS feeds, web scrapers, free social media APIs
- **Content Normalizer**: Standardize content format, extract key information
- **Deduplication**: Prevent duplicate content ingestion

#### 2. **Reliability Evaluation Engine**
- **Content Analyzer**: Extract entities, keywords, semantic structure
- **Reliability Classifier**: Categorize information reliability (verified, unverified, noise)
- **Source Behavior Scorer**: Calculate reliability based on source history, cross-confirmation, temporal persistence
- **Clustering Processor**: Group related information signals into narrative clusters

#### 3. **Source Trust Engine**
- **Trust Score Calculator**: ML model for dynamic source reliability scoring
- **Behavior Recognition**: Identify source consistency and reliability patterns
- **Persistence Tracking**: Monitor information lifespan and confirmation over time
- **Cross-Source Validation**: Detect corroboration and contradiction across sources

#### 4. **Publishing Engine**
- **Content Ranker**: Sort and prioritize content for publication
- **Multi-channel Publisher**: PWA, web, API endpoints
- **Notification System**: Push notifications for high-impact news
- **Reliability Tracker**: Monitor information persistence and source behavior

## 2. Data Flow Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   Sources   │───▶│  Ingestion   │───▶│ Evaluation  │───▶│ Learning &   │
│             │    │   Engine     │    │   Engine    │    │ Trust Update │
│ • RSS Feeds │    │              │    │             │    │              │
│ • Web APIs  │    │ • Collect    │    │ • Analyze   │    │ • Update     │
│ • Scrapers  │    │ • Normalize  │    │ • Score     │    │   Trust      │
│ • Social    │    │ • Dedupe     │    │ • Classify  │    │ • Learn      │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                            │                   │                   │
                            ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ PostgreSQL  │◀───│    Redis     │◀───│ Publishing  │◀───│   Feedback   │
│             │    │   Cache      │    │   Engine    │    │    Loop      │
│ • Raw Data  │    │              │    │             │    │              │
│ • Scores    │    │ • Processed  │    │ • Rank      │    │ • User       │
│ • Analytics │    │ • Sessions   │    │ • Publish   │    │   Actions    │
│ • History   │    │ • ML Cache   │    │ • Notify    │    │ • Source     │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
```

### Detailed Data Flow Steps

1. **Ingestion Phase**
   - Sources polled every 5-15 minutes (configurable per source)
   - Content normalized to standard schema
   - Duplicate detection using content hash + fuzzy matching
   - Raw content stored with metadata

2. **Evaluation Phase**
   - Content analysis (NLP, entity extraction)
   - Impact classification using ML model
   - Confidence scoring based on multiple factors
   - Cross-reference with existing knowledge base

3. **Trust Update Phase**
   - Trust scores updated based on historical source behavior
   - Pattern recognition for consistent, reliable reporting
   - Cross-source confirmation analysis for reliability scoring

4. **Publishing Phase**
   - Content ranked by composite score
   - Multi-channel distribution (PWA, web, API)
   - User interaction tracking for feedback

## 3. Core Database Tables

### PostgreSQL Schema

#### **sources**
```sql
-- Source management and trust scoring
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    source_type VARCHAR(50), -- 'rss', 'api', 'scraper', 'social'
    is_enabled BOOLEAN DEFAULT true,
    trust_score DECIMAL(3,2) DEFAULT 0.50, -- 0.00 to 1.00
    reliability_history JSONB, -- Historical performance data
    last_fetched TIMESTAMP,
    fetch_frequency INTEGER DEFAULT 900, -- seconds
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### **news_articles**
```sql
-- Core news content and metadata
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    title TEXT NOT NULL,
    content TEXT,
    url TEXT UNIQUE,
    content_hash VARCHAR(64) UNIQUE, -- For deduplication
    published_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW(),
    
    -- Scoring and classification
    impact_score DECIMAL(3,2), -- 0.00 to 1.00
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    sentiment_score DECIMAL(3,2), -- -1.00 to 1.00
    impact_category VARCHAR(50), -- 'high', 'medium', 'low', 'noise'
    
    -- Content analysis
    entities JSONB, -- Extracted entities (coins, people, companies)
    keywords TEXT[],
    language VARCHAR(10) DEFAULT 'en',
    
    -- Publishing status
    is_published BOOLEAN DEFAULT false,
    published_at TIMESTAMP,
    view_count INTEGER DEFAULT 0,
    
    -- Metadata
    raw_data JSONB, -- Original scraped data
    processing_status VARCHAR(20) DEFAULT 'pending'
);
```

#### **trust_score_history**
```sql
-- Track trust score changes over time
CREATE TABLE trust_score_history (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    article_id INTEGER REFERENCES news_articles(id),
    old_trust_score DECIMAL(3,2),
    new_trust_score DECIMAL(3,2),
    adjustment_reason VARCHAR(100),
    cross_confirmation_count INTEGER, -- Number of sources confirming
    persistence_hours INTEGER, -- How long information remained valid
    contradiction_detected BOOLEAN, -- Was information contradicted
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **user_interactions**
```sql
-- Track user behavior for learning
CREATE TABLE user_interactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50), -- Anonymous user ID
    article_id INTEGER REFERENCES news_articles(id),
    interaction_type VARCHAR(20), -- 'view', 'like', 'share', 'report'
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **source_behavior_metrics**
```sql
-- Track source reliability behavior over time
CREATE TABLE source_behavior_metrics (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    reporting_consistency DECIMAL(3,2), -- 0.00 to 1.00
    cross_confirmation_rate DECIMAL(3,2), -- How often confirmed by others
    contradiction_rate DECIMAL(3,2), -- How often contradicted
    average_persistence_hours INTEGER, -- Avg lifespan of information
    timestamp TIMESTAMP,
    evaluation_window_days INTEGER DEFAULT 30
);
```

#### **ml_models**
```sql
-- Track ML model versions and performance
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    model_path TEXT,
    performance_metrics JSONB,
    is_active BOOLEAN DEFAULT false,
    trained_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Redis Schema (Key Patterns)

```
# Session and caching
session:{user_id} -> user session data
cache:article:{id} -> processed article data
cache:source:{id}:trust -> current trust score

# Rate limiting
ratelimit:source:{id} -> fetch rate limiting
ratelimit:api:{endpoint} -> API rate limiting

# Processing queues
queue:ingestion -> pending ingestion tasks
queue:evaluation -> pending evaluation tasks
queue:ml_training -> ML training jobs

# Real-time data
trending:articles -> sorted set of trending articles
live:source:{id}:behavior -> real-time source reliability metrics
```

## 4. AI vs Rule-Based Logic Boundaries

### **AI-Powered Components**

#### **Content Analysis & Classification**
- **NLP Models**: 
  - Semantic analysis for information clustering
  - Entity extraction (spaCy, custom crypto entity models)
  - Content similarity detection for deduplication and clustering
  
- **Reliability Classification**:
  - ML model (Random Forest/XGBoost) trained on source behavior data
  - Features: source trust, content consistency, entity mentions, temporal patterns
  - Continuous learning from cross-source confirmation data

- **Trust Score Calculation**:
  - Gradient boosting model considering:
    - Historical cross-source confirmation rate
    - Consistency of reporting over time
    - Information persistence and lifespan
    - Contradiction rate and correction frequency
  
#### **Pattern Recognition**
- **Source Behavior Analysis**:
  - Time-series analysis to detect source reliability patterns
  - Identify sources with consistent, verified reporting
  - Temporal pattern detection for information lifecycle

### **Rule-Based Components**

#### **Content Filtering & Validation**
- **Spam Detection**:
  - Keyword blacklists
  - Content length thresholds
  - Duplicate content rules
  - Source reputation thresholds

- **Quality Gates**:
  - Minimum content length requirements
  - Required entity mentions (crypto-related)
  - Language detection and filtering
  - URL validation and domain checking

#### **Publishing Logic**
- **Reliability Ranking**:
  - Weighted combination of source trust scores
  - Time decay functions for information freshness
  - Cross-source confirmation multipliers
  - Contradiction penalty adjustments

- **Rate Limiting & Throttling**:
  - Maximum articles per source per hour
  - Duplicate content suppression windows
  - User notification frequency limits

## 5. Source Trust & Reliability Evolution System

### **Trust Score Calculation Framework**

#### **Base Trust Factors (Weighted)**
```python
trust_score = (
    confirmation_rate * 0.35 +     # Cross-source confirmation frequency
    persistence_score * 0.25 +     # Information lifespan and durability
    consistency_score * 0.20 +     # Reporting consistency over time
    contradiction_penalty * 0.15 + # Penalty for contradicted information
    source_reputation * 0.05      # Historical source reputation
)
```

#### **Reliability Learning Mechanisms**

1. **Cross-Source Confirmation Tracking**
   - Track how often information is confirmed by other sources
   - Time-weighted confirmation (recent confirmations weighted higher)
   - Category-specific confirmation (different weights for different info types)

2. **Temporal Persistence Analysis**
   - Measure information lifespan before contradiction or fade
   - Learn optimal persistence windows for different information types
   - Identify sources with consistently durable, verified information

3. **User Feedback Integration**
   - Track user engagement with articles from different sources
   - Learn from user "report as unreliable" or "verified" feedback
   - Use feedback to adjust source trust scores

4. **Continuous Model Updates**
   - Retrain models weekly with new data
   - A/B test new model versions against current production
   - Gradual rollout of improved models with performance monitoring

### **Reliability Feedback Loop Architecture**

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Source    │───▶│  Reliability │───▶│   Trust     │
│   Behavior  │    │   Engine     │    │   Update    │
└─────────────┘    └──────────────┘    └─────────────┘
       ▲                   ▲                   │
       │                   │                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│    User     │───▶│ Confirmation │◀───│   Source    │
│  Feedback   │    │   Analysis   │    │ Trust Score │
└─────────────┘    └──────────────┘    └─────────────┘
```

### **Trust Score Update Triggers**

1. **Real-time Updates**:
   - Immediate penalty for contradicted information
   - Bonus for cross-source confirmed information
   - User feedback integration

2. **Batch Updates** (Daily):
   - Cross-source confirmation analysis
   - Persistence score recalculation
   - Consistency metrics update

3. **Model Retraining** (Weekly):
   - Full source behavior dataset analysis
   - Feature importance updates
   - Model performance optimization

### **Cold Start Problem Solutions**

1. **New Source Onboarding**:
   - Start with neutral trust score (0.50)
   - Accelerated learning period with higher weight updates
   - Manual review and categorization for first 100 articles

2. **Domain Authority Integration**:
   - Use domain reputation services (free tiers)
   - Social media follower counts and engagement rates
   - Cross-reference with established crypto news aggregators

## Cost Optimization Strategies

### **Infrastructure Efficiency**
- Single VPS deployment with Docker containers
- PostgreSQL + Redis on same instance
- Celery workers for background processing
- Nginx for static file serving and load balancing

### **Data Source Optimization**
- Prioritize free RSS feeds and APIs
- Implement intelligent polling (reduce frequency for low-value sources)
- Use web scraping only for high-value sources without feeds
- Cache processed content aggressively

### **ML Model Efficiency**
- Use lightweight models (scikit-learn, lightweight transformers)
- Batch processing for non-real-time tasks
- Model caching and versioning
- Incremental learning where possible

This architecture provides a solid foundation for the coin87 project, balancing automation, intelligence, and cost efficiency while maintaining the flexibility to scale and improve over time.