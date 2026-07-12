"""Interactive CLI for reviewing LLM-extracted experiences and bullets.

Walks the user through every `experience` whose title or bullets are still
flagged `is_pending_review=1`. For each one, the user can:

- Accept the experience as canonical (clears pending flags on title + bullets)
- Drill into individual bullets (accept / edit text / edit tags / drop)
- Drop the entire experience (hard-delete; cascades to title + bullets)
- Edit company / dates / title inline
- Skip (leave pending; revisit later)
- Quit (saves progress per-experience; safe to abort)

This is a temporary affordance — Phase D's frontend rebuild ships a real
review UI. Until then, this tool prevents flying blind on LLM extraction
quality.

Usage:
    python -m onboarding.review_cli --user testuser
    python -m onboarding.review_cli --user testuser --db /tmp/test.sqlite
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Iterator
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Candidate, Experience
from db.session import get_session, init_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Minimal terminal colors. Windows 10+ supports ANSI but legacy cmd.exe
# needs ENABLE_VIRTUAL_TERMINAL_PROCESSING flipped on stdout's console mode.
# ---------------------------------------------------------------------------


class Color:
    """ANSI escape codes for the review CLI's terminal styling."""

    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    HEADER = "\x1b[1;36m"  # bold cyan
    PROMPT = "\x1b[1;33m"  # bold yellow
    OK = "\x1b[32m"  # green
    WARN = "\x1b[33m"  # yellow
    ERROR = "\x1b[31m"  # red
    META = "\x1b[2;37m"  # dim white


def _enable_ansi_on_windows() -> None:
    """Set ENABLE_VIRTUAL_TERMINAL_PROCESSING on the stdout handle.

    No-op on non-Windows. On Windows Terminal / modern PowerShell this is
    already on; on legacy cmd.exe it has to be flipped. If ctypes fails for
    any reason we silently fall through — the worst case is escape sequences
    render as garbage glyphs, not a crash.
    """
    # os.name (not sys.platform) is the Windows guard on purpose: mypy statically
    # narrows `sys.platform` to the --platform value, so `sys.platform != "win32"`
    # marks this whole block unreachable under the Linux CI platform and trips
    # `warn_unreachable`. `os.name` is typed `str` (never narrowed), so the block
    # stays reachable on every platform — the same reason app.py guards with
    # `sys.platform.startswith(...)` rather than an `==` literal.
    if os.name != "nt":
        return
    try:
        import ctypes

        # ctypes.windll exists only on win32; widen ctypes to Any via cast so mypy
        # (which now type-checks this reachable block against Linux too) doesn't
        # flag a missing attribute — and, unlike a constant getattr, ruff is happy.
        # Runtime-guarded by the os.name check above.
        kernel32 = cast(Any, ctypes).windll.kernel32
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception as exc:
        # Silent degrade is intentional — without ANSI, escape sequences render
        # as garbage but the tool still works. Log at debug for diagnosis.
        logger.debug("ANSI enable failed: %s", exc)


# ---------------------------------------------------------------------------
# Review session — state + actions
# ---------------------------------------------------------------------------


