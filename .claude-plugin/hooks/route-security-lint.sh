#!/usr/bin/env bash
# PreToolUse hook on Edit|Write of app.py OR a route-bearing blueprint module
# under blueprints/: when proposed content adds or modifies a Flask route
# (@app.route or @<bp>.route/.get/.post/...) that touches the filesystem,
# require both _safe_username() and _within() to appear in the same content.
# Encodes the security pattern documented in CLAUDE.md "Key Patterns — Security".
#
# Scope (PX-21, v1.0.8 blueprint split): app.py + blueprints/**.py. The
# read-only dashboard/ surface is deliberately NOT covered — its routes are
# localhost-gated, take no <username>, and read fixed diagnostic dirs, so the
# _safe_username/_within user-path guards do not apply there.
#
# Heuristic, not perfect: catches obvious omissions; review still required
# for routes that do filesystem access through indirection.
#
# Portable-enforcement-core adapter (feat/portable-enforcement-core,
# 2026-07-08): thin wrapper forwarding the Claude PreToolUse JSON contract on
# stdin to the shared guard implementation
# (scripts/enforcement/guards/route_security_lint.py), byte-identical to this
# script's pre-migration behavior (see tests/test_enforcement_core.py). The
# same guard also runs as a native git pre-commit hook (.githooks/, opt-in)
# scanning each staged route file's full content, and
# tests/test_route_containment_gate.py remains the whole-tree, AST-based
# do-not-regress gate — this hook only samples at edit/commit time.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" route-security-lint
