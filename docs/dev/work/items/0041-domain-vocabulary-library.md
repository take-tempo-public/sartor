```toml
schema = 1
id = 41
kind = "item"
title = "Domain-vocabulary library for Compose drafting"
status = "deferred"
decision_owner = "user"
blocked_on = "post-1.1.0 - owner scheduled this for 1.1.x investigation, not the Final March"
refs = ["docs/dev/RELEASE_ARC.md", "analyzer.py"]
summary = "Local lexicons (design, SWE, business, startup) so Compose drafting uses the JD domain's language and conventions."
```

Owner-captured 2026-08-03 during Final March planning: a library of domain
vocabularies and practices the Compose drafting calls can leverage so resumes use
the language of the JD's domain. Two hard constraints from the owner: no research
at compose time — (1) latency, (2) the product claim that the only thing leaving
the system is the LLM requests. So this is local, curated data shipped with or
imported into the product, consulted at prompt-assembly time.

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff
