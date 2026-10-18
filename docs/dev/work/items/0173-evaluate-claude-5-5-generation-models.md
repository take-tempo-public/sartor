```toml
schema = 1
id = 173
kind = "item"
title = "Evaluate the Claude 5.5 generation (Sonnet, Haiku, Opus) against the models the product and its subagents pin"
status = "closed"
decision_owner = "agent"
resolution = "2026-10-17: absorbed into item 137 by the owner's decision. The 5.5 candidate evaluation itself was NOT run; only its free first step was (results in this file's Updates). 137 carries the scope, the 17 proposals and the findings."
closure_exception = "Owner (amodal1), 2026-10-17, in chat: '137 absorbs 173; authorize first step'. A merge of a duplicate item, not a completed evaluation; no falsifiable artifact exists because the work it describes is still open under item 137."
branches = ["docs/model-55-eval-item"]
refs = [
  "docs/dev/work/items/0137-review-models-and-settings-for-performance-and-cost.md",
  "docs/dev/work/items/0174-model-pricing-disagrees-with-pricing-page.md",
  "analyzer.py:1042-1043",
  "analyzer.py:1573-1595",
  "hardening.py:439-465",
  "hardening.py:1710-1727",
  "evals/runner.py:112-117",
  "promptfooconfig.yaml:10",
  "promptfooconfig.yaml:17",
  "agents/",
  "CLAUDE.md",
  "CHANGELOG.md:5468",
  "scripts/enforcement/blast_radius.py:199-204",
]
summary = "Absorbed into item 137 (owner, 2026-10-17). No 5.5 A/B was run; the free first step was, and found real issues."
```