class ReviewSession:
    """Drives the interactive loop. One session per CLI invocation.

    Tracks per-run counters for the final summary. Commits to the DB after
    every experience-level action so partial progress survives a Ctrl-C.
    """

    def __init__(self, session: Session, candidate: Candidate) -> None:
        """Initialize a review session with per-run action counters zeroed."""
        self.session = session
        self.candidate = candidate
        self.accepted = 0
        self.dropped = 0
        self.skipped = 0
        self.edited = 0

    def pending_experiences(self) -> list[Experience]:
        """Return experiences belonging to this candidate that have any pending title or bullet, ordered newest-first."""
        stmt = (
            select(Experience)
            .where(Experience.candidate_id == self.candidate.id)
            .order_by(Experience.start_date.desc())
        )
        all_for_candidate = list(self.session.execute(stmt).scalars())
        return [e for e in all_for_candidate if self._is_pending(e)]

    @staticmethod
    def _is_pending(exp: Experience) -> bool:
        """True if any of the experience's titles or bullets is still pending review."""
        if any(t.is_pending_review for t in exp.titles):
            return True
        return any(b.is_pending_review for b in exp.bullets)

    # -- Display --

    def show_experience(self, exp: Experience, idx: int, total: int) -> None:
        """Print one experience block — header, titles, and bullets — to the terminal."""
        print()
        print(f"{Color.HEADER}{'═' * 70}{Color.RESET}")
        print(
            f"{Color.HEADER}Experience {idx} of {total}{Color.RESET} {Color.DIM}— pending review{Color.RESET}"
        )
        print(f"{Color.HEADER}{'═' * 70}{Color.RESET}")
        print(f"  {Color.BOLD}Company:{Color.RESET}  {exp.company}")
        if exp.location:
            print(f"  {Color.BOLD}Location:{Color.RESET} {exp.location}")
        date_range = f"{exp.start_date} → {exp.end_date or 'present'}"
        print(f"  {Color.BOLD}Dates:{Color.RESET}    {date_range}")

        if exp.titles:
            for t in exp.titles:
                marker = "★" if t.is_official else " "
                pending_tag = f" {Color.WARN}[pending]{Color.RESET}" if t.is_pending_review else ""
                print(f"  {Color.BOLD}Title:{Color.RESET}    {marker} {t.title}{pending_tag}")
        else:
            print(f"  {Color.BOLD}Title:{Color.RESET}    {Color.WARN}(none){Color.RESET}")

        active_bullets = [b for b in exp.bullets if b.is_active]
        pending_bullets = [b for b in active_bullets if b.is_pending_review]
        print(
            f"\n  {Color.BOLD}Bullets:{Color.RESET} "
            f"{len(active_bullets)} active "
            f"({Color.WARN}{len(pending_bullets)} pending{Color.RESET})"
        )

        for i, b in enumerate(active_bullets, start=1):
            pending_marker = (
                f"{Color.WARN}[P]{Color.RESET}"
                if b.is_pending_review
                else f"{Color.OK}[✓]{Color.RESET}"
            )
            outcome_marker = f"{Color.OK}#{Color.RESET}" if b.has_outcome else " "
            text = b.text if len(b.text) <= 100 else b.text[:97] + "..."
            print(f"    {pending_marker} {outcome_marker} {i:>2}. {text}")

    # -- Top-level prompt --

    def prompt_action(self) -> str:
        """Prompt for and return the top-level per-experience action key."""
        print(
            f"\n  {Color.PROMPT}Action:{Color.RESET} "
            f"[{Color.BOLD}a{Color.RESET}]ccept all  "
            f"[{Color.BOLD}b{Color.RESET}]ullets  "
            f"[{Color.BOLD}e{Color.RESET}]dit fields  "
            f"[{Color.BOLD}d{Color.RESET}]rop  "
            f"[{Color.BOLD}s{Color.RESET}]kip  "
            f"[{Color.BOLD}q{Color.RESET}]uit"
        )
        return input("  > ").strip().lower()

    # -- Action handlers --

    def accept_all(self, exp: Experience) -> None:
        """Mark every title and bullet on the experience reviewed, then commit."""
        for t in exp.titles:
            t.is_pending_review = 0
        for b in exp.bullets:
            b.is_pending_review = 0
        self.session.commit()
        self.accepted += 1
        print(
            f"  {Color.OK}✓ Accepted — title + {len(exp.bullets)} bullets are now canonical.{Color.RESET}"
        )

    def drop_experience(self, exp: Experience) -> None:
        """Confirm, then permanently delete the experience and all its bullets."""
        confirm = (
            input(
                f"  {Color.WARN}Delete experience '{exp.company}' and all its bullets? "
                f"This is permanent. [y/N] {Color.RESET}"
            )
            .strip()
            .lower()
        )
        if confirm != "y":
            print("  Cancelled.")
            return
        self.session.delete(exp)
        self.session.commit()
        self.dropped += 1
        print(f"  {Color.ERROR}✗ Dropped.{Color.RESET}")

    def skip(self) -> None:
        """Leave the current experience pending and bump the skip counter."""
        self.skipped += 1
        print(f"  {Color.DIM}Skipped — will remain pending.{Color.RESET}")

    def review_bullets(self, exp: Experience) -> None:
        """Drill into the experience's pending bullets, accepting or editing each."""
        active = [b for b in exp.bullets if b.is_active]
        if not active:
            print(f"  {Color.DIM}(no active bullets){Color.RESET}")
            return

        for i, b in enumerate(active, start=1):
            if not b.is_pending_review:
                continue
            print(f"\n  {Color.BOLD}Bullet {i}/{len(active)}:{Color.RESET}")
            print(f"    {b.text}")
            outcome = (
                f"{Color.OK}has metric{Color.RESET}"
                if b.has_outcome
                else f"{Color.DIM}no metric{Color.RESET}"
            )
            print(f"    {Color.META}({outcome}){Color.RESET}")
            choice = (
                input(
                    f"    [{Color.BOLD}a{Color.RESET}]ccept  "
                    f"[{Color.BOLD}e{Color.RESET}]dit text  "
                    f"[{Color.BOLD}d{Color.RESET}]rop  "
                    f"[{Color.BOLD}s{Color.RESET}]kip  "
                    f"[{Color.BOLD}q{Color.RESET}]uit bullets > "
                )
                .strip()
                .lower()
            )
            if choice == "a":
                b.is_pending_review = 0
                self.session.commit()
                self.edited += 1
                print(f"    {Color.OK}✓ accepted{Color.RESET}")
            elif choice == "e":
                new_text = input("    new text (Enter to keep current):\n    > ").strip()
                if new_text:
                    b.text = new_text
                b.is_pending_review = 0
                self.session.commit()
                self.edited += 1
                print(f"    {Color.OK}✓ updated{Color.RESET}")
            elif choice == "d":
                b.is_active = 0
                b.is_pending_review = 0
                self.session.commit()
                self.edited += 1
                print(
                    f"    {Color.ERROR}✗ dropped (soft-delete; preserves audit trail){Color.RESET}"
                )
            elif choice == "q":
                return
            else:  # skip
                continue

    def edit_fields(self, exp: Experience) -> None:
        """Edit the experience's company, location, dates, or title, then commit."""
        print(
            f"  Edit which? "
            f"[{Color.BOLD}c{Color.RESET}]ompany  "
            f"[{Color.BOLD}l{Color.RESET}]ocation  "
            f"[{Color.BOLD}d{Color.RESET}]ates  "
            f"[{Color.BOLD}t{Color.RESET}]itle  "
            f"[{Color.BOLD}b{Color.RESET}]ack"
        )
        choice = input("  > ").strip().lower()
        if choice == "c":
            new = input(f"  Company (current: {exp.company}): ").strip()
            if new:
                exp.company = new
        elif choice == "l":
            new = input(f"  Location (current: {exp.location or '(none)'}): ").strip()
            exp.location = new or None
        elif choice == "d":
            new_start = input(f"  Start (YYYY-MM, current: {exp.start_date}): ").strip()
            if new_start:
                exp.start_date = new_start
            new_end = input(
                f"  End (YYYY-MM or 'present', current: {exp.end_date or 'present'}): "
            ).strip()
            if new_end:
                exp.end_date = None if new_end.lower() == "present" else new_end
        elif choice == "t":
            if not exp.titles:
                print(f"  {Color.WARN}No title rows to edit.{Color.RESET}")
                return
            t = exp.titles[0]
            new = input(f"  Title (current: {t.title}): ").strip()
            if new:
                t.title = new
        self.session.commit()
        self.edited += 1
        print(f"  {Color.OK}✓ saved.{Color.RESET}")

    # -- Main loop --

    def run(self) -> int:
        """Run the interactive review loop over all pending experiences."""
        pending = self.pending_experiences()
        total = len(pending)
        if total == 0:
            print(
                f"{Color.OK}No experiences pending review for {self.candidate.username}.{Color.RESET}"
            )
            return 0

        print(
            f"{Color.HEADER}Reviewing {total} experience(s) for {self.candidate.username}.{Color.RESET}"
        )
        print(
            f"{Color.META}Per-experience actions: accept, drill into bullets, edit fields, drop, skip, quit.{Color.RESET}"
        )
        print(
            f"{Color.META}Progress saves after every action. Safe to quit at any time.{Color.RESET}"
        )

        for idx, exp in enumerate(pending, start=1):
            while True:
                self.show_experience(exp, idx, total)
                action = self.prompt_action()
                if action in ("a", "accept"):
                    self.accept_all(exp)
                    break
                if action in ("b", "bullets"):
                    self.review_bullets(exp)
                    continue
                if action in ("e", "edit"):
                    self.edit_fields(exp)
                    continue
                if action in ("d", "drop"):
                    self.drop_experience(exp)
                    break
                if action in ("s", "skip", ""):
                    self.skip()
                    break
                if action in ("q", "quit"):
                    self._print_summary()
                    return 0
                print(f"  {Color.WARN}Unknown action: {action!r}{Color.RESET}")

        self._print_summary()
        return 0

    def _print_summary(self) -> None:
        """Print the end-of-review summary (accepted / dropped / skipped counts)."""
        print()
        print(f"{Color.HEADER}{'═' * 70}{Color.RESET}")
        print(f"{Color.HEADER}Review summary for {self.candidate.username}{Color.RESET}")
        print(f"{Color.HEADER}{'═' * 70}{Color.RESET}")
        print(f"  {Color.OK}Accepted:{Color.RESET} {self.accepted}")
        print(f"  {Color.ERROR}Dropped:{Color.RESET}  {self.dropped}")
        print(f"  {Color.DIM}Skipped:{Color.RESET}  {self.skipped} (still pending)")
        print(f"  Edits made: {self.edited}")
        remaining = len(self.pending_experiences())
        if remaining:
            print(
                f"\n  {Color.WARN}{remaining} experience(s) still have pending titles/bullets.{Color.RESET}"
            )
            print(f"  {Color.META}Re-run this command to continue.{Color.RESET}")
        else:
            print(
                f"\n  {Color.OK}All experiences fully reviewed. Corpus is canonical.{Color.RESET}"
            )


