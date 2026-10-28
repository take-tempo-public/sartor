"""The runner's per-cell seeds (item 183, step 3a): `golden-v1` fixtures carry their own ``seed.json``.

LLM-free: `analyze` is replaced by a fake that records the context it was handed and raises, which the
runner turns into a ``pipeline_error`` record and moves on. What these tests pin:

* the seed source is decided once, after the fixtures are selected, and the ``--seed`` path is the same
  as before (``global``);
* a fixture's ``seed.json`` is read only in assemble mode, so ``--suite real`` is unchanged;
* each cell gets its own corpus, opened and closed one at a time;
* a missing or bad cell seed fails before any client exists.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from evals import golden_set as gs
from evals import runner
from evals.seed_import import seeded_session


def _cells() -> list[str]:
    """The committed cells, whatever they are: this file tests the runner, not the dataset's contents."""
    return gs.cell_names(gs.SUITE_DIR)


def _cell_fixtures() -> list[str]:
    """The fixture name of every JD of every committed cell, from the cells' own source files."""
    return sorted(
        gs.fixture_name(cell, jd["slug"])
        for cell in _cells()
        for jd in gs.load_cell(gs.SUITE_DIR, cell)[0]["jds"]
    )


def _golden() -> list[Path]:
    return runner._select_fixtures("golden-v1", None)


def _pairs() -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = gs.load_manifest(gs.SUITE_DIR).get("pairs", [])
    return pairs


def _cell_of(fixture_dir: Path) -> str:
    """The cell whose corpus a fixture runs on: a pair runs on its résumé's cell."""
    if fixture_dir.name.startswith(gs.PAIR_PREFIX):
        pair = next(p for p in _pairs() if gs.pair_fixture_name(p["id"]) == fixture_dir.name)
        return str(pair["resume_fixture"]).split("--")[0]
    return fixture_dir.name.split("--")[0]


class TestSelection:
    def test_the_suite_resolves_to_the_committed_fixtures(self) -> None:
        names = sorted(p.name for p in _golden())
        assert [n for n in names if not n.startswith(gs.PAIR_PREFIX)] == _cell_fixtures()
        assert [n for n in names if n.startswith(gs.PAIR_PREFIX)] == sorted(
            gs.pair_fixture_name(p["id"]) for p in _pairs()
        )
        assert all((p / "seed.json").is_file() for p in _golden())

    def test_its_label_is_the_suite_name(self) -> None:
        assert {runner._suite_of(p) for p in _golden()} == {gs.SUITE}

    def test_all_does_not_include_it(self) -> None:
        assert not set(_golden()) & set(runner._select_fixtures("all", None))

    def test_a_fixture_is_found_by_name(self) -> None:
        name = _golden()[0].name
        assert runner._select_fixtures("synthetic", name) == [runner.GOLDEN_DIR / name]

    def test_the_directory_is_the_one_the_format_module_writes(self) -> None:
        assert runner.GOLDEN_DIR == gs.SUITE_DIR / "fixtures"

    def test_it_is_a_command_line_choice(self) -> None:
        with pytest.raises(SystemExit):
            runner.main(["--suite", "no-such-suite", "--estimate"])


class TestSeedSource:
    GOLDEN = staticmethod(_golden)

    def test_a_given_seed_is_global_in_both_modes(self) -> None:
        for mode in ("generate", "assemble"):
            assert runner._seed_source(mode, has_seed=True, fixtures=_golden()) == "global"

    def test_generate_never_reads_a_fixtures_own_seed(self) -> None:
        # The fixtures HAVE a seed.json; generate mode must not pick it up (real fixtures can too).
        assert all((p / "seed.json").is_file() for p in _golden())
        assert runner._seed_source("generate", has_seed=False, fixtures=_golden()) == "none"

    def test_assemble_uses_each_fixtures_own_seed(self) -> None:
        assert runner._seed_source("assemble", has_seed=False, fixtures=_golden()) == "per_fixture"

    def test_assemble_with_no_seed_anywhere_is_refused(self) -> None:
        synthetic = runner._select_fixtures("synthetic", None)
        with pytest.raises(ValueError, match="requires --seed"):
            runner._seed_source("assemble", has_seed=False, fixtures=synthetic)

    def test_assemble_with_one_cell_missing_its_seed_names_it(self, tmp_path: Path) -> None:
        good = _golden()[0]
        bare = tmp_path / "bare--x"
        bare.mkdir()
        with pytest.raises(ValueError, match="bare--x"):
            runner._seed_source("assemble", has_seed=False, fixtures=[good, bare])

    def test_assemble_with_no_fixtures_is_refused(self) -> None:
        with pytest.raises(ValueError, match="requires --seed"):
            runner._seed_source("assemble", has_seed=False, fixtures=[])

    def test_an_unknown_mode_is_refused_first(self) -> None:
        with pytest.raises(ValueError, match="Unknown mode"):
            runner._check_mode("bogus", has_seed=True, fixtures=_golden())


