# VEDA — Venture Evaluation & Due Diligence Agent

<div align="center">

**AI-Powered M&A Due Diligence Platform for Indian Startups**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-orange.svg)

</div>

---

## 🎯 Overview

**VEDA** (Venture Evaluation & Due Diligence Agent) is an enterprise-grade, multi-agent AI system designed to automate M&A due diligence for Indian startups. Built on Google Cloud's Vertex AI and powered by Gemini 2.5 Flash, VEDA analyzes technical debt, regulatory compliance, market potential, and competitive positioning to deliver board-ready acquisition recommendations in minutes.

### Key Features

- **🤖 Multi-Agent Architecture**: 6 specialized AI agents working in parallel
- **📊 Comprehensive Analysis**: Code quality, compliance, market forecasting, competitor intelligence
- **🔒 Enterprise Security**: Google OAuth 2.0, session management, role-based access
- **📈 Real-Time Progress**: WebSocket-based live updates during audit execution
- **📄 Automated Reporting**: PDF generation with executive summaries and risk scores
- **🇮🇳 India-Focused**: SEBI, RBI, IT Act, PDPB 2023, GST compliance checks
- **🎯 Deal Intelligence**: Sentiment analysis, investment scoring, startup similarity matching
- **📅 Workflow Automation**: Google Calendar integration, task management, meeting scheduling

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         VEDA Platform                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   FastAPI    │───▶│  Primary     │───▶│   BigQuery   │      │
│  │   REST API   │    │   Agent      │    │   Database   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                    │                                   │
│         │                    ▼                                   │
│         │         ┌─────────────────────┐                       │
│         │         │   6 Specialized     │                       │
│         │         │   Sub-Agents        │                       │
│         │         └─────────────────────┘                       │
│         │                    │                                   │
│         │         ┌──────────┼──────────┐                       │
│         │         │          │          │                       │
│         │    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐                 │
│         │    │ Code   │ │ Reg.   │ │ Market │                 │
│         │    │ Audit  │ │ Scout  │ │ Analyst│                 │
│         │    └────────┘ └────────┘ └────────┘                 │
│         │         │          │          │                       │
│         │    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐                 │
│         │    │ Exec   │ │ Comp.  │ │ News   │                 │
│         │    │Summary │ │ Intel  │ │Sentiment│                │
│         │    └────────┘ └────────┘ └────────┘                 │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   MCP        │───▶│   GitHub     │    │   Google     │     │
│  │   Server     │    │   API        │    │   Calendar   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Agent Workflow

1. **Code Auditor Agent**: Scans GitHub repositories for tech debt, security vulnerabilities, test coverage, CI/CD maturity
2. **Regulatory Scout Agent**: Validates compliance with Indian regulations (SEBI, RBI, IT Act, PDPB, GST)
3. **Market Analyst Agent**: Generates 3-year revenue forecasts (Bear/Base/Bull scenarios) and acquisition price ranges
4. **Executive Summary Agent**: Synthesizes findings into board-ready recommendations with risk ratings
5. **Competitor Intelligence Agent**: Analyzes competitive positioning and market differentiation
6. **News Sentiment Agent**: Performs sentiment analysis on company news and public perception

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Google Cloud Project** with Vertex AI API enabled
- **BigQuery Dataset** for data storage
- **GitHub Personal Access Token** (for repository scanning)
- **Google OAuth 2.0 Credentials** (for authentication)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/jackstealer/VEDA_123.git
cd VEDA_123
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

```bash
# Create .env file
cat > .env << EOF
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
BQ_DATASET=veda_ma_diligence

GITHUB_TOKEN=your-github-token
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
SESSION_SECRET=your-session-secret

OAUTH_REDIRECT_URI=http://localhost:8080/auth/callback
MCP_SERVER_URL=http://localhost:8001
EOF
```

4. **Set up Google Cloud credentials**

```bash
# Place your service account JSON in the project root
export GOOGLE_APPLICATION_CREDENTIALS=service_account.json
```

