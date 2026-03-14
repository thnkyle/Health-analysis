import json
import os
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

from models import DataType, HealthRecord

ANTHROPIC_API_KEY = os.environ.get("HEALTH_AI_API_KEY", "")
MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-6")


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _format_records_for_prompt(records: list[HealthRecord]) -> str:
    """Format health records into a concise text representation for Claude."""
    if not records:
        return "No health records available."

    grouped: dict[str, list[dict]] = {}
    for r in records:
        dt = r.data_type.value if isinstance(r.data_type, DataType) else str(r.data_type)
        recorded = r.recorded_at if isinstance(r.recorded_at, datetime) else datetime.fromisoformat(str(r.recorded_at))
        grouped.setdefault(dt, []).append({
            "value": r.value,
            "unit": r.unit,
            "recorded_at": recorded.isoformat(),
        })

    lines = []
    for dt, entries in sorted(grouped.items()):
        lines.append(f"\n## {dt} ({len(entries)} records)")
        for e in entries[-50:]:  # limit to last 50 per type to manage token usage
            lines.append(f"  {e['recorded_at']}: {e['value']} {e['unit']}")
        if len(entries) > 50:
            lines.append(f"  ... ({len(entries) - 50} earlier records omitted)")

    return "\n".join(lines)


def analyze_health_ai(
    db: Session,
    user_id: str,
    data_type: DataType | None = None,
) -> dict:
    """Use Claude to analyze health data and provide insights."""
    query = db.query(HealthRecord).filter(HealthRecord.user_id == user_id)
    if data_type:
        query = query.filter(HealthRecord.data_type == data_type)

    records = query.order_by(HealthRecord.recorded_at).all()

    if not records:
        return {
            "summary": "No health data available for analysis.",
            "insights": [],
            "recommendations": [],
            "risk_factors": [],
        }

    formatted_data = _format_records_for_prompt(records)

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=(
            "You are a health data analyst AI. Analyze the provided health metrics "
            "and return a JSON object with these fields:\n"
            '- "summary": A 2-3 sentence overview of the user\'s health data.\n'
            '- "insights": An array of strings, each a specific observation about '
            "patterns, trends, or notable data points.\n"
            '- "recommendations": An array of strings with actionable health suggestions '
            "based on the data.\n"
            '- "risk_factors": An array of strings identifying any concerning patterns '
            "or values that may need attention.\n\n"
            "Be specific and reference actual values from the data. "
            "Do NOT provide medical diagnoses. Frame recommendations as general wellness advice. "
            "Return ONLY valid JSON, no markdown fences."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Analyze the following health data:\n{formatted_data}",
            }
        ],
    )

    text = next((b.text for b in response.content if b.type == "text"), "{}")

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {
            "summary": text,
            "insights": [],
            "recommendations": [],
            "risk_factors": [],
        }

    # Ensure all expected fields exist
    for field in ("summary", "insights", "recommendations", "risk_factors"):
        if field not in result:
            result[field] = [] if field != "summary" else "Analysis complete."

    return result


def detect_anomalies_ai(
    db: Session,
    user_id: str,
    data_type: DataType | None = None,
) -> dict:
    """Use Claude to detect anomalies in health data with contextual reasoning."""
    query = db.query(HealthRecord).filter(HealthRecord.user_id == user_id)
    if data_type:
        query = query.filter(HealthRecord.data_type == data_type)

    records = query.order_by(HealthRecord.recorded_at).all()

    if len(records) < 3:
        return {
            "anomalies": [],
            "analysis": "Not enough data points for anomaly detection (minimum 3 required).",
            "correlations": [],
            "total": 0,
        }

    formatted_data = _format_records_for_prompt(records)

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=(
            "You are a health data anomaly detection AI. Analyze the provided health "
            "metrics and identify anomalous values. Consider:\n"
            "- Statistical outliers (values far from the mean)\n"
            "- Contextual anomalies (normal values at unusual times or patterns)\n"
            "- Trend breaks (sudden changes in established patterns)\n"
            "- Cross-metric correlations (e.g., high heart rate with low sleep)\n\n"
            "Return a JSON object with:\n"
            '- "anomalies": An array of objects, each with:\n'
            '  - "data_type": The metric type\n'
            '  - "value": The anomalous value\n'
            '  - "recorded_at": The timestamp\n'
            '  - "severity": "low", "medium", or "high"\n'
            '  - "reason": Why this is anomalous (reference context and patterns)\n'
            '- "analysis": A brief overall assessment of data quality and patterns.\n'
            '- "correlations": An array of strings describing any cross-metric patterns found.\n\n'
            "Return ONLY valid JSON, no markdown fences."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Detect anomalies in this health data:\n{formatted_data}",
            }
        ],
    )

    text = next((b.text for b in response.content if b.type == "text"), "{}")

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {
            "anomalies": [],
            "analysis": text,
            "correlations": [],
        }

    # Ensure expected fields
    result.setdefault("anomalies", [])
    result.setdefault("analysis", "Analysis complete.")
    result.setdefault("correlations", [])
    result["total"] = len(result["anomalies"])

    return result