class TestFixtureHash:
    def test_the_seed_joins_the_hash_only_when_given(self) -> None:
        fdir = _golden()[0]
        without = runner._load_fixture(fdir, seed_mode=True)["hash"]
        with_seed = runner._load_fixture(fdir, seed_mode=True, seed_path=fdir / "seed.json")["hash"]
        base = hashlib.sha256()
        base.update((fdir / "jd.txt").read_bytes())
        base.update((fdir / "expected.json").read_bytes())
        assert without == base.hexdigest()  # unchanged from before this branch
        base.update((fdir / "seed.json").read_bytes())
        assert with_seed == base.hexdigest()

    def test_a_changed_seed_changes_the_hash(self, tmp_path: Path) -> None:
        fdir = tmp_path / "cell--x"
        shutil.copytree(_golden()[0], fdir)
        before = runner._load_fixture(fdir, seed_mode=True, seed_path=fdir / "seed.json")["hash"]
        seed = json.loads((fdir / "seed.json").read_text(encoding="utf-8"))
        seed["candidate"]["name"] = "Someone Else"
        (fdir / "seed.json").write_text(gs.canonical_json(seed), encoding="utf-8")
        after = runner._load_fixture(fdir, seed_mode=True, seed_path=fdir / "seed.json")["hash"]
        assert before != after