5. **Initialize BigQuery schema**

```bash
python db/setup_schema.py
```

6. **Run the application**

Terminal 1 - MCP Server:

```bash
uvicorn mcp_server.server:app --host 0.0.0.0 --port 8001
```

Terminal 2 - Main API:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

7. **Access the dashboard**

```
http://localhost:8080
```

---

## 📖 API Documentation

### Authentication

All endpoints (except `/login` and `/auth/*`) require Google OAuth 2.0 authentication.

**Login Flow:**

1. Navigate to `/login`
2. Click "Sign in with Google"
3. Authorize VEDA to access your Google account
4. Redirected to dashboard with session cookie

### Core Endpoints

#### Start Audit

```http
POST /audit
Content-Type: application/json
Authorization: Bearer <session-token>

{
  "company_name": "TechStartup Inc",
  "github_repo_url": "https://github.com/techstartup/main-repo",
  "industry": "saas",
  "description": "B2B SaaS platform for enterprise automation",
  "schedule_kickoff_meeting": true,
  "attendee_email": "investor@vc.com"
}
```

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "message": "VEDA audit started. Connect to WebSocket for live updates.",
  "created_at": "2026-05-07T10:30:00",
  "websocket_url": "/ws/550e8400-e29b-41d4-a716-446655440000"
}
```

#### Get Audit Status

```http
GET /status/{job_id}
```

#### Get Full Report

```http
GET /report/{job_id}
```

**Response Structure:**

```json
{
  "job_id": "...",
  "company_name": "TechStartup Inc",
  "overall_risk_score": 78.5,
  "code_audit": {
    "tech_debt_score": 72,
    "security_flags": [
      "Hardcoded secrets detected",
      "Missing input validation"
    ],
    "maintenance_health": "MODERATE",
    "bus_factor_risk": "HIGH"
  },
  "regulatory": {
    "compliance_score": 85,
    "red_flags": ["Missing PDPB consent forms"],
    "regulatory_deal_blocker": false
  },
  "market_forecast": {
    "market_fit_score": 80,
    "recommended_acquisition_price_range_inr_cr": "50-75 Cr"
  },
  "executive_summary": {
    "recommendation": "PROCEED_WITH_CONDITIONS",
    "overall_rating": "B+",
    "one_line_verdict": "Strong market position with moderate technical debt"
  }
}
```

#### Download PDF Report

```http
GET /report/{job_id}/pdf
```

#### WebSocket Live Updates

```javascript
const ws = new WebSocket(`ws://localhost:8080/ws/${jobId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Agent ${data.agent_name}: ${data.message}`);
};
```

### Deal Intelligence Endpoints

#### Parse Pitch Deck

```http
POST /pitch-deck/parse
Content-Type: multipart/form-data

file: <PDF file>
```

#### Analyze Sentiment

```http
POST /sentiment/analyze
Content-Type: application/json

{
  "text": "Company shows strong growth trajectory with innovative product"
}
```

#### Find Similar Startups

```http
POST /embeddings/similar
Content-Type: application/json

{
  "summary": "B2B SaaS platform for enterprise automation",
  "top_k": 3
}
```

#### Compute Investment Score

```http
POST /intelligence/score
Content-Type: application/json

