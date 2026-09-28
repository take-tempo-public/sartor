```toml
schema = 1
id = 118
kind = "item"
title = "error_message redaction misses quoted-key header forms and Basic auth credentials"
status = "open"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery"]
refs = [
  "analyzer.py:598-624",
  "tests/test_llm_call_error_capture.py",
  "SECURITY.md",
]
summary = "_HEADER_VALUE_PATTERN skips {'x-api-key': ...} / {\"authorization\": ...} and masks only the word 'Basic'."
```

**Observed (epic refuter R1-3; reproduced at epic close):**

```
$ python -c "from analyzer import _redact_error_message as r; ..."
{'x-api-key': 'abc123secret'}                     -> unchanged
{"authorization": "Bearer tok999secret"}          -> unchanged
Authorization: Basic dXNlcjpwYXNz                 -> Authorization: *** dXNlcjpwYXNz
```

`_HEADER_VALUE_PATTERN` requires `key\s*[:=]` with no quote between them, so a
dict/JSON repr of headers slips through, and `(?:bearer\s+)?` only swallows a Bearer
prefix, so for Basic auth the scheme word is masked and the credential kept. `sk-ant-…`
keys are always masked (separate pattern), which bounds the Anthropic-key exposure; this
gap is for other credentials a server or proxy might echo. `SECURITY.md` now states the
masking is pattern-based.

**Suggested shape:** allow optional quotes around the key and between `:`/`=` and the
value, and mask any auth scheme plus its token (`(?:bearer|basic|token)\s+\S+`); one
test per form in `TestRedactErrorMessage`.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)