class TestEstimate:
    def test_assemble_is_priced_without_a_seed_flag(self) -> None:
        estimate = runner.estimate_spend(
            _golden(), runner._select_rubrics("smoke"), mode="assemble", seed_mode=False
        )
        n = len(_cell_fixtures()) + len(_pairs())  # every fixture, pairs included
        assert len(_golden()) == n
        assert estimate.calls["analyze_extraction"] == n
        assert estimate.calls["recommend"] == n
        assert estimate.calls["generate_cover_letter"] == n
        assert "generate" not in estimate.calls

    def test_generate_over_the_same_fixtures_still_reads_the_resume_files(self) -> None:
        estimate = runner.estimate_spend(
            _golden(), runner._select_rubrics("smoke"), mode="generate", seed_mode=False
        )
        assert estimate.calls["generate"] == len(_golden())
        assert estimate.skipped_fixtures == ()

    def test_the_command_line_estimate_needs_no_seed(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = runner.main(
            ["--suite", "golden-v1", "--mode", "assemble", "--subset", "smoke", "--estimate"]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "analyze_extraction" in out and "recommend" in out

    def test_the_command_line_still_refuses_assemble_on_a_suite_without_seeds(self) -> None:
        assert runner.main(["--suite", "synthetic", "--mode", "assemble", "--estimate"]) == 1


class _Capture:
    """A fake `analyze` that records the context it is handed, then raises (the run goes on)."""

    def __init__(self) -> None:
        self.seen: list[dict[str, Any]] = []

    def __call__(self, client: Any, context: dict[str, Any], **kwargs: Any) -> Any:
        self.seen.append(
            {
                "name": context["candidate"]["name"],
                "companies": sorted(e["company"] for e in context["career_corpus"]),
                "jd_first_line": context["job_description"].split("\n", 1)[0],
            }
        )
        raise RuntimeError("stop here, the context is what is under test")


class TestRunSuite:
    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> _Capture:
        fake = _Capture()
        monkeypatch.setattr(runner, "analyze", fake)
        runner.run_suite(
            suite="golden-v1",
            subset="smoke",
            mode="assemble",
            out_dir=tmp_path / "out",
            client=MagicMock(),
            **kwargs,
        )
        return fake

    def test_each_cell_is_built_from_its_own_corpus(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = self._run(tmp_path, monkeypatch)
        profiles = {c: gs.load_cell(gs.SUITE_DIR, c)[0] for c in _cells()}
        assert len(fake.seen) == len(_golden())
        for fdir, seen in zip(_golden(), fake.seen, strict=True):
            profile = profiles[_cell_of(fdir)]
            roles = [
                r for s in profile["sections"] if s["kind"] == "experience" for r in s["roles"]
            ]
            assert seen["name"] == profile["candidate"]["name"]
            assert seen["companies"] == sorted(r["company"] for r in roles)
            # The posting is the fixture's own: for a pair that is the OTHER cell's, on this cell's corpus.
            assert seen["jd_first_line"] == (fdir / "jd.txt").read_text("utf-8").split("\n", 1)[0]
        assert len(fake.seen) == len(_cell_fixtures()) + len(_pairs())
        pair_runs = {
            fdir.name: seen
            for fdir, seen in zip(_golden(), fake.seen, strict=True)
            if fdir.name.startswith(gs.PAIR_PREFIX)
        }
        assert len(pair_runs) == len(_pairs()) > 0
        by_name = {fdir.name: seen for fdir, seen in zip(_golden(), fake.seen, strict=True)}
        for pair in _pairs():
            resume_run = by_name[pair["resume_fixture"]]
            jd_run = by_name[pair["jd_fixture"]]
            got = pair_runs[gs.pair_fixture_name(pair["id"])]
            assert got["name"] == resume_run["name"] and got["companies"] == resume_run["companies"]
            assert got["jd_first_line"] == jd_run["jd_first_line"]

    def test_the_corpora_are_opened_and_closed_one_at_a_time(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = seeded_session
        state = {"open": 0, "max_open": 0, "opened": 0}

        @contextmanager
        def counting(seed: Any) -> Iterator[Any]:
            with real(seed) as pair:
                state["open"] += 1
                state["opened"] += 1
                state["max_open"] = max(state["max_open"], state["open"])
                try:
                    yield pair
                finally:
                    state["open"] -= 1

        monkeypatch.setattr(runner, "seeded_session", counting)
        self._run(tmp_path, monkeypatch)
        assert state == {"open": 0, "max_open": 1, "opened": len(_golden())}

    def test_the_global_seed_path_still_opens_one_corpus_for_the_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = seeded_session
        opened: list[int] = []

        @contextmanager
        def counting(seed: Any) -> Iterator[Any]:
            opened.append(1)
            with real(seed) as pair:
                yield pair

        monkeypatch.setattr(runner, "seeded_session", counting)
        seed = json.loads((_golden()[0] / "seed.json").read_text(encoding="utf-8"))
        fake = self._run(tmp_path, monkeypatch, seed_data=seed)
        assert opened == [1]
        assert {s["name"] for s in fake.seen} == {seed["candidate"]["name"]}

    def test_the_record_carries_the_suite_and_the_case_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._run(tmp_path, monkeypatch)
        rows = [
            json.loads(line)
            for path in (tmp_path / "out").glob("*.jsonl")
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        assert rows, "the failed pipelines should still leave pipeline_error records"
        assert {r["suite"] for r in rows} == {"golden-v1"}

    def test_a_missing_seed_fails_before_a_client_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fixtures = tmp_path / "fixtures"
        bare = fixtures / "cell--x"
        shutil.copytree(_golden()[0], bare)
        (bare / "seed.json").unlink()
        monkeypatch.setattr(runner, "GOLDEN_DIR", fixtures)
        monkeypatch.setattr(runner, "_get_client", _no_client)
        with pytest.raises(ValueError, match="requires --seed"):
            runner.run_suite(
                suite="golden-v1", subset="smoke", mode="assemble", out_dir=tmp_path / "out"
            )
        assert not (tmp_path / "out").exists()

    def test_a_bad_seed_fails_before_a_client_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fixtures = tmp_path / "fixtures"
        cell = fixtures / "cell--x"
        shutil.copytree(_golden()[0], cell)
        (cell / "seed.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(runner, "GOLDEN_DIR", fixtures)
        monkeypatch.setattr(runner, "_get_client", _no_client)
        with pytest.raises(ValueError, match="seed_schema_version"):
            runner.run_suite(
                suite="golden-v1", subset="smoke", mode="assemble", out_dir=tmp_path / "out"
            )
        assert not (tmp_path / "out").exists()


def _no_client() -> Any:
    raise AssertionError("a client was created before the cell seeds were checked")