{
  "tech_debt_score": 72,
  "compliance_score": 85,
  "market_fit_score": 80,
  "sentiment_text": "Positive market reception",
  "financial_signals": {
    "revenue_inr_lakhs": 500,
    "growth_rate_pct": 120
  }
}
```

---

## 🗄️ Database Schema

### BigQuery Tables

#### `audit_jobs`

Tracks audit execution status and metadata.

| Column          | Type      | Description                      |
| --------------- | --------- | -------------------------------- |
| job_id          | STRING    | Unique audit identifier          |
| company_name    | STRING    | Target company name              |
| github_repo_url | STRING    | Repository URL                   |
| industry        | STRING    | Industry sector                  |
| status          | STRING    | PENDING/RUNNING/COMPLETED/FAILED |
| created_at      | TIMESTAMP | Job creation time                |
| updated_at      | TIMESTAMP | Last status update               |

#### `audit_reports`

Stores complete audit reports with scores and recommendations.

| Column             | Type      | Description                            |
| ------------------ | --------- | -------------------------------------- |
| job_id             | STRING    | Links to audit_jobs                    |
| company_name       | STRING    | Target company                         |
| overall_risk_score | FLOAT     | Composite risk score (0-100)           |
| recommendation     | STRING    | PROCEED/PROCEED_WITH_CONDITIONS/REJECT |
| report_json        | JSON      | Full report data                       |
| completed_at       | TIMESTAMP | Report generation time                 |

#### `risk_scores`

Normalized risk metrics for analytics.

| Column             | Type   | Description                 |
| ------------------ | ------ | --------------------------- |
| job_id             | STRING | Audit identifier            |
| tech_debt_score    | FLOAT  | Code quality score          |
| compliance_score   | FLOAT  | Regulatory compliance score |
| market_fit_score   | FLOAT  | Market potential score      |
| overall_risk_score | FLOAT  | Weighted composite score    |

#### `agent_events`

Audit trail of agent execution steps.

| Column       | Type      | Description                |
| ------------ | --------- | -------------------------- |
| event_id     | STRING    | Unique event ID            |
| job_id       | STRING    | Audit identifier           |
| agent_name   | STRING    | Agent that generated event |
| status       | STRING    | RUNNING/DONE/FAILED        |
| progress_pct | INT       | Completion percentage      |
| created_at   | TIMESTAMP | Event timestamp            |

---

## 🔧 Configuration

### Environment Variables

| Variable                   | Required | Default               | Description                  |
| -------------------------- | -------- | --------------------- | ---------------------------- |
| `GCP_PROJECT_ID`           | ✅       | -                     | Google Cloud project ID      |
| `GCP_LOCATION`             | ✅       | us-central1           | Vertex AI region             |
| `BQ_DATASET`               | ✅       | veda_ma_diligence     | BigQuery dataset name        |
| `GITHUB_TOKEN`             | ✅       | -                     | GitHub PAT for API access    |
| `GOOGLE_CLIENT_ID`         | ✅       | -                     | OAuth 2.0 client ID          |
| `GOOGLE_CLIENT_SECRET`     | ✅       | -                     | OAuth 2.0 client secret      |
| `SESSION_SECRET`           | ✅       | -                     | Session encryption key       |
| `OAUTH_REDIRECT_URI`       | ✅       | -                     | OAuth callback URL           |
| `MCP_SERVER_URL`           | ❌       | http://localhost:8001 | MCP server endpoint          |
| `AGENT_TIMEOUT_CODE`       | ❌       | 120                   | Code audit timeout (seconds) |
| `AGENT_TIMEOUT_REGULATORY` | ❌       | 90                    | Regulatory audit timeout     |
| `AGENT_TIMEOUT_MARKET`     | ❌       | 180                   | Market analysis timeout      |

### Agent Timeouts

Configure per-agent execution timeouts to prevent hanging:

```python
# utils/config.py
AGENT_TIMEOUT_CODE       = 120  # Code Auditor
AGENT_TIMEOUT_REGULATORY = 90   # Regulatory Scout
AGENT_TIMEOUT_MARKET     = 180  # Market Analyst
AGENT_TIMEOUT_SUMMARY    = 60   # Executive Summary
```

---

## 🐳 Docker Deployment

### Build and Run

```bash
# Build main API container
docker build -t veda-api -f Dockerfile .

# Build MCP server container
docker build -t veda-mcp -f Dockerfile.mcp .

# Run with Docker Compose
docker-compose up -d
```

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  veda-api:
    image: veda-api
    ports:
      - "8080:8080"
    environment:
      - GCP_PROJECT_ID=${GCP_PROJECT_ID}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    volumes:
      - ./service_account.json:/app/service_account.json

  veda-mcp:
    image: veda-mcp
    ports:
      - "8001:8001"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
```

