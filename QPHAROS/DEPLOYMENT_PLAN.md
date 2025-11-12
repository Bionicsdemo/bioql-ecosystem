# QPHAROS - Production Deployment Plan

## 🎯 Overview

This document outlines the complete deployment strategy to transform QPHAROS from a local prototype into a production-ready SaaS platform that customers can access and pay for.

## 📋 Deployment Phases

### Phase 1: Infrastructure Setup (Weeks 1-2)
### Phase 2: API Development (Weeks 3-4)
### Phase 3: Web Dashboard (Weeks 5-8)
### Phase 4: Payment Integration (Week 9)
### Phase 5: Beta Launch (Week 10-12)
### Phase 6: Public Launch (Week 13+)

---

## 🏗️ Phase 1: Infrastructure Setup (Weeks 1-2)

### Cloud Platform Selection

**Recommended: AWS (Amazon Web Services)**

**Why AWS?**
- ✅ Mature ML/AI tools
- ✅ Global presence
- ✅ IBM Quantum compatibility
- ✅ Robust security
- ✅ Scalability

**Alternative: Google Cloud Platform (GCP)**
- Better for ML workloads
- Competitive pricing
- Good quantum computing integration

### AWS Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Route 53 (DNS)                      │
│              https://api.qpharos.bioql.bio              │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              CloudFront (CDN + WAF)                     │
│              SSL Certificate (ACM)                      │
└─────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│   ALB (Load Balancer)   │  │   S3 (Static Assets)    │
│   api.qpharos.bio       │  │   Web Dashboard         │
└─────────────────────────┘  └─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│              ECS Fargate (Containers)                   │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  FastAPI     │  │  Celery      │  │  Celery     │ │
│  │  Web Server  │  │  Worker 1    │  │  Worker 2   │ │
│  └──────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────┘
                │                │
                ▼                ▼
┌─────────────────────┐  ┌─────────────────────┐
│   RDS PostgreSQL    │  │  ElastiCache Redis  │
│   (Database)        │  │  (Queue + Cache)    │
└─────────────────────┘  └─────────────────────┘
```

### Infrastructure as Code (Terraform)

```hcl
# main.tf
provider "aws" {
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "qpharos_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "qpharos-vpc"
  }
}

