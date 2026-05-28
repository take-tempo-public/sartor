"""Dashboard blueprint — observability for the callback. LLM pipeline.

Reads logs/llm_calls.jsonl (per-call telemetry from analyzer._call_llm) and
evals/results/*.jsonl (per-rubric verdicts from evals/runner.py), renders two
filterable HTML tables at /_dashboard. Localhost-only.
"""

from .routes import dashboard_bp

__all__ = ["dashboard_bp"]