**Filed 2026-10-17 from the owner's question in a read-only session:** "have we evaluated updates to the
opus, sonnet, and haiku models we use (all in the 5.5 generation)?" **The answer is no.** Nothing in the
repo evaluates, prices, or even names a 5.5 model as a product or subagent candidate. This item is the
tracked home for that evaluation; the owner asked that it include the entire list of proposals made when
the question was answered (below, "Proposals", kept as made, then the filing session's additions).

**Relationship to item 137.** Item 137 ("Review current Claude models and call settings for performance
and cost", filed 2026-10-01, `open`, never started) already asks whether the pinned models and call
settings are the best fit. **The session that answered the owner's question did not find 137 and said
nothing about it; this item was filed without checking for it first, and 137 was found afterwards.**
They overlap: 137 is the broad review (routing per call kind, thinking-off, cache hit rate, output
limits, subagent pins); this item is the specific candidate list (the 5.5 generation) that review would
test. Whether 137 absorbs this one or the two stay separate is the owner's call; the choice is recorded
under "Open question". 137's `refs` cite `analyzer.py:850-851` and `:827-831`; those lines have moved
(the constants are now at `analyzer.py:1042-1043`, the thinking-off code at `:1573-1595`).

## What was observed

Source: this session's own reads and greps on 2026-10-17 at `main` `e490683`. Each is a fact about the
repo at that commit, not a claim about the API.

- **The product's pins.** `analyzer.py:1042` `SONNET_MODEL = "claude-sonnet-5"`; `analyzer.py:1043`
  `HAIKU_MODEL = "claude-haiku-4-5-20251001"  # still the latest Haiku — no Haiku 5`. A grep for
  `OPUS_MODEL` over `*.py` found nothing: **the product has no Opus constant and makes no Opus call.**
- **Call-site spread.** In `analyzer.py` the grep shows 13 `model=HAIKU_MODEL` sites (the first at
  `:1967`, the last at `:4625`) and 4 explicit `model=SONNET_MODEL` sites (`:4736`, `:4869`, `:5083`,
  `:5256`); every other Sonnet call takes `_call_llm`'s default (`effective_model = model or
  SONNET_MODEL`, `:1542`). **The default-path Sonnet sites were not counted.** `onboarding/extract_experiences.py:29`
  imports `HAIKU_MODEL` and calls with it at `:174`. The per-call-kind routing the evaluation must cover
  is in `docs/dev/architecture.md` §"LLM routing + cost"; it was not re-derived here.
- **Thinking is scoped by equality.** `analyzer.py:1594-1595`: `if effective_model == SONNET_MODEL:
  stream_kwargs["thinking"] = {"type": "disabled"}`. The Haiku path sends no `thinking` argument at all.
  The comment block at `:1573-1580` records why: Sonnet 5 turns adaptive thinking on when `thinking` is
  omitted, which spends the 8192-token `MAX_TOKENS` budget and can truncate the JSON payload.
- **An unpriced model costs $0.00.** `hardening.py:1710-1727` `compute_call_cost` returns `0.0` for a
  model with no `MODEL_PRICING` key and logs a warning only. `MODEL_PRICING` (`hardening.py:446-465`)
  has three keys: `claude-sonnet-5`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`. Its comment says
  "pricing as of 2026-07-05". So a model swap with no pricing key makes every telemetry-derived spend
  figure read low or zero, **including the spend caps the 2026-10-17 A/B (item 140b) enforced from a
  telemetry window**.
- **The eval judge is also Haiku 4.5.** `evals/runner.py:112-117`: `MODEL_SNAPSHOTS = {"sonnet":
  "claude-sonnet-5", "haiku_judge": "claude-haiku-4-5-20251001"}` and `JUDGE_MODEL =
  "claude-haiku-4-5-20251001"`. `evals/results/baseline_v1.json` was captured on the older models
  (`reference-model-upgrade-playbook` records the smoke gate exiting 2 on a regression over 0.5 against
  it). Moving the generator and the judge in the same run would confound the comparison.
- **Other hard-coded strings.** `promptfooconfig.yaml:10` and `:17` name `claude-sonnet-5`
  (`anthropic:claude-sonnet-5`). A `git grep` of the literal strings found them in 13 files: `analyzer.py`,
  `evals/runner.py`, `hardening.py`, `promptfooconfig.yaml`, `scripts/verify_doc_template.py`, and eight
  test files (`tests/test_dashboard_copy.py`, `tests/test_hardening.py`, `tests/test_n1_pipeline.py`,
  `tests/test_verify_doc_template.py`, and four under `tests/ux/`). Many of the test hits are likely
  fixture data using the string, **not read**. This is a starting list, not the C-10 enumeration.
- **The subagent pins** (`agents/*.md` frontmatter `model:`): eight on `claude-sonnet-5`
  (`compliance-witness`, `git-flow`, `headhunter`, `n1-refuter`, `prompt-archaeologist`, `tune-drafter`,
  `ux-onboarding-designer`, `wiki-grounding-auditor`), `n1-judge` on `claude-opus-5`, and `eval-judge` and
  `wiki-scribe` on `claude-haiku-4-5-20251001`. `CLAUDE.md` §"Model-pin convention" says the dated-versus-
  undated split is provider-imposed and tells agents not to "fix" it by re-pinning.
- **Latest eval records.** `evals/results/20261017_154819Z.jsonl` names only `claude-sonnet-5` and
  `claude-haiku-4-5-20251001`. A grep for `claude-(sonnet|opus|haiku)-5-5` over `evals/` found no match.
  A grep for `5.5` over `analyzer.py`, `hardening.py`, `CHANGELOG.md`, `evals/`, `promptfooconfig.yaml`
  and the work-item files found only unrelated hits (section numbers, numeric scores in result files);
  **the `-5-5` ID form was not searched in those files separately**. Across the whole repo the `-5-5`
  form appears in handoff provenance stamps (that output was cut off at 40 lines, so the full set was
  not seen).
- **The 5.5 generation is in use as tooling, not as a candidate.** Provenance stamps in
  `docs/dev/handoffs/` show sessions run by `anthropic/claude-sonnet-5-5` (for example
  `llm-handle-leak-and-letter-date.md`) and `anthropic/claude-opus-5-5` (for example
  `regenerate-persistence.md`); that is the model doing the coding, not a pinned product model.
- **The gated surfaces.** `scripts/enforcement/blast_radius.py:199` and `:204` list `analyzer.py` and
  `hardening.py`. Changing the model constants or the pricing table is a C-10 change: the
  `require-consumer-enumeration` guard will block the edit until
  `docs/dev/blast-radius/<branch-slug>.md` names the surface.
- **The last model bump is the template.** `CHANGELOG.md:5468` (Sonnet 4.6 to Sonnet 5, 2026-07-05)
  touched `analyzer.py`, `hardening.py`, `evals/runner.py`, `promptfooconfig.yaml`, `docs/architecture.md`,
  two `docs/wiki/` cite lines and the Sonnet-pinned `agents/*.md` frontmatter.

## Not verified (C-12: declared, not filled)

Everything below was **not checked against Anthropic's documentation or a live API call** by the
filing session. The 5.5 model IDs it gives come from the filing session's own system context, not from a
source it read.

- That `claude-sonnet-5-5`, `claude-opus-5-5` and `claude-haiku-5-5` are the API model IDs, that each is
  generally available to this account, and whether any is an alias or a dated snapshot.
- Their prices, including cache-write and cache-read rates, and any introductory discount and its end date.
- Whether Sonnet 5.5 keeps adaptive thinking on by default when `thinking` is omitted, and whether
  `thinking={"type": "disabled"}` is accepted.
- **Whether Haiku 5.5 thinks by default, and whether it accepts `thinking: disabled`.** The Haiku path
  sends no `thinking` argument today, so this is the largest unknown: a Haiku with default thinking would
  consume the output budget on the 13 structured calls with no code change on the Haiku path at all.
- Output-token and context limits, and the deprecation dates for `claude-sonnet-5` and
  `claude-haiku-4-5-20251001`.
- Whether the "no Haiku 5" comment at `analyzer.py:1043` is the only stale statement; the same claim is in
  `CHANGELOG.md` (the 2026-07-05 entry, a dated historical record that should not be edited).
- Whether `docs/dev/architecture.md` §"LLM routing + cost" still matches the call sites.
- Whether the Opus pin on `n1-judge` has any role in the product's quality; it is dev tooling.

## Proposals

### As made when the owner asked (kept in full)

1. **File the 5.5 evaluation as a tracked work item.** Done by filing this item.
2. **Run a candidate A/B per model**: Sonnet 5.5 for the heavy-reasoning calls and Haiku 5.5 for the
   structured-selection calls, **keeping each swap separate so the deltas stay attributable**. Opus 5.5 is
   the subagent pin on `n1-judge` only, since the product has no Opus call.
3. **Check whether the `thinking` default carries over to 5.5.**
4. **Fix the stale "no Haiku 5" comment** (`analyzer.py:1043`) as part of that branch.
5. **Follow the model-upgrade playbook** (written for the 2026-07-05 bump, not re-verified since):
   1. Send `thinking={"type": "disabled"}` for the new Sonnet. Adaptive thinking turns on by default and
      eats the 8192-token output cap.
   2. Add the new pricing key and **keep the old one**, so historical `llm_calls.jsonl` records still cost
      out correctly.
   3. Do not bump `PROMPT_VERSION` for a model-only change; the model is its own telemetry axis.
   4. Re-run `python evals/runner.py --suite synthetic`, because `baseline_v1.json` is pinned to the old
      model.
   5. Leave frozen and historical references alone (`RELEASE_ARC.md` snapshots, `baseline_v1.json`, sealed
      review archives, generic test fixtures that use the old string as data); do sync current-state docs
      and the `docs/wiki/` cite lines.
6. **Verify the unverified things first**: the 5.5 API IDs, prices, the `thinking` behavior and the
   `thinking: disabled` acceptance (the list above), before any code change.

### Added by the filing session (proposals, not decisions)

7. **Verify before spending.** The first step is free: read the current model documentation and make one
   cheap live call per model to confirm the ID, the `thinking` default and the usage fields. Record the
   result under `## Updates` with the source. Nothing paid beyond that without the owner's spend approval.
8. **Add the pricing keys first, in the same commit as any constant change.** `compute_call_cost` returns
   `0.0` for an unpriced model, so the order matters: a swap with no key silently zeroes the cost figures
   the evaluation itself relies on. A test that every model constant has a `MODEL_PRICING` key would make
   the order a gate (C-11); whether one exists today is **not checked**.
9. **Move one variable per run.** Sonnet candidate with the Haiku judge unchanged; then Haiku candidate;
   then, separately, the judge. The judge is `JUDGE_MODEL` (`evals/runner.py:117`) and shares the Haiku
   4.5 pin with the candidate being replaced.
10. **Cover Haiku's missing `thinking` argument deliberately.** Decide, from the step-7 observation,
    whether the Haiku path needs an explicit `thinking` setting under 5.5 and whether the equality test at
    `analyzer.py:1594` should become a set or a per-model policy. Adopting adaptive thinking for either tier
    stays a separate, eval-gated change.
11. **Use more than one run on a single fixture.** Item 140b found `data-scientist-junior`'s assemble grounding
    score bimodal (`0.0` or about `1.2` against `4.8` to `5.0`), so a single-run delta on it cannot tell a
    model effect from variance (`docs/dev/diagnosis/ds-junior-score-drop.md`). Pick N per arm in advance,
    write the decision rule before any paid run, and keep the generated text so generator and judge
    variance can be separated (item 140b could not).
12. **Measure cost and latency, not only scores.** Cost from `compute_call_cost` over a telemetry window
    (not the result record's `cost_usd`, which omits failed fixtures); latency per call kind from
    `logs/llm_calls.jsonl` (`/sartor:bench`); and the cache-hit rate, since a model change can change the
    cache key.
13. **Evaluate per call kind, not per tier.** The 13 Haiku sites are different jobs (extraction, clarify,
    recommend, critique and others). One eval-gated branch per swap, with the routing table in
    `docs/dev/architecture.md` kept in step.
14. **Enumerate consumers first (C-10).** The edit set is the 2026-07-05 bump's: `analyzer.py`,
    `hardening.py`, `evals/runner.py`, `promptfooconfig.yaml`, `docs/dev/architecture.md`, the wiki cite
    lines (`docs/wiki/pages/deterministic-llm-boundary.md` and the call-catalog page), and `agents/*.md`;
    plus the literal strings in the test files named above. The grep list in "What was observed" is a
    start; re-derive it, with every name the string goes by, before the first edit.
15. **Decide the subagent pins separately.** The `agents/*.md` pins are dev tooling, change nothing the
    product ships, and `CLAUDE.md` §"Model-pin convention" fixes how they are written. Moving them is its
    own small branch, after the product decision, and the convention note must be revisited if dated 5.5
    snapshots exist.
16. **Candidate runs need a mechanism that does not edit the pins.** AGENTS.md describes the
    prompt-override primitive as covering system-prompt constants only. **Whether a model override exists
    was not searched.** If it does not, a candidate run is either a branch that changes the constants or a
    small committed override, and that design choice is the first item on the implementation branch. The
    item 140b method (a detached worktree outside the repo, `SARTOR_HOME` pointing at the data root,
    `analyzer.__file__` printed per arm, `model` asserted on every record, spend from a telemetry window) is
    the working template; its driver scripts were not committed.
17. **Record the result in `evals/TUNING_LOG.md`** with before and after numbers and provenance, as that file
    already does for prompt changes, so the next generation bump starts from a table.

## Done means

A short written finding, per call kind and per candidate, with measured before and after numbers:
eval scores from `evals/runner.py` with the arm sizes stated in advance, cost from the telemetry window,
latency from `logs/llm_calls.jsonl`. Each swap the finding recommends is its own eval-gated branch.
**The finding is allowed to say "keep the current pins."** Closing this item needs a falsifiable
`verified_by` (a test that every pinned model has a price, or the recorded run) or an owner-named
`closure_exception` (C-11).

## Open question for the owner

Does this item stand alone, or does item 137 absorb it? The filing session recommends keeping them
separate until the free verification (proposal 7) is done, because 137 is a review of settings and this is
a model comparison with a spend, and 137 has sat unstarted since 2026-10-01. That is a recommendation, not
a decision.

## Updates

### 2026-10-17 - filed during docs/model-55-eval-item

Filed from the owner's question in a read-only session, then written up by the session that continued the
thread. The facts above were read at `main` `e490683`. Nothing was run against the API; no model ID,
price or `thinking` behavior for the 5.5 generation was verified (see "Not verified"). Item 137 is
cross-referenced in its own `## Updates`.

### 2026-10-17 - owner decisions, and the first step run (docs/model-55-eval-item)

**Decisions (owner, in chat, 2026-10-17):** "137 absorbs 173" and "authorize first step" (proposal 7). This item is
therefore **closed as absorbed** (see `closure_exception`); the open work continues under item 137. The "Not verified"
list above is superseded by what follows; the filing text is kept as written.

**Sources.** (a) The Models API, `models.retrieve` for six IDs (free). (b) Six minimal live calls ("Reply with the
single word: ok", `max_tokens` 1024) through the project's own client factory, `web_infra.clients._get_client`; they bypass
`analyzer`, so `logs/llm_calls.jsonl` has no rows for them. Cost computed by hand from `usage` at the documented
rates: about `$0.0004` in total. (c) The pricing and model-deprecations pages, `platform.claude.com/docs/en/about-claude/pricing`
and `.../model-deprecations`, fetched with `WebFetch` on 2026-10-17 (the pricing page's full text was saved to a file and read
from it). (d) The local `logs/llm_calls.jsonl` (1,564 records, one machine, a mix of dev and eval runs; numbers only).
The driver scripts are in the session scratchpad and are **not committed**.

**Verified: the IDs exist.** `models.retrieve` returned all six:

| id | display name | created | max input | max output | thinking `adaptive` / `enabled` / `disabled` / `between_tools` |
|---|---|---|---|---|---|
| `claude-sonnet-5-5` | Claude Sonnet 5.5 | 2026-09-28 | 1,000,000 | 128,000 | yes / no / **no** / **yes** |
| `claude-haiku-5-5` | Claude Haiku 5.5 | 2026-10-07 | 1,000,000 | 128,000 | yes / no / yes / no |
| `claude-opus-5-5` | Claude Opus 5.5 | 2026-09-21 | 1,000,000 | 128,000 | yes / no / no / no |
| `claude-sonnet-5` (pinned) | Claude Sonnet 5 | 2026-06-29 | 1,000,000 | 128,000 | yes / no / yes / no |
| `claude-haiku-4-5-20251001` (pinned) | Claude Haiku 4.5 | 2025-10-15 | 200,000 | 64,000 | **no** / yes / yes / no |
| `claude-opus-5` (subagent pin) | Claude Opus 5 | 2026-07-24 | 1,000,000 | 128,000 | yes / no / yes / no |

All three 5.5 models list `effort` levels `low`, `medium`, `high`, `xhigh`, `max`; Haiku 4.5 lists none.

**Verified: the live `thinking` behavior** (request ids in parentheses):
- Sonnet 5.5, `thinking` omitted: `200`, one `text` block, `thinking_tokens` 0 (`req_011Cg8zS4cjpJhXdapP8Y5PX`).
- **Sonnet 5.5, `thinking={"type":"disabled"}`: `400 invalid_request_error`**, "To turn thinking off on this model, send
  \"thinking\": {\"type\": \"between_tools\"} instead of {\"type\": \"disabled\"}. ..." (`req_011Cg8zS7hnP7Mczg2F24b1H`).
- Sonnet 5.5, `thinking={"type":"between_tools"}`: `200` (`req_011Cg8zS8KzCfmiJiVKyEh2Q`).
- Haiku 5.5, `thinking` omitted: `200`, `thinking_tokens` 0 (`req_011Cg8zSBgdvj4nfkJVGeAth`); `thinking={"type":"disabled"}`:
  `200` (`req_011Cg8zSDoPtQwJFC1P9kYXs`).
- Opus 5.5, `thinking` omitted: `200`, `thinking_tokens` 0 (`req_011Cg8zSFfkyXt2F3gpGRx7X`).
- **Limit:** all default-thinking calls were a one-word reply, so zero thinking tokens there does **not** show what
  the default does on the product's real prompts. That is still unmeasured.
- `usage` now carries `output_tokens_details.thinking_tokens`, `inference_geo`, `speed`, `service_tier` and a
  `cache_creation` breakdown by TTL. **`logs/llm_calls.jsonl` has no thinking-tokens field** (grep over its keys), so a
  model A/B cannot see thinking spend separately unless the telemetry gains it; `output_tokens` is the only figure.

**Verified from the pricing page (page text, not an invoice):**

| model | input | output | 5m cache write | cache read |
|---|---|---|---|---|
| Sonnet 5.5 | $2 | $10 | $2.50 | $0.10 (0.05x base, footnote 2) |
| Sonnet 5 | $2 (footnote 3) | $10 | $2.50 | $0.20 |
| Haiku 5.5, prompts up to 100,000 tokens | $0.10 | $0.50 | $0.125 | $0.01 |
| Haiku 5.5, prompts over 100,000 tokens | $0.50 | $2.50 | $0.625 | $0.05 |
| Haiku 4.5 | $1 | $5 | $1.25 | $0.10 |
| Opus 5.5 | $4 | $20 | $5 | $0.20 (0.05x base, footnote 2) |
| Opus 5 | $5 | $25 | $6.25 | $0.50 |

Prices per million tokens. A request's prompt length for the Haiku 5.5 tiers counts cache reads and writes.

**Verified from the deprecations page:** `claude-haiku-4-5-20251001` is **Active**, tentative retirement "Not sooner than
October 15, 2026" (a date that has now passed; no deprecation notice is listed, and the page promises at least 60 days'
notice before a public model is retired). `claude-sonnet-5`: not sooner than June 30, 2027. `claude-sonnet-5-5`: September
28, 2027. `claude-haiku-5-5`: October 7, 2027. `claude-opus-5-5`: September 22, 2027. `claude-opus-5`: July 24, 2027.

**Measured: prompt sizes (this machine's `logs/llm_calls.jsonl`).** Total prompt tokens (input plus cache writes plus cache reads),
per record: `claude-haiku-4-5-20251001` n=620, median 2,358, p90 5,162, p99 9,251, max 12,506, **none over 100,000**;
`claude-sonnet-5` n=237, median 5,270, max 21,181. So Haiku 5.5's over-100K tier did not apply to any recorded Haiku
call. One machine, not the large-corpus case; the tier can still matter there.

**Findings that change the plan** (each is an observation above plus a consequence; the consequences are inferences):
1. **A Sonnet swap is not a one-line constant change.** `analyzer.py:1594-1595` sends `thinking={"type":"disabled"}` on
   the Sonnet path; on `claude-sonnet-5-5` that request returns `400`. Pointing `SONNET_MODEL` at 5.5 without changing the
   setting would fail every heavy call. The replacement is `between_tools` (per the API message; the `claude-api` skill's cached
   notes add that it takes no other field, is accepted only at effort `high` or below, and forbids per-message effort changes, **not
   re-verified live**).
2. **Haiku 5.5 changes the Haiku path's default.** Haiku 4.5 does not support `adaptive`; Haiku 5.5 does, and the product's
   Haiku path sends no `thinking` argument. The skill's cached notes say Haiku 5.5 runs adaptive by default; the
   one-word probe did not show it thinking. A decision is needed: send `disabled` explicitly (accepted, verified) to hold
   today's behavior, or adopt adaptive as a separate eval-gated change.
3. **Pricing is wrong for the current pins**, independent of 5.5: filed as item 174.
4. **Haiku 4.5 is past its earliest retirement date and is also the eval judge and two subagent pins.** Nothing is
   scheduled, but the 60-day notice means the move off it may come with little lead time. This raises the priority of item
   137.
5. **Cache reads on Sonnet 5.5 and Opus 5.5 are priced at 0.05x base** (half Sonnet 5's per-token read price). The product
   leans on prompt caching, so a Sonnet 5.5 cost advantage is plausible; **unmeasured**.
6. **Haiku 5.5's prompt-length tiers cannot be expressed in `MODEL_PRICING`'s flat per-model rates**; adding the 5.5 keys
   needs a change to `compute_call_cost`, not only new entries (also in item 174).

**Still not verified:** how Sonnet 5.5, Haiku 5.5 and Opus 5.5 score on the eval fixtures; whether the default `thinking` on real
prompts truncates the 8192-token `MAX_TOKENS` budget; the latency and cache-hit differences; whether `between_tools` changes
output quality or length on the structured-JSON calls; the platform availability for this account beyond these six calls.

**Proposals status after the first step:** 1 (file the item): done. 3 (does the `thinking` default carry over): answered
for the `disabled` setting (it does not on Sonnet 5.5), not for the default on real prompts. 6 and 7: done, results above. 2,
4, 5, 8 to 17: open, now under item 137. Proposal 4 (the stale "no Haiku 5" comment) is still unmade.
