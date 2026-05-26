"""Drive the wizard to produce the 10 manifest screenshots.

Generates a synthetic Priya master .docx (matching the worked
example at docs/walkthrough_example.md), walks through all six
wizard steps via Playwright, and captures the 10 PNGs per
docs/ux/screenshot_capture.md.

Cost: ~$0.27 in Anthropic API spend per run (full wizard pass:
extract_experiences + analyze + clarify + recommend_bullets +
recommend_summaries + critique × N + generate + cover letter).
Time: ~6-8 minutes including LLM waits.

Prereqs: app must be running (`python app.py` in another shell),
.api_key in place, Chromium installed (`python -m playwright
install chromium`).

Usage:
    python -m scripts.capture_screenshots
    python -m scripts.capture_screenshots --headless
    python -m scripts.capture_screenshots --keep-user

Cleanup: by default the script deletes the demo user and its
on-disk artefacts after capture. Pass --keep-user to retain them
(useful when iterating on capture states).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from docx import Document
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PWTimeout

REPO = Path(__file__).resolve().parent.parent
SHOTS = REPO / "docs" / "screenshots"
TMP = REPO / "scripts" / "_tmp_capture"
APP_URL = "http://localhost:5000"
DEMO_USER = "demo"
VIEWPORT = {"width": 1440, "height": 900}

# Generous timeouts — analyze and generate both routinely take 30-60s.
LLM_TIMEOUT_MS = 120_000
SHORT_TIMEOUT_MS = 15_000


PRIYA_JD = """\
Senior Backend Engineer, Platform — Vertica Logistics

We're hiring a senior IC to own the platform that powers our
real-time shipment tracking and routing engine. You'll work in
Python on a Postgres + AWS stack, with heavy use of Kafka for
our event backbone. Comfort with Kafka topic design, partition
strategy, and consumer-lag debugging is essential.

You'll partner with our SRE and data teams, lead architectural
reviews, and mentor a team of 6 mid- and junior-level engineers
on the platform group. We need someone who has led migrations
of similar scope — moving production systems off legacy queues
onto Kafka, refactoring monolithic services into event-driven
ones. Kafka experience is non-negotiable; we use Kafka across
12 topics serving 8k events/sec at peak.

Bonus: Kubernetes experience, prior work on logistics or
supply-chain platforms.

Stack: Python 3.11+, Postgres 14, AWS (ECS, RDS, S3), Kafka,
Datadog, Terraform. We deploy via GitHub Actions. The team
runs an on-call rotation but expects engineers to invest in
reducing pages rather than absorbing them.