# RDS Database
resource "aws_db_instance" "qpharos_db" {
  identifier           = "qpharos-db"
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  storage_type         = "gp3"
  db_name              = "qpharos"
  username             = "qpharos_admin"
  password             = var.db_password
  multi_az             = true
  backup_retention_period = 7

  tags = {
    Name = "qpharos-database"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "qpharos_redis" {
  cluster_id           = "qpharos-redis"
  engine               = "redis"
  node_type            = "cache.t3.medium"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}

# ECS Cluster
resource "aws_ecs_cluster" "qpharos_cluster" {
  name = "qpharos-cluster"
}

# S3 Bucket for results
resource "aws_s3_bucket" "qpharos_results" {
  bucket = "qpharos-results"

  tags = {
    Name = "qpharos-results"
  }
}
```

### Estimated AWS Costs

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| ECS Fargate | 3 containers (2 vCPU, 4GB) | $150 |
| RDS PostgreSQL | db.t3.medium, Multi-AZ | $180 |
| ElastiCache Redis | cache.t3.medium | $50 |
| ALB | Load balancer + data transfer | $40 |
| S3 | 100GB storage + requests | $25 |
| CloudFront | CDN + data transfer | $30 |
| Route 53 | DNS hosting | $1 |
| **TOTAL** | | **$476/month** |

*Note: Scales with usage. At 1000 active users, expect $2K-3K/month*

---

## 🔧 Phase 2: API Development (Weeks 3-4)

### FastAPI Backend

**Directory Structure:**
```
qpharos-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── database.py          # DB connection
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── job.py
│   │   └── subscription.py
│   ├── routers/             # API endpoints
│   │   ├── auth.py
│   │   ├── screening.py
│   │   ├── binding.py
│   │   ├── admet.py
│   │   ├── generation.py
│   │   └── pipeline.py
│   ├── services/            # Business logic
│   │   └── qpharos_service.py
│   ├── tasks/               # Celery tasks
│   │   └── quantum_tasks.py
│   └── utils/
│       ├── auth.py
│       └── rate_limit.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Main API Implementation

```python
# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import sys
import os

# Add QPHAROS to path
sys.path.insert(0, '/path/to/QPHAROS')
from QPHAROS import QuantumDrugDesignPipeline, QPHAROSConfig

app = FastAPI(
    title="QPHAROS API",
    version="1.0.0",
    description="Quantum Pharmaceutical Optimization System"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.qpharos.bio"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Routes
@app.post("/api/v1/screen/molecule")
async def screen_molecule(
    smiles: str,
    target: str,
    token: str = Depends(security)
):
    """Screen a single molecule against target protein"""

    # Verify API key
    user = verify_api_key(token.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check quota
    if not check_quota(user, "screening", 1):
        raise HTTPException(status_code=429, detail="Quota exceeded")

    # Create job
    job_id = create_job(user.id, "screening", {
        "smiles": smiles,
        "target": target
    })

    # Queue task
    from app.tasks.quantum_tasks import run_screening
    task = run_screening.delay(job_id, smiles, target)

    # Update usage
    update_usage(user.id, "screening", 1, 50.0)

    return {
        "job_id": job_id,
        "status": "queued",
        "task_id": task.id
    }

@app.get("/api/v1/screen/{job_id}/status")
async def get_job_status(
    job_id: str,
    token: str = Depends(security)
):
    """Get status of screening job"""
    user = verify_api_key(token.credentials)
    job = get_job(job_id)

    if job.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "job_id": job_id,
        "status": job.status,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "results": job.results if job.status == "completed" else None
    }

@app.post("/api/v1/pipeline/design-drug")
async def design_drug(
    target: str,
    disease: str,
    iterations: int = 50,
    token: str = Depends(security)
):
    """Run complete drug design pipeline"""

    user = verify_api_key(token.credentials)

    # Check quota (full pipeline = 10 screening equivalents)
    if not check_quota(user, "pipeline", 1):
        raise HTTPException(status_code=429, detail="Quota exceeded")

    # Create job
    job_id = create_job(user.id, "pipeline", {
        "target": target,
        "disease": disease,
        "iterations": iterations
    })

    # Queue task
    from app.tasks.quantum_tasks import run_drug_design
    task = run_drug_design.delay(job_id, target, disease, iterations)

    # Update usage
    update_usage(user.id, "pipeline", 1, 250.0)

    return {
        "job_id": job_id,
        "status": "queued",
        "estimated_time": f"{iterations * 2} minutes"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Celery Tasks

```python
# app/tasks/quantum_tasks.py
from celery import Celery
import sys
sys.path.insert(0, '/path/to/QPHAROS')
from QPHAROS import QuantumDrugDesignPipeline, QPHAROSConfig

celery_app = Celery('qpharos', broker='redis://redis:6379/0')

@celery_app.task(bind=True)
def run_screening(self, job_id, smiles, target):
    """Background task for molecular screening"""

    # Update job status
    update_job_status(job_id, "running")

    try:
        # Initialize QPHAROS
        config = QPHAROSConfig(backend="ibm_torino")
        from QPHAROS.core.quantum_backend import QuantumBackend
        from QPHAROS.layers.layer2_binding import QuantumBindingPredictor

        backend = QuantumBackend(config)
        predictor = QuantumBindingPredictor(backend, config)

        # Run prediction
        result = predictor.predict_binding(
            ligand_smiles=smiles,
            protein_pdb=target
        )

        # Save results
        update_job_status(job_id, "completed", results=result)

        return {"status": "success", "results": result}

    except Exception as e:
        update_job_status(job_id, "failed", error=str(e))
        return {"status": "failed", "error": str(e)}

@celery_app.task(bind=True)
def run_drug_design(self, job_id, target, disease, iterations):
    """Background task for full drug design pipeline"""

    update_job_status(job_id, "running")

    try:
        # Initialize pipeline
        pipeline = QuantumDrugDesignPipeline(
            target_protein=target,
            disease_profile=disease,
            backend="ibm_torino"
        )

        # Run design
        results = pipeline.design_drug(
            iterations=iterations,
            save_results=True
        )

        # Save results
        update_job_status(job_id, "completed", results=results)

        return {"status": "success", "results": results}

    except Exception as e:
        update_job_status(job_id, "failed", error=str(e))
        return {"status": "failed", "error": str(e)}
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy QPHAROS
COPY QPHAROS/ /app/QPHAROS/

# Copy API code
COPY app/ /app/app/
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/qpharos
      - REDIS_URL=redis://redis:6379/0
      - BIOQL_API_KEY=${BIOQL_API_KEY}
    depends_on:
      - db
      - redis

  celery-worker:
    build: .
    command: celery -A app.tasks.quantum_tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/qpharos
      - REDIS_URL=redis://redis:6379/0
      - BIOQL_API_KEY=${BIOQL_API_KEY}
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=qpharos
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## 🌐 Phase 3: Web Dashboard (Weeks 5-8)

### Technology Stack

- **Frontend Framework:** React 18 + TypeScript
- **Styling:** Tailwind CSS
- **State Management:** Zustand
- **API Client:** Axios + React Query
- **Charts:** Recharts
- **Tables:** TanStack Table
- **Forms:** React Hook Form + Zod

### Dashboard Features

1. **Home Dashboard**
   - Usage statistics
   - Recent jobs
   - Quick actions

2. **Molecular Screening**
   - SMILES input
   - Target selection
   - Batch upload (CSV)
   - Results visualization

3. **Drug Design Pipeline**
   - Target configuration
   - Parameter tuning
   - Progress tracking
   - Results download

4. **ADMET Analysis**
   - Molecule submission
   - Lipinski checking
   - Property charts

5. **Usage & Billing**
   - Current usage
   - Billing history
   - Invoice download
   - Subscription management

### Key Components

```typescript
// src/components/ScreeningForm.tsx
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { screenMolecule } from '@/api/qpharos';

export function ScreeningForm() {
  const [smiles, setSmiles] = useState('');
  const [target, setTarget] = useState('6B3J');

  const mutation = useMutation({
    mutationFn: screenMolecule,
    onSuccess: (data) => {
      console.log('Job created:', data.job_id);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({ smiles, target });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium">
          SMILES String
        </label>
        <input
          type="text"
          value={smiles}
          onChange={(e) => setSmiles(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300"
          placeholder="COc1ccc2cc3[n+]cc2c1OC)CCc1cc2c(cc1-3)OCO2"
        />
      </div>

      <div>
        <label className="block text-sm font-medium">
          Target Protein
        </label>
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300"
        >
          <option value="6B3J">GLP-1R (6B3J)</option>
          <option value="4EIY">AMPK</option>
          <option value="6A93">5-HT2A</option>
        </select>
      </div>

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full bg-blue-600 text-white py-2 rounded-md"
      >
        {mutation.isPending ? 'Screening...' : 'Screen Molecule'}
      </button>
    </form>
  );
}
```

### Deployment (Vercel)

```bash
# Install Vercel CLI
npm install -g vercel

# Build and deploy
cd qpharos-dashboard
vercel --prod
```

---

## 💳 Phase 4: Payment Integration (Week 9)

### Stripe Integration

```python
# app/routers/billing.py
import stripe
from fastapi import APIRouter, Depends

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/api/v1/billing/create-checkout")
async def create_checkout_session(
    tier: str,
    user: User = Depends(get_current_user)
):
    """Create Stripe checkout session"""

    prices = {
        "research": "price_1234research",
        "professional": "price_1234professional",
        "enterprise": "price_1234enterprise"
    }

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": prices[tier],
            "quantity": 1
        }],
        mode="subscription",
        success_url="https://app.qpharos.bio/success",
        cancel_url="https://app.qpharos.bio/pricing"
    )

    return {"checkout_url": session.url}

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400)

    # Handle events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Activate subscription
        activate_subscription(session["customer"])

    elif event["type"] == "invoice.payment_succeeded":
        # Update billing
        pass

    return {"status": "success"}
```

---

## 🚀 Phase 5: Beta Launch (Weeks 10-12)

### Beta Partner Selection

**5 Companies:**
1. Academic lab (free)
2. Small biotech (50% discount)
3. Medium biotech (50% discount)
4. CRO (50% discount)
5. Pharma company (pilot pricing)

### Onboarding Process

1. **Kickoff Call** (Week 1)
   - Introduction
   - Use case discussion
   - Access credentials

2. **Training Session** (Week 1)
   - Platform walkthrough
   - API documentation
   - Best practices

3. **First Screening** (Week 2)
   - Guided molecule screening
   - Results interpretation
   - Q&A

4. **Weekly Check-ins** (Weeks 3-12)
   - Progress review
   - Feature requests
   - Bug reports

5. **Case Study** (Week 12)
   - Results documentation
   - Success metrics
   - Testimonial

---

## 📊 Phase 6: Public Launch (Week 13+)

### Launch Checklist

**Pre-Launch:**
- [x] Infrastructure deployed
- [x] API tested
- [x] Dashboard live
- [x] Payment integrated
- [x] Beta feedback incorporated
- [ ] Legal (Terms, Privacy Policy)
- [ ] Security audit
- [ ] Load testing
- [ ] Monitoring setup
- [ ] Support system ready

**Launch Day:**
- [ ] Press release
- [ ] Blog post
- [ ] Social media
- [ ] Email announcement
- [ ] Conference presentation

**Post-Launch:**
- [ ] Monitor metrics
- [ ] Support tickets
- [ ] Feature requests
- [ ] Bug fixes
- [ ] Marketing campaigns

---

## 📈 Monitoring & Analytics

### Datadog Setup

```python
from ddtrace import tracer
from ddtrace.contrib.fastapi import patch

patch()

@app.middleware("http")
async def add_datadog_metrics(request: Request, call_next):
    with tracer.trace("api.request"):
        response = await call_next(request)
        return response
```

### Key Metrics to Track

- **API Performance:** Response time, error rate
- **Usage:** Molecules/day, API calls/day
- **Business:** MRR, churn, NPS
- **Technical:** CPU, memory, queue length
- **Cost:** AWS spend, IBM Quantum credits

---

## 🔐 Security Measures

1. **API Security:**
   - JWT tokens
   - Rate limiting
   - Input validation

2. **Data Security:**
   - Encryption at rest (AWS KMS)
   - Encryption in transit (TLS 1.3)
   - Database encryption

3. **Compliance:**
   - GDPR compliance
   - HIPAA ready (optional)
   - SOC 2 audit (Year 2)

---

## 💰 Budget Summary

| Phase | Duration | Cost |
|-------|----------|------|
| Infrastructure Setup | 2 weeks | $10K |
| API Development | 2 weeks | $20K |
| Web Dashboard | 4 weeks | $40K |
| Payment Integration | 1 week | $5K |
| Beta Launch | 3 weeks | $15K |
| **TOTAL** | **12 weeks** | **$90K** |

**Ongoing Costs:**
- AWS: $500-3K/month (scales with usage)
- IBM Quantum: $5K/month
- Support tools: $500/month
- **Total:** $6K-8.5K/month

---

## ✅ Success Criteria

**Launch Success:**
- ✅ 5 beta partners onboarded
- ✅ 10+ paying customers (Month 3)
- ✅ $10K+ MRR (Month 6)
- ✅ < 1% error rate
- ✅ < 5% churn rate
- ✅ NPS > 50

**Ready for Scale:**
- 50+ customers
- $50K+ MRR
- 99.9% uptime
- Positive unit economics

---

*QPHAROS is ready to revolutionize drug discovery. Let's launch!* 🚀🧬⚛️