---

## 📊 Scoring Methodology

### Overall Risk Score Calculation

```
Overall Risk Score = (Tech Debt × 0.35) + (Compliance × 0.35) + (Market Fit × 0.30)
```

### Tech Debt Score (0-100)

**Factors:**

- Code quality and maintainability
- Security vulnerabilities
- Test coverage
- CI/CD maturity
- Documentation quality
- Dependency health

**Scoring:**

- 90-100: Excellent (A)
- 75-89: Good (B)
- 60-74: Moderate (C)
- 40-59: Poor (D)
- 0-39: Critical (F)

### Compliance Score (0-100)

**Indian Regulatory Frameworks:**

- SEBI Guidelines (Securities)
- RBI Cloud Guidelines (Banking/Fintech)
- IT Act Section 43A (Data Protection)
- PDPB 2023 (Privacy)
- GST Compliance (Tax)

**Red Flags:**

- Missing data protection policies
- Non-compliant payment processing
- Inadequate security controls
- Missing regulatory licenses

### Market Fit Score (0-100)

**Factors:**

- Total Addressable Market (TAM)
- Growth trajectory
- Competitive positioning
- Revenue model viability
- Customer acquisition metrics

**3-Year Forecast Scenarios:**

- **Bear Case**: Conservative growth (20% CAGR)
- **Base Case**: Expected growth (50% CAGR)
- **Bull Case**: Optimistic growth (100% CAGR)

### Investment Score (0-100)

**Weighted Formula:**

```
Investment Score =
  (Tech Debt × 0.25) +
  (Compliance × 0.25) +
  (Market Fit × 0.30) +
  (Sentiment × 0.10) +
  (Financial Signals × 0.10)
```

**Grades:**

- A (90-100): Strong Buy
- B (75-89): Buy
- C (60-74): Hold
- D (40-59): Caution
- F (0-39): Avoid

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=. --cov-report=html tests/

# Run E2E tests
pytest tests/test_e2e.py -v
```

### Test Database Connection

```bash
python db/test_connection.py
```

---

## 📁 Project Structure

```
VEDA_123/
├── agents/                      # AI agent implementations
│   ├── primary_agent.py         # Main orchestrator
│   ├── code_auditor.py          # GitHub code analysis
│   ├── regulatory_scout.py      # Compliance checking
│   ├── market_analyst.py        # Market forecasting
│   ├── executive_summary.py     # Report synthesis
│   ├── competitor_intelligence.py
│   ├── news_sentiment.py
│   └── schemas.py               # Pydantic models
├── api/                         # FastAPI application
│   ├── main.py                  # API routes
│   ├── auth.py                  # OAuth implementation
│   └── progress_manager.py      # WebSocket manager
├── db/                          # Database layer
│   ├── bigquery_client.py       # BigQuery operations
│   ├── setup_schema.py          # Schema initialization
│   └── test_connection.py
├── mcp_server/                  # Model Context Protocol server
│   └── server.py                # GitHub/Calendar tools
├── utils/                       # Utility modules
│   ├── config.py                # Configuration management
│   ├── cloud_logger.py          # Google Cloud Logging
│   ├── embeddings_engine.py     # Vertex AI embeddings
│   ├── sentiment_engine.py      # NLP sentiment analysis
│   ├── investment_scorer.py     # Investment scoring logic
│   ├── pdf_generator.py         # Report PDF generation
│   ├── pitch_deck_parser.py     # PDF pitch deck extraction
│   └── vertex_helper.py         # Vertex AI utilities
├── static/                      # Frontend assets
│   ├── index.html               # Dashboard UI
│   └── login.html               # Login page
├── regulatory_docs/             # Compliance reference docs
│   ├── sebi_guidelines.txt
│   ├── rbi_cloud_guidelines.txt
│   ├── it_act_43a.txt
│   ├── pdpb_2023.txt
│   └── gst_compliance.txt
├── tests/                       # Test suite
│   └── test_e2e.py
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Main API container
├── Dockerfile.mcp               # MCP server container
├── .gitignore
└── README.md
```

---

## 🔐 Security

### Authentication & Authorization

- **Google OAuth 2.0**: Industry-standard authentication
- **Session Management**: Secure HTTP-only cookies with 8-hour expiry
- **Token Refresh**: Automatic OAuth token refresh for long-running audits
- **CORS Protection**: Configurable origin whitelist

### Data Protection

- **Encryption at Rest**: BigQuery automatic encryption
- **Encryption in Transit**: TLS 1.3 for all API communication
- **Secret Management**: Google Cloud Secret Manager integration
- **Audit Logging**: Complete audit trail in BigQuery

### Best Practices

- Never commit `credentials.json` or `service_account.json`
- Rotate OAuth credentials every 90 days
- Use least-privilege IAM roles for service accounts
- Enable VPC Service Controls for production deployments

---

## 🌐 Deployment

### Google Cloud Run

```bash
# Build and push container
gcloud builds submit --tag gcr.io/${PROJECT_ID}/veda-api

