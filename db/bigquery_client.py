"""
VEDA — BigQuery Client (Fixed)
Avoids the streaming buffer UPDATE issue by using INSERT-only pattern.
BigQuery does not allow UPDATE/DELETE on recently streamed rows.
Solution: always INSERT new rows, use ORDER BY + LIMIT 1 to get latest.
"""
from dotenv import load_dotenv
load_dotenv()
import uuid
import json
import traceback
from datetime import datetime
from typing import Optional

from google.cloud import bigquery
from utils.config import PROJECT_ID, BQ_DATASET


class BigQueryClient:

    def __init__(self):
        self.client  = bigquery.Client(project=PROJECT_ID)
        self.dataset = BQ_DATASET
        self._prefix = f"{PROJECT_ID}.{BQ_DATASET}"

    # ─────────────────────────────────────────────────────────────────────────
    # audit_jobs — INSERT only (no UPDATE to avoid streaming buffer error)
    # ─────────────────────────────────────────────────────────────────────────

    def create_job(self, job_id: str, request_data: dict, created_at: str):
        """Insert initial job record with PENDING status."""
        rows = [{
            "job_id":          job_id,
            "company_name":    request_data.get("company_name", ""),
            "github_repo_url": request_data.get("github_repo_url", ""),
            "industry":        request_data.get("industry", ""),
            "description":     request_data.get("description", ""),
            "status":          "PENDING",
            "message":         "Audit queued",
            "created_at":      self._now(),
            "updated_at":      self._now(),
            "completed_at":    None,
            "requested_by":    request_data.get("requested_by", ""),
        }]
        errors = self.client.insert_rows_json(f"{self._prefix}.audit_jobs", rows)
        if errors:
            print(f"[BigQuery] create_job errors: {errors}")

    def update_job_status(self, job_id: str, status: str, message: str):
        """
        INSERT a new status row instead of UPDATE.
        BigQuery streaming buffer does not support UPDATE on recently inserted rows.
        We get the latest status using ORDER BY updated_at DESC LIMIT 1.
        """
        rows = [{
            "job_id":       job_id,
            "company_name": "",
            "github_repo_url": "",
            "industry":     "",
            "description":  "",
            "status":       status,
            "message":      message,
            "created_at":   self._now(),
            "updated_at":   self._now(),
            "completed_at": self._now() if status in ("COMPLETED", "FAILED") else None,
            "requested_by": "",
        }]
        try:
            errors = self.client.insert_rows_json(f"{self._prefix}.audit_jobs", rows)
            if errors:
                print(f"[BigQuery] update_job_status errors: {errors}")
        except Exception as e:
            # Non-fatal — job will still run even if status update fails
            print(f"[BigQuery] update_job_status failed (non-fatal): {e}")

    def get_job(self, job_id: str) -> dict | None:
        query = f"""
            SELECT job_id, company_name, github_repo_url, industry,
                status, message, created_at, updated_at, completed_at
            FROM `{self._prefix}.audit_jobs`
            WHERE job_id = @job_id
            ORDER BY created_at DESC
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
            ]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        return dict(rows[0]) if rows else None

    def list_jobs(self, limit: int = 20) -> list:
        query = f"""
            SELECT job_id, company_name, status, created_at, updated_at
            FROM `{self._prefix}.audit_jobs`
            ORDER BY created_at DESC
            LIMIT {limit}
        """
        rows = self.client.query(query).result()
        return [dict(r) for r in rows]

    # ─────────────────────────────────────────────────────────────────────────
    # audit_reports
    # ─────────────────────────────────────────────────────────────────────────

    def save_report(self, job_id: str, report: dict):
        """Save the full due diligence report."""
        exec_summary = report.get("executive_summary", {})
        rows = [{
            "job_id":                 job_id,
            "company_name":           report.get("company_name", ""),
            "overall_risk_score":     float(report.get("overall_risk_score", 0)),
            "recommendation":         exec_summary.get("recommendation", ""),
            "overall_rating":         exec_summary.get("overall_rating", ""),
            "one_line_verdict":       exec_summary.get("one_line_verdict", ""),
            "executive_summary_text": exec_summary.get("executive_summary", ""),
            "report_json":            json.dumps(report),
            "pdf_generated":          False,
            "completed_at":           self._now(),
        }]
        errors = self.client.insert_rows_json(f"{self._prefix}.audit_reports", rows)
        if errors:
            print(f"[BigQuery] save_report errors: {errors}")
        else:
            self._save_risk_scores(job_id, report)

    def get_report(self, job_id: str) -> Optional[dict]:
        """Fetch the full report JSON."""
        query = f"""
            SELECT report_json
            FROM `{self._prefix}.audit_reports`
            WHERE job_id = @job_id
            ORDER BY completed_at DESC
            LIMIT 1
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
        ])
        rows = list(self.client.query(query, job_config=cfg).result())
        if not rows:
            return None
        return json.loads(rows[0]["report_json"])

    def mark_pdf_generated(self, job_id: str):
        """Non-critical — just log it."""
        print(f"[BigQuery] PDF generated for job {job_id}")

    # ─────────────────────────────────────────────────────────────────────────
    # risk_scores
    # ─────────────────────────────────────────────────────────────────────────

    def _save_risk_scores(self, job_id: str, report: dict):
        code   = report.get("code_audit", {})
        reg    = report.get("regulatory", {})
        market = report.get("market_forecast", {})
        exec_s = report.get("executive_summary", {})

        rows = [{
            "job_id":               job_id,
            "company_name":         report.get("company_name", ""),
            "industry":             report.get("industry", ""),
            "tech_debt_score":      float(code.get("tech_debt_score", 0)),
            "compliance_score":     float(reg.get("compliance_score", 0)),
            "market_fit_score":     float(market.get("market_fit_score", 0)),
            "overall_risk_score":   float(report.get("overall_risk_score", 0)),
            "security_flags_count": len(code.get("security_flags", [])),
            "red_flags_count":      len(reg.get("red_flags", [])),
            "recommendation":       exec_s.get("recommendation", ""),
            "scored_at":            self._now(),
        }]
        errors = self.client.insert_rows_json(f"{self._prefix}.risk_scores", rows)
        if errors:
            print(f"[BigQuery] risk_scores errors: {errors}")

    def get_all_risk_scores(self, limit: int = 50) -> list:
        query = f"""
            SELECT
                company_name, industry, tech_debt_score, compliance_score,
                market_fit_score, overall_risk_score, recommendation, scored_at
            FROM `{self._prefix}.risk_scores`
            ORDER BY scored_at DESC
            LIMIT {int(limit)}
        """
        rows = self.client.query(query).result()
        return [self._row_to_dict(r) for r in rows]

    # ─────────────────────────────────────────────────────────────────────────
    # agent_events
    # ─────────────────────────────────────────────────────────────────────────

    def log_agent_event(
        self,
        job_id: str,
        step: int,
        agent_name: str,
        status: str,
        message: str,
        progress_pct: int,
        event_data: dict = None,
    ):
        rows = [{
            "event_id":     str(uuid.uuid4()),
            "job_id":       job_id,
            "step":         step,
            "agent_name":   agent_name,
            "status":       status,
            "message":      message,
            "progress_pct": progress_pct,
            "event_data":   json.dumps(event_data or {}),
            "created_at":   self._now(),
        }]
        try:
            errors = self.client.insert_rows_json(f"{self._prefix}.agent_events", rows)
            if errors:
                print(f"[BigQuery] agent_events errors: {errors}")
        except Exception as e:
            print(f"[BigQuery] log_agent_event failed (non-fatal): {e}")

    def get_agent_events(self, job_id: str) -> list:
        query = f"""
            SELECT step, agent_name, status, message, progress_pct, created_at
            FROM `{self._prefix}.agent_events`
            WHERE job_id = @job_id
            ORDER BY created_at ASC
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
        ])
        try:
            rows = self.client.query(query, job_config=cfg).result()
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            print(f"[BigQuery] get_agent_events error: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # error_logs
    # ─────────────────────────────────────────────────────────────────────────

    def log_error(
        self,
        job_id: str,
        error: Exception = None,
        agent_name: str = "PrimaryAgent",
        traceback_str: str = "",
    ):
        rows = [{
            "log_id":        str(uuid.uuid4()),
            "job_id":        job_id,
            "agent_name":    agent_name,
            "error_type":    type(error).__name__ if error else "UnknownError",
            "error_message": str(error)[:500] if error else "",
            "traceback":     (traceback_str or traceback.format_exc())[:10000],
            "logged_at":     self._now(),
        }]
        try:
            self.client.insert_rows_json(f"{self._prefix}.error_logs", rows)
        except Exception as e:
            print(f"[BigQuery] log_error failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Analytics
    # ─────────────────────────────────────────────────────────────────────────

    def get_dashboard_stats(self) -> dict:
        query = f"""
            SELECT
                COUNT(DISTINCT job_id)                      AS total_audits,
                COUNTIF(status = 'COMPLETED')               AS completed_audits,
                COUNTIF(status = 'FAILED')                  AS failed_audits,
                COUNTIF(status IN ('PENDING','RUNNING'))    AS active_audits
            FROM (
                SELECT job_id, MAX(status) AS status
                FROM `{self._prefix}.audit_jobs`
                GROUP BY job_id
            )
        """
        rows = list(self.client.query(query).result())
        if not rows:
            return {}
        return self._row_to_dict(rows[0])

    def get_industry_breakdown(self) -> list:
        query = f"""
            SELECT
                industry,
                COUNT(*) AS audit_count,
                ROUND(AVG(overall_risk_score), 1) AS avg_risk_score
            FROM `{self._prefix}.risk_scores`
            GROUP BY industry
            ORDER BY audit_count DESC
            LIMIT 20
        """
        rows = self.client.query(query).result()
        return [self._row_to_dict(r) for r in rows]

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def _row_to_dict(self, row) -> dict:
        result = {}
        for key in row.keys():
            val = row[key]
            if hasattr(val, "isoformat"):
                result[key] = val.isoformat()
            else:
                result[key] = val
        return result