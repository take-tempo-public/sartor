```toml
schema = 1
id = 192
kind = "item"
title = "The committed corpus seed uses area / study_type for educations; the importer reads field, so the discipline is dropped"
status = "watching"
decision_owner = "agent"
branches = ["feat/eval-dataset-format"]
refs = [
  "evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json",
  "evals/seed_import.py",
  "scripts/export_corpus_seed.py",
  "docs/dev/blast-radius/eval-dataset-format.md",
]
summary = "The committed corpus seed's educations use area/study_type; the importer reads field, so the discipline is lost."
```

Found while designing the golden set's seed round trip (item 183, step 3a), and then checked directly on 2026-10-22:

- `evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json` has education keys `area`, `degree`, `display_order`, `end_date`, `id`, `institution`, `is_active`, `start_date`, `study_type`.
- `evals/seed_import.py:280` reads `field`, and `scripts/export_corpus_seed.py:258` writes `field`. So importing this seed leaves `Education.field` empty: the discipline ("Computer Science" in this file) is silently dropped. `study_type` is read by nothing.
- The importer does not warn about a key it does not read.

Not fixed on that branch: the file is under `evals/fixtures/synthetic/`, which step 3b (item 191) retires, and it is the input of `evals/corpus_drafting_probe.py`. The golden renderer writes `field`, and `tests/test_golden_set.py::TestSeed` imports each rendered seed and exports it back, which would expose any key the importer does not read.

Candidate fixes: rename the two keys in the file; or make `validate_seed` / `import_seed` refuse or log an unknown education key (the same check would cover every entity). Decide when 3b touches the file or the importer. Watching, not open: nothing breaks today, because no eval reads the discipline.

## Updates

### 2026-10-22 -- filed during feat/eval-dataset-format