# Deploy to Cloud Run
gcloud run deploy veda-api \
  --image gcr.io/${PROJECT_ID}/veda-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=${PROJECT_ID}
```

### Environment Setup

1. **Enable APIs**

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  secretmanager.googleapis.com \
  cloudlogging.googleapis.com
```

2. **Create Service Account**

```bash
gcloud iam service-accounts create veda-sa \
  --display-name="VEDA Service Account"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:veda-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

3. **Store Secrets**

```bash
echo -n "your-github-token" | \
  gcloud secrets create GITHUB-TOKEN --data-file=-

echo -n "your-oauth-client-id" | \
  gcloud secrets create GOOGLE-CLIENT-ID --data-file=-
```

---

## 📈 Performance

### Benchmarks

| Metric                  | Value              |
| ----------------------- | ------------------ |
| Average Audit Duration  | 3-5 minutes        |
| Concurrent Audits       | 10+ (configurable) |
| API Response Time (p95) | <200ms             |
| WebSocket Latency       | <50ms              |
| BigQuery Query Time     | <1s                |

### Optimization Tips

- **Parallel Agent Execution**: Agents run concurrently where possible
- **Streaming Inserts**: BigQuery streaming for real-time updates
- **Connection Pooling**: Reuse HTTP clients for external APIs
- **Caching**: Cache GitHub API responses for 5 minutes
- **Async I/O**: FastAPI async endpoints for non-blocking operations

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all function signatures
- Add docstrings for public functions
- Write tests for new features

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Cloud**: Vertex AI, BigQuery, Secret Manager
- **FastAPI**: High-performance web framework
- **Gemini 2.5 Flash**: Generative AI model
- **GitHub API**: Repository analysis
- **Google Calendar API**: Workflow automation

---

## 📞 Support

For questions, issues, or feature requests:

- **GitHub Issues**: [https://github.com/jackstealer/VEDA_123/issues](https://github.com/jackstealer/VEDA_123/issues)
- **GitHub Repository**: [https://github.com/jackstealer/VEDA_123](https://github.com/jackstealer/VEDA_123)

---

## 🗺️ Roadmap

### Q2 2026

- [ ] Multi-language support (Hindi, Tamil, Bengali)
- [ ] Integration with Indian stock exchanges (NSE/BSE)
- [ ] Advanced competitor benchmarking
- [ ] Custom compliance framework builder

### Q3 2026

- [ ] Mobile app (iOS/Android)
- [ ] Slack/Teams integration
- [ ] Automated valuation models
- [ ] Deal room collaboration features

### Q4 2026

- [ ] AI-powered negotiation assistant
- [ ] Post-merger integration tracking
- [ ] Portfolio company monitoring
- [ ] Predictive M&A opportunity scoring

---

<div align="center">

**Built with ❤️ for the Indian M&A ecosystem**

[GitHub Repository](https://github.com/jackstealer/VEDA_123)

</div>