def iter_pending_experiences(session: Session, candidate_id: int) -> Iterator[Experience]:
    """Yield pending experiences for a candidate without running the interactive loop.

    Read-only helper used by tests and any future automation.
    """
    stmt = (
        select(Experience)
        .where(Experience.candidate_id == candidate_id)
        .order_by(Experience.start_date.desc())
    )
    for exp in session.execute(stmt).scalars():
        if any(t.is_pending_review for t in exp.titles):
            yield exp
            continue
        if any(b.is_pending_review for b in exp.bullets):
            yield exp


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: interactively review one user's pending experiences."""
    parser = argparse.ArgumentParser(
        description="Walk through LLM-extracted experiences and bullets interactively."
    )
    parser.add_argument("--user", required=True, help="Username to review")
    parser.add_argument(
        "--db", default=None, help="Override DB path (defaults to db/resume.sqlite)"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    _enable_ansi_on_windows()

    init_db(args.db)
    if args.db is None:
        session = get_session()
    else:
        from db.session import make_engine, make_session_factory

        session = make_session_factory(make_engine(args.db))()

    try:
        candidate = session.query(Candidate).filter_by(username=args.user).first()
        if candidate is None:
            print(
                f"{Color.ERROR}No candidate found with username {args.user!r}.{Color.RESET}\n"
                f"{Color.META}Run the importer first: "
                f"python -m onboarding.corpus_import --user {args.user} --with-llm{Color.RESET}",
                file=sys.stderr,
            )
            return 2

        rs = ReviewSession(session, candidate)
        return rs.run()
    except KeyboardInterrupt:
        print(
            f"\n{Color.WARN}Interrupted — progress through the most-recent committed action was saved.{Color.RESET}"
        )
        return 130
    finally:
        session.close()


__all__ = ["ReviewSession", "iter_pending_experiences", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
