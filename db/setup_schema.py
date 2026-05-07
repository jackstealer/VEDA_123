"""
VEDA — BigQuery Schema Setup
Run this ONCE in Google Cloud Shell to create the dataset and all 5 tables.

Usage:
    python db/setup_schema.py

Make sure GCP_PROJECT_ID is set in your .env or environment before running.
"""

import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
DATASET_ID = os.getenv("BQ_DATASET", "veda_ma_diligence")
LOCATION   = os.getenv("GCP_LOCATION", "US")

client = bigquery.Client(project=PROJECT_ID)

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Create Dataset
# ─────────────────────────────────────────────────────────────────────────────

def create_dataset():
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = LOCATION
    dataset_ref.description = "VEDA — Venture Evaluation & Due Diligence Agent"

    try:
        dataset = client.create_dataset(dataset_ref, exists_ok=True)
        print(f"✅ Dataset '{DATASET_ID}' is ready in {LOCATION}")
        return dataset
    except Exception as e:
        print(f"❌ Failed to create dataset: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Table Schemas
# ─────────────────────────────────────────────────────────────────────────────

TABLES = {

    # ── Table 1: audit_jobs ──────────────────────────────────────────────────
    # Tracks every audit job from PENDING → RUNNING → COMPLETED / FAILED
    "audit_jobs": [
        bigquery.SchemaField("job_id",          "STRING",    mode="REQUIRED",   description="Unique UUID for each audit"),
        bigquery.SchemaField("company_name",     "STRING",    mode="NULLABLE",   description="Target company being audited"),
        bigquery.SchemaField("github_repo_url",  "STRING",    mode="NULLABLE",   description="GitHub repo URL of target"),
        bigquery.SchemaField("industry",         "STRING",    mode="NULLABLE",   description="Industry sector e.g. fintech, saas"),
        bigquery.SchemaField("description",      "STRING",    mode="NULLABLE",   description="Short company description"),
        bigquery.SchemaField("status",           "STRING",    mode="NULLABLE",   description="PENDING | RUNNING | COMPLETED | FAILED"),
        bigquery.SchemaField("message",          "STRING",    mode="NULLABLE",   description="Latest status message from agent"),
        bigquery.SchemaField("created_at",       "TIMESTAMP", mode="NULLABLE",   description="When audit was submitted"),
        bigquery.SchemaField("updated_at",       "TIMESTAMP", mode="NULLABLE",   description="Last status update time"),
        bigquery.SchemaField("completed_at",     "TIMESTAMP", mode="NULLABLE",   description="When audit finished"),
        bigquery.SchemaField("requested_by",     "STRING",    mode="NULLABLE",   description="Email or user ID of requester"),
    ],

    # ── Table 2: audit_reports ───────────────────────────────────────────────
    # Stores the full JSON report once COMPLETED
    "audit_reports": [
        bigquery.SchemaField("job_id",               "STRING",  mode="REQUIRED",  description="Links to audit_jobs.job_id"),
        bigquery.SchemaField("company_name",          "STRING",  mode="NULLABLE",  description="Target company name"),
        bigquery.SchemaField("overall_risk_score",    "FLOAT",   mode="NULLABLE",  description="Weighted risk score 0-100"),
        bigquery.SchemaField("recommendation",        "STRING",  mode="NULLABLE",  description="PROCEED | PROCEED WITH CONDITIONS | DO NOT PROCEED"),
        bigquery.SchemaField("overall_rating",        "STRING",  mode="NULLABLE",  description="STRONG BUY | BUY | HOLD | AVOID"),
        bigquery.SchemaField("one_line_verdict",      "STRING",  mode="NULLABLE",  description="Single sentence verdict"),
        bigquery.SchemaField("executive_summary_text","STRING",  mode="NULLABLE",  description="Full boardroom summary paragraph"),
        bigquery.SchemaField("report_json",           "STRING",  mode="NULLABLE",  description="Complete report as JSON string"),
        bigquery.SchemaField("pdf_generated",         "BOOL",    mode="NULLABLE",  description="Whether PDF was generated"),
        bigquery.SchemaField("completed_at",          "TIMESTAMP",mode="NULLABLE", description="Report generation timestamp"),
    ],

    # ── Table 3: risk_scores ─────────────────────────────────────────────────
    # Stores individual scores per agent for analytics & dashboards
    "risk_scores": [
        bigquery.SchemaField("job_id",              "STRING",  mode="REQUIRED",  description="Links to audit_jobs.job_id"),
        bigquery.SchemaField("company_name",         "STRING",  mode="NULLABLE",  description="Target company name"),
        bigquery.SchemaField("industry",             "STRING",  mode="NULLABLE",  description="Industry sector"),
        bigquery.SchemaField("tech_debt_score",      "FLOAT",   mode="NULLABLE",  description="Code quality score 0-100 from CodeAuditor"),
        bigquery.SchemaField("compliance_score",     "FLOAT",   mode="NULLABLE",  description="Regulatory compliance score 0-100"),
        bigquery.SchemaField("market_fit_score",     "FLOAT",   mode="NULLABLE",  description="Composite market fit score 0-100"),
        bigquery.SchemaField("overall_risk_score",   "FLOAT",   mode="NULLABLE",  description="Final weighted risk score 0-100"),
        bigquery.SchemaField("security_flags_count", "INTEGER", mode="NULLABLE",  description="Number of security issues found"),
        bigquery.SchemaField("red_flags_count",      "INTEGER", mode="NULLABLE",  description="Number of regulatory red flags"),
        bigquery.SchemaField("recommendation",       "STRING",  mode="NULLABLE",  description="Final recommendation"),
        bigquery.SchemaField("scored_at",            "TIMESTAMP",mode="NULLABLE", description="When scores were computed"),
    ],

    # ── Table 4: agent_events ────────────────────────────────────────────────
    # Logs every WebSocket progress event for audit trail & debugging
    "agent_events": [
        bigquery.SchemaField("event_id",     "STRING",    mode="REQUIRED",  description="Unique event ID"),
        bigquery.SchemaField("job_id",       "STRING",    mode="NULLABLE",  description="Links to audit_jobs.job_id"),
        bigquery.SchemaField("step",         "INTEGER",   mode="NULLABLE",  description="Step number 1-4"),
        bigquery.SchemaField("agent_name",   "STRING",    mode="NULLABLE",  description="Which sub-agent fired this event"),
        bigquery.SchemaField("status",       "STRING",    mode="NULLABLE",  description="RUNNING | DONE | FAILED"),
        bigquery.SchemaField("message",      "STRING",    mode="NULLABLE",  description="Human-readable event message"),
        bigquery.SchemaField("progress_pct", "INTEGER",   mode="NULLABLE",  description="Progress percentage 0-100"),
        bigquery.SchemaField("event_data",   "STRING",    mode="NULLABLE",  description="JSON payload from agent"),
        bigquery.SchemaField("created_at",   "TIMESTAMP", mode="NULLABLE",  description="Event timestamp"),
    ],

    # ── Table 5: error_logs ──────────────────────────────────────────────────
    # Full error traces for debugging failed audits
    "error_logs": [
        bigquery.SchemaField("log_id",       "STRING",    mode="REQUIRED",  description="Unique log ID"),
        bigquery.SchemaField("job_id",       "STRING",    mode="NULLABLE",  description="Links to audit_jobs.job_id"),
        bigquery.SchemaField("agent_name",   "STRING",    mode="NULLABLE",  description="Which agent failed"),
        bigquery.SchemaField("error_type",   "STRING",    mode="NULLABLE",  description="Exception class name"),
        bigquery.SchemaField("error_message","STRING",    mode="NULLABLE",  description="Short error message"),
        bigquery.SchemaField("traceback",    "STRING",    mode="NULLABLE",  description="Full Python traceback (max 10000 chars)"),
        bigquery.SchemaField("logged_at",    "TIMESTAMP", mode="NULLABLE",  description="When error was logged"),
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Create all tables
# ─────────────────────────────────────────────────────────────────────────────

def create_tables():
    for table_name, schema in TABLES.items():
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
        table = bigquery.Table(table_ref, schema=schema)

        try:
            client.create_table(table, exists_ok=True)
            field_count = len(schema)
            print(f"  ✅ Table '{table_name}' ready  ({field_count} fields)")
        except Exception as e:
            print(f"  ❌ Failed to create '{table_name}': {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Verify everything was created
# ─────────────────────────────────────────────────────────────────────────────

def verify():
    print("\n── Verifying tables in BigQuery ──")
    dataset = client.get_dataset(f"{PROJECT_ID}.{DATASET_ID}")
    tables = list(client.list_tables(dataset))
    for t in tables:
        print(f"  ✓ {t.table_id}")
    print(f"\n  Total: {len(tables)} tables in dataset '{DATASET_ID}'")


# ─────────────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n🔷 VEDA — BigQuery Schema Setup")
    print(f"   Project : {PROJECT_ID}")
    print(f"   Dataset : {DATASET_ID}")
    print(f"   Location: {LOCATION}\n")

    print("── Creating dataset ──")
    create_dataset()

    print("\n── Creating tables ──")
    create_tables()

    verify()

    print("\n✅ Done! VEDA database is ready.")
    print(f"   View in console: https://console.cloud.google.com/bigquery?project={PROJECT_ID}")