"""One-shot importer for migrating file-based PII into the SQLite corpus.

Phase A scope: deterministic parts (candidate, skills, certifications,
education, clarifications). LLM-assisted experience + bullet extraction
lands in `extract_experiences.py` as a separate module.
"""
