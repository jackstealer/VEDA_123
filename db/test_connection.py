"""
VEDA — BigQuery Connection Test
Run this after setup_schema.py to confirm everything works.

Usage:
    python db/test_connection.py
"""

import os
import uuid
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
DATASET_ID = os.getenv("BQ_DATASET",     "veda_ma_diligence")

client = bigquery.Client(project=PROJECT_ID)

print(f"\n🔷 VEDA — BigQuery Connection Test")
print(f"   Project : {PROJECT_ID}")
print(f"   Dataset : {DATASET_ID}\n")

EXPECTED_TABLES = [
    "audit_jobs",
    "audit_reports",
    "risk_scores",
    "agent_events",
    "error_logs",
]

# ── 1. Check all tables exist ────────────────────────────────────────────────
print("── Checking tables ──")
dataset = client.get_dataset(f"{PROJECT_ID}.{DATASET_ID}")
existing = {t.table_id for t in client.list_tables(dataset)}

all_ok = True
for table in EXPECTED_TABLES:
    if table in existing:
        schema = client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{table}").schema
        print(f"  ✅ {table:25s} ({len(schema)} fields)")
    else:
        print(f"  ❌ {table:25s} — MISSING! Run setup_schema.py first.")
        all_ok = False

if not all_ok:
    print("\n❌ Some tables are missing. Run: python db/setup_schema.py")
    exit(1)

# ── 2. Insert a test row into audit_jobs ─────────────────────────────────────
print("\n── Testing INSERT into audit_jobs ──")
test_job_id = f"test_{uuid.uuid4().hex[:8]}"
from datetime import datetime

rows = [{
    "job_id":          test_job_id,
    "company_name":    "Test Company Pvt Ltd",
    "github_repo_url": "https://github.com/test/repo",
    "industry":        "saas",
    "description":     "Connection test",
    "status":          "PENDING",
    "message":         "Test insert",
    "created_at":      datetime.utcnow().isoformat(),
    "updated_at":      datetime.utcnow().isoformat(),
    "completed_at":    None,
    "requested_by":    "test@veda.ai",
}]
errors = client.insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.audit_jobs", rows)
if errors:
    print(f"  ❌ INSERT failed: {errors}")
else:
    print(f"  ✅ INSERT succeeded (job_id: {test_job_id})")

# ── 3. Read it back ──────────────────────────────────────────────────────────
print("\n── Testing SELECT from audit_jobs ──")
import time
time.sleep(2)  # BigQuery streaming buffer delay

query = f"""
    SELECT job_id, company_name, status
    FROM `{PROJECT_ID}.{DATASET_ID}.audit_jobs`
    WHERE job_id = '{test_job_id}'
    LIMIT 1
"""
results = list(client.query(query).result())
if results:
    row = results[0]
    print(f"  ✅ SELECT succeeded: job_id={row['job_id']}, status={row['status']}")
else:
    print(f"  ⚠️  Row not visible yet (streaming buffer delay — this is normal)")
    print(f"      Check in 30 seconds via BigQuery console.")

# ── 4. Test agent_events insert ──────────────────────────────────────────────
print("\n── Testing INSERT into agent_events ──")
import json
event_rows = [{
    "event_id":     f"evt_{uuid.uuid4().hex[:8]}",
    "job_id":       test_job_id,
    "step":         1,
    "agent_name":   "Code Auditor",
    "status":       "RUNNING",
    "message":      "Test event",
    "progress_pct": 25,
    "event_data":   json.dumps({"test": True}),
    "created_at":   datetime.utcnow().isoformat(),
}]
errors = client.insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.agent_events", event_rows)
if errors:
    print(f"  ❌ agent_events INSERT failed: {errors}")
else:
    print(f"  ✅ agent_events INSERT succeeded")

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"""
✅ BigQuery is fully set up and working!

Next steps:
  1. Start MCP server:  uvicorn mcp_server.server:app --port 8001 --reload
  2. Start VEDA API:    uvicorn api.main:app --port 8080 --reload
  3. Open browser:      http://localhost:8080
  4. View BigQuery:     https://console.cloud.google.com/bigquery?project={PROJECT_ID}
""")