Compensation is competitive for a senior IC role in our region.
We're remote-first; HQ is in Seattle if you want to come in.
"""

SAMPLE_REFINE_NOTE = "emphasize the team-lead role more in the summary"


def write_priya_docx(path: Path) -> None:
    """Synthetic master résumé matching docs/walkthrough_example.md.

    Generates a minimal but parser-friendly .docx with three
    experiences, ~8 bullets each, one Kafka-passing-mention bullet
    on the Helix card, no team-size claim anywhere. Also drops a
    copy into resumes/<DEMO_USER>/ so the import-legacy route
    finds it during onboarding.
    """
    doc = Document()
    doc.add_heading("Priya Sharma", level=0)
    doc.add_paragraph("priya.sharma@example.com · linkedin.com/in/priya-sharma")

    doc.add_heading("Experience", level=1)

    doc.add_heading("Helix Logistics — Senior Backend Engineer", level=2)
    doc.add_paragraph("2023 – Present")
    for bullet in [
        "Built and maintained Python services on the order-routing platform serving 4M+ daily shipments.",
        "Owned the order-events pipeline; helped migrate it off AWS SQS to Kafka over a six-month dual-write/cutover phase.",
        "Designed Postgres schemas and partition strategies for the routing engine; reduced p99 query latency from 1.2s to 180ms.",
        "Led architecture reviews for the platform team; wrote four ADRs that became the team's default patterns.",
        "Mentored junior and mid-level engineers through pairing, code review, and brown-bag tech talks.",
        "Built incident-response runbooks for the on-call rotation; cut median MTTR from 47 to 18 minutes.",
        "Set up Datadog dashboards and SLOs for the routing service; standardized monitoring patterns across the platform group.",
        "Refactored a monolithic dispatch service into three event-driven services; cut deploy lead time 4x.",
    ]:
        doc.add_paragraph(bullet, style="List Bullet")

    doc.add_heading("Northwind Foods — Backend Engineer", level=2)
    doc.add_paragraph("2019 – 2023")
    for bullet in [
        "Built Postgres-backed inventory and pricing services in Python and FastAPI.",
        "Tuned Postgres query plans and indexing for the catalog service; improved key endpoint throughput 3x.",
        "Implemented webhook integrations with supplier APIs; handled idempotency and retry logic at the application layer.",
        "Migrated legacy Django reports onto a Looker dashboard; freed two engineers from one-off report requests.",
        "Wrote pytest integration suites with real Postgres in CI; cut prod regressions in the catalog service to near zero.",
        "Partnered with the data team to ship a daily ETL into Snowflake; replaced a fragile cron-on-EC2 job.",
        "Refactored CI/CD scripts from Bash into Python; made them testable.",
        "Reviewed PRs across three sister teams; informally mentored two engineers who later took senior roles.",
    ]:
        doc.add_paragraph(bullet, style="List Bullet")

    doc.add_heading("Carver Robotics — Junior Backend Engineer", level=2)
    doc.add_paragraph("2017 – 2019")
    for bullet in [
        "Wrote Python services for the robot fleet's command-and-control layer.",
        "Built REST APIs in Flask for the operator console.",
        "Maintained ROS integration scripts that bridged the Python services and the robot firmware layer.",
        "Wrote CAD-pipeline tooling in Python to ingest part specs from the mechanical engineering team.",
        "Built test harnesses simulating robot sensor input for the backend.",
        "Contributed to monitoring dashboards for the fleet-management service.",
    ]:
        doc.add_paragraph(bullet, style="List Bullet")

    doc.add_heading("Skills", level=1)
    doc.add_paragraph(
        "Python, Postgres, AWS (ECS, RDS, S3), Kafka, FastAPI, Flask, "
        "Datadog, Terraform, GitHub Actions, pytest, Docker."
    )

    doc.add_heading("Education", level=1)
    doc.add_paragraph("B.S. Computer Science, University of Washington, 2017")

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    print(f"  ✓ wrote {path.relative_to(REPO)}")

    # Also drop a copy into resumes/<DEMO_USER>/ so the
    # /api/users/<user>/import-legacy route (which reads from that
    # directory under with_llm=true) finds it during onboarding.
    legacy_dir = REPO / "resumes" / DEMO_USER
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_path = legacy_dir / "priya_master.docx"
    shutil.copyfile(str(path), str(legacy_path))
    print(f"  ✓ wrote {legacy_path.relative_to(REPO)}")


def cap(page: Page, filename: str) -> None:
    out = SHOTS / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out), full_page=False)
    print(f"  📸 {out.relative_to(REPO)}")


def wait_quiet(page: Page, ms: int = 600) -> None:
    """Small settle pause so animated transitions complete before capture."""
    page.wait_for_timeout(ms)


def ensure_demo_user(page: Page) -> None:
    """Create the demo user via the New User form if not already present."""
    page.wait_for_selector("#userSelect", timeout=SHORT_TIMEOUT_MS)
    options = page.eval_on_selector_all(
        "#userSelect option", "els => els.map(e => e.value)"
    )
    if DEMO_USER in options:
        print(f"  · {DEMO_USER!r} user already exists; selecting it")
        page.select_option("#userSelect", DEMO_USER)
        return

    print(f"  · creating {DEMO_USER!r} user")
    page.click("text=New user")
    page.wait_for_selector("#newUsername", state="visible")
    page.fill("#newUsername", DEMO_USER)
    page.fill("#newName", "Priya Sharma")
    page.fill("#newEmail", "priya.sharma@example.com")
    # leave phone / linkedin / website blank — not load-bearing for capture
    page.click("text=Create")
    # Selection happens automatically post-create.
    page.wait_for_function(
        f"document.getElementById('userSelect').value === '{DEMO_USER}'",
        timeout=SHORT_TIMEOUT_MS,
    )


def ensure_corpus_imported(page: Page) -> None:
    """Import the synthetic .docx into the demo user's corpus.

    For a brand-new user, the UI's upload path returns 409 +
    opens an onboarding modal; the modal's "Import" button hits
    /api/users/<user>/import-legacy which reads from resumes/<user>/.
    We bypass the modal entirely and call that route directly via
    Playwright's request context — same outcome, no headless flake.
    """
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible")
    wait_quiet(page)

    # If the corpus is already populated (re-run with --keep-user),
    # skip the import entirely.
    existing = page.locator("#corpusExperienceList .corpus-card").count()
    if existing > 0:
        print(f"  · corpus already has {existing} experiences; skipping import")
        cap(page, "walkthrough_setup_corpus-empty.png")
        return

    # Capture S03 — empty corpus state — BEFORE the import.
    cap(page, "walkthrough_setup_corpus-empty.png")

    print("  · running import_legacy.run_import(demo, with_llm=True)…")
    # ~$0.02 Haiku call for extraction; ~10-20s.
    # We call run_import directly (same path the Flask route wraps)
    # rather than going through HTTP, because the HTTP path was
    # failing with an opaque KeyError('config') that didn't reproduce
    # via curl or a REPL — bypassing it removes Playwright's request
    # encoding, the Flask route, and Flask debug-mode's auto-reload
    # window from the dependency chain.
    from onboarding.import_legacy import run_import
    report = run_import(DEMO_USER, with_llm=True)
    if report.errors:
        raise RuntimeError(
            f"import_legacy reported errors: {report.errors}"
        )
    print(
        f"  · imported: {report.experiences_created} experiences "
        f"({report.experiences_merged} merged), "
        f"{report.bullets_created} bullets"
    )

    # Refresh the Corpus tab UI to render the freshly-imported rows.
    # The cache key _corpusLoadedForUser was set during the empty-state
    # render — clear it so refreshCorpus() actually re-fetches; wrap in
    # an async IIFE so page.evaluate awaits the refresh's promise.
    # Page reload so the freshly-populated DB state is consistent in
    # the page's JS context for the rest of the run. We don't need
    # the Corpus tab to actually render cards (Step 1+ reads from
    # backend APIs that hit the DB directly); the reload is purely
    # belt-and-braces so currentUser + corpus loaded state are clean.
    print("  · reloading page so corpus state is fresh in the UI")
    page.reload()
    page.wait_for_selector("#userSelect", timeout=SHORT_TIMEOUT_MS)
    page.select_option("#userSelect", DEMO_USER)
    page.wait_for_function(
        f"document.getElementById('userSelect').value === '{DEMO_USER}'",
        timeout=SHORT_TIMEOUT_MS,
    )
    wait_quiet(page, 1500)


def run_step1(page: Page) -> None:
    """Step 1 — paste JD, capture pre + post analyze."""
    page.click("#topTabApplication")
    page.click("button.wizard-step[data-wstep='1']")
    page.wait_for_selector("#jdText", state="visible")
    wait_quiet(page)

    page.fill("#jdText", PRIYA_JD)
    wait_quiet(page)
    cap(page, "walkthrough_step1pre_jd-textarea.png")

    print("  · clicking Analyze; this is the ~30-60s Sonnet 4.6 call…")
    page.click("#btnAnalyze")
    page.wait_for_selector(
        "#analysisContent > *", state="attached", timeout=LLM_TIMEOUT_MS
    )
    wait_quiet(page, 1200)
    cap(page, "walkthrough_step1post_analysis-filled.png")
    # Same state, hero shot for README.
    cap(page, "readme_hero_wizard-step1-filled.png")


def run_step2(page: Page) -> None:
    """Step 2 — get clarify questions, type a partial answer.

    Forward navigation uses the in-flow "Continue to Clarify →"
    button, not the wizard rail. The rail's step 2 button stays
    disabled (class=upcoming) until _wizardRender is invoked, which
    only happens via wizardGoTo() — clicking the rail directly is
    a no-op when the step isn't yet "reached." The in-flow button
    calls wizardGoTo(2), which then enables the rail.
    """
    page.click("text=Continue to Clarify →")
    page.wait_for_selector("#panelClarify", state="visible")
    wait_quiet(page)

    print("  · requesting clarification questions (~30s Sonnet call)…")
    page.click("#btnClarify")
    page.wait_for_selector(
        "#clarifyQuestions textarea", state="visible", timeout=LLM_TIMEOUT_MS
    )
    wait_quiet(page, 1000)

    # Type a partial answer in the first question so the capture
    # shows realistic mid-typing state.
    first_answer = page.locator("#clarifyQuestions textarea").first
    first_answer.click()
    first_answer.type(
        "Lead implementer. Designed the topic + partition scheme — 12 topics, 60 partitions on the busiest one,",
        delay=8,
    )
    wait_quiet(page)
    cap(page, "walkthrough_step2_clarify-questions.png")


def run_step3(page: Page) -> None:
    """Step 3 — Compose. Wait for cards, capture; no manual pinning."""
    # Submit minimal clarifications by filling all blanks and clicking submit.
    # (Step 5 will use whatever answers are present.)
    questions = page.locator("#clarifyQuestions textarea")
    qcount = questions.count()
    for i in range(qcount):
        box = questions.nth(i)
        if not (box.input_value() or "").strip():
            box.click()
            box.type("Yes — see prior answer for related context.", delay=4)
    page.click("#btnSubmitClarifications")
    page.wait_for_selector("#panelCompose", state="visible", timeout=LLM_TIMEOUT_MS)
    wait_quiet(page)

    print("  · waiting for compose recommendations (Haiku, multiple calls)…")
    # The cards rendered by loadComposition() use class
    # `compose-experience-card` (see static/app.js:2757), NOT the
    # corpus tab's `.corpus-card`. Same shape of selector bug we
    # hit earlier on the corpus list — they're separate render
    # functions with different class names.
    page.wait_for_selector(
        "#composeList .compose-experience-card", timeout=LLM_TIMEOUT_MS
    )
    wait_quiet(page, 1500)
    cap(page, "walkthrough_step3_compose-experience-card.png")


def run_step4(page: Page) -> None:
    """Step 4 — Template. Modern is the default; let live preview render."""
    page.click("text=Save and continue to Template →")
    page.wait_for_selector("#panelTemplate", state="visible")
    wait_quiet(page)
    # Try to click the Modern card if not already selected. Templates render
    # dynamically into #templatePickList — pick the second card by index as
    # a stable proxy for "Modern" (Classic is usually first).
    items = page.locator("#templatePickList [role='option']")
    if items.count() >= 2:
        items.nth(1).click()
    # Wait for the live preview iframe to load content.
    page.wait_for_selector("#livePreviewFrame", state="visible")
    wait_quiet(page, 2000)
    cap(page, "walkthrough_step4_template-modern-preview.png")


def run_step5_and_6(page: Page) -> None:
    """Step 5 — Generate. Step 6 — Download. Capture Refine state."""
    page.click("text=Continue to Generate →")
    page.wait_for_selector("#panelGenerate", state="visible")
    wait_quiet(page)

    print("  · generating résumé (~30-60s Sonnet 4.6 call)…")
    page.click("#btnGenerate")
    page.wait_for_selector(
        "#panelOutput", state="visible", timeout=LLM_TIMEOUT_MS
    )
    page.wait_for_selector(
        "#resumePreview", state="visible", timeout=LLM_TIMEOUT_MS
    )
    wait_quiet(page, 2000)

    # Type a sample refine note so the capture shows what refinement
    # looks like in practice. #refinementInput lives inside
    # #refinementArea, which is unhidden after the first generate.
    try:
        page.wait_for_selector("#refinementInput", state="visible", timeout=SHORT_TIMEOUT_MS)
        page.locator("#refinementInput").click()
        page.locator("#refinementInput").type(SAMPLE_REFINE_NOTE, delay=8)
        wait_quiet(page)
    except PWTimeout:
        print("  · refinement input not visible; capturing without it")
    cap(page, "walkthrough_step6_download-with-refine.png")


def run_cover_letter(page: Page) -> None:
    """Optional — generate cover letter, capture."""
    cover_btn = page.locator("#btnGenerateCover")
    if cover_btn.count() == 0:
        print("  · cover-letter button not found; skipping S10")
        return
    print("  · generating cover letter (~30s Sonnet call)…")
    cover_btn.click()
    # Switch to the cover-letter tab if not auto-switched.
    try:
        page.wait_for_selector("#tabCoverLetter.active", timeout=SHORT_TIMEOUT_MS)
    except PWTimeout:
        page.click("#tabBtnCoverLetter")
    page.wait_for_selector(
        "#coverLetterPreview, #tabCoverLetter [contenteditable]",
        state="visible",
        timeout=LLM_TIMEOUT_MS,
    )
    wait_quiet(page, 1500)
    cap(page, "walkthrough_coverletter_first-generation.png")


def capture_user_picker(page: Page) -> None:
    """S02 — capture the user-picker section with the New User form open.

    Native <select> dropdowns are OS-rendered and not Playwright-screenshot-
    able while open, so we use the New User form (DOM-rendered) as a more
    informative substitute. Shows both the picker and the create affordance.
    """
    page.goto(APP_URL)
    page.wait_for_selector("#panelUser", state="visible", timeout=SHORT_TIMEOUT_MS)
    page.click("text=New user")
    page.wait_for_selector("#newUserForm", state="visible")
    page.fill("#newUsername", "your-username")
    wait_quiet(page)
    cap(page, "install_setup_user-picker.png")
    # Restore a clean state for the rest of the run.
    page.reload()


def cleanup(keep_user: bool) -> None:
    if keep_user:
        print(f"  · keeping {DEMO_USER!r} user + corpus per --keep-user flag")
        return
    print("  · cleaning up demo user artefacts…")
    for sub in [
        REPO / "configs" / f"{DEMO_USER}.config",
        REPO / "resumes" / DEMO_USER,
        REPO / "output" / DEMO_USER,
        REPO / "personas" / "owned" / DEMO_USER,
        TMP,
    ]:
        if sub.exists():
            if sub.is_dir():
                shutil.rmtree(sub, ignore_errors=True)
            else:
                sub.unlink(missing_ok=True)
            print(f"    · removed {sub.relative_to(REPO)}")
    # Note: the demo user's rows remain in db/resume.sqlite. That's fine
    # for re-runs; the user can drop the row manually if they want a
    # truly clean DB.


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--headless", action="store_true", help="run Chromium headless")
    ap.add_argument(
        "--keep-user",
        action="store_true",
        help="don't delete the demo user + on-disk artefacts after capture",
    )
    args = ap.parse_args()

    SHOTS.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    docx_path = TMP / "priya_master.docx"

    print("=" * 70)
    print("callback. screenshot capture")
    print("=" * 70)
    print(f"App URL:     {APP_URL}")
    print(f"Demo user:   {DEMO_USER}")
    print(f"Viewport:    {VIEWPORT['width']}x{VIEWPORT['height']}")
    print(f"Output dir:  {SHOTS.relative_to(REPO)}")
    print()

    print("1) Generating synthetic Priya master .docx")
    write_priya_docx(docx_path)
    print()

    start = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            viewport=VIEWPORT,  # type: ignore[arg-type]
            color_scheme="light",
        )
        page = ctx.new_page()
        page.set_default_timeout(SHORT_TIMEOUT_MS)

        print("2) Capturing S02 — user picker section")
        capture_user_picker(page)
        print()

        print("3) Creating demo user")
        page.goto(APP_URL)
        ensure_demo_user(page)
        print()

        print("4) Capturing S03 — empty corpus + importing Priya .docx")
        ensure_corpus_imported(page)
        print()

        print("5) Step 1 — Job + Analyze (S01 hero + S04 pre + S05 post)")
        run_step1(page)
        print()

        print("6) Step 2 — Clarify (S06)")
        run_step2(page)
        print()

        print("7) Step 3 — Compose (S07)")
        run_step3(page)
        print()

        print("8) Step 4 — Template (S08)")
        run_step4(page)
        print()

        print("9) Steps 5 + 6 — Generate + Download (S09)")
        run_step5_and_6(page)
        print()

        print("10) Cover letter (S10)")
        run_cover_letter(page)
        print()

        browser.close()

    elapsed = time.time() - start
    print(f"✓ capture complete in {elapsed:.1f}s")
    print()

    cleanup(keep_user=args.keep_user)

    print()
    print("Next steps:")
    print(f"  · review {SHOTS.relative_to(REPO)}/")
    print("  · if any capture looks off, re-run with --keep-user and iterate")
    print("  · once the 10 PNGs look right, I (Claude) can do the markdown")
    print("    insertion pass per docs/ux/screenshot_capture.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
