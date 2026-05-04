#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Smoke tests for skill-conductor scripts.

Run: uv run scripts/test_smoke.py

Tests verify the most critical scripts execute successfully on a known-good
skill, fail loudly on a known-bad skill, and produce expected output shapes.

This is not a full unit test suite — it's a fast safety net so we don't ship
broken scripts. Real behavior is verified by Mode 3 VALIDATE on real skills.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
UV_BIN = shutil.which("uv") or "/home/shima/.local/bin/uv"
RESULTS = []


def run(label: str, fn) -> None:
    """Run a test, print pass/fail, accumulate failures."""
    try:
        fn()
        RESULTS.append((label, True, None))
        print(f"  ✓ {label}")
    except AssertionError as e:
        RESULTS.append((label, False, str(e)))
        print(f"  ✗ {label}: {e}")
    except Exception as e:
        RESULTS.append((label, False, f"{type(e).__name__}: {e}"))
        print(f"  ✗ {label}: {type(e).__name__}: {e}")


def make_good_skill(tmp: Path) -> Path:
    """Create a minimally valid skill folder for tests."""
    skill = tmp / "test-good-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: test-good-skill\n"
        "description: A test skill for smoke testing. Use when running smoke tests.\n"
        "---\n\n"
        "# Test Good Skill\n\n"
        "This is a test skill. It exists only for smoke tests.\n\n"
        "## Usage\n\n"
        "Do not use in production.\n"
    )
    return skill


def make_bad_skill(tmp: Path) -> Path:
    """Skill with multiple violations (no frontmatter, wrong name)."""
    skill = tmp / "BadSkill_Name"  # wrong case + underscore
    skill.mkdir()
    (skill / "SKILL.md").write_text("# No frontmatter here\n")
    return skill


# --- utils.parse_skill_md ---

def test_parse_good():
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import utils
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_good_skill(Path(tmp))
            name, desc, content = utils.parse_skill_md(skill)
            assert name == "test-good-skill", f"name: {name}"
            assert "smoke testing" in desc, f"desc: {desc}"
            assert "# Test Good Skill" in content
    finally:
        sys.path.pop(0)


def test_parse_no_frontmatter_raises():
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import utils
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_bad_skill(Path(tmp))
            try:
                utils.parse_skill_md(skill)
                raise AssertionError("expected ValueError on missing frontmatter")
            except ValueError:
                pass
    finally:
        sys.path.pop(0)


# --- eval_skill.py ---

def test_eval_skill_good_passes():
    with tempfile.TemporaryDirectory() as tmp:
        skill = make_good_skill(Path(tmp))
        result = subprocess.run(
            [UV_BIN, "run", str(SCRIPTS_DIR / "eval_skill.py"), str(skill)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
        assert "10/10" in result.stdout or "PASS" in result.stdout.upper(), \
            f"expected pass marker, got: {result.stdout[:300]}"


def test_eval_skill_bad_fails():
    with tempfile.TemporaryDirectory() as tmp:
        skill = make_bad_skill(Path(tmp))
        result = subprocess.run(
            [UV_BIN, "run", str(SCRIPTS_DIR / "eval_skill.py"), str(skill)],
            capture_output=True, text=True, timeout=30,
        )
        # bad skill must either exit non-zero or report failures
        combined = result.stdout + result.stderr
        assert result.returncode != 0 or "FAIL" in combined.upper() or "ERROR" in combined.upper(), \
            f"expected failure for bad skill, got: {combined[:300]}"


# --- quick_validate.py ---

def test_quick_validate_good_passes():
    with tempfile.TemporaryDirectory() as tmp:
        skill = make_good_skill(Path(tmp))
        result = subprocess.run(
            [UV_BIN, "run", str(SCRIPTS_DIR / "quick_validate.py"), str(skill)],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:300]}"


def test_quick_validate_bad_fails():
    with tempfile.TemporaryDirectory() as tmp:
        skill = make_bad_skill(Path(tmp))
        result = subprocess.run(
            [UV_BIN, "run", str(SCRIPTS_DIR / "quick_validate.py"), str(skill)],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode != 0, "expected non-zero exit on bad skill"


# --- init_skill.py ---

def test_init_skill_creates_structure():
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [UV_BIN, "run", str(SCRIPTS_DIR / "init_skill.py"),
             "smoke-init-test", "--path", tmp],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
        created = Path(tmp) / "smoke-init-test"
        assert created.exists(), f"skill dir not created at {created}"
        assert (created / "SKILL.md").exists(), "SKILL.md not created"
        # frontmatter should be valid
        content = (created / "SKILL.md").read_text()
        assert content.startswith("---"), "frontmatter missing"
        assert "name: smoke-init-test" in content, "name not set"


# --- package_skill.py ---

def test_package_skill_creates_zip():
    with tempfile.TemporaryDirectory() as tmp:
        skill = make_good_skill(Path(tmp))
        out_dir = Path(tmp) / "dist"
        out_dir.mkdir()
        result = subprocess.run(
            [UV_BIN, "run", str(SCRIPTS_DIR / "package_skill.py"),
             str(skill), str(out_dir)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:500]}"
        produced = list(out_dir.glob("*.skill"))
        assert len(produced) == 1, f"expected 1 .skill file, got {len(produced)}: {produced}"
        # .skill should be a valid zip
        import zipfile
        assert zipfile.is_zipfile(produced[0]), f"{produced[0]} is not a zip"


# --- aggregate_benchmark.py (smoke: --help works) ---

def test_aggregate_benchmark_help():
    result = subprocess.run(
        [UV_BIN, "run", str(SCRIPTS_DIR / "aggregate_benchmark.py"), "--help"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, f"--help failed: {result.stderr}"
    assert "skill" in result.stdout.lower() or "benchmark" in result.stdout.lower()


# --- run all ---

def main():
    print("\nskill-conductor smoke tests\n" + "─" * 32)

    print("\nutils.parse_skill_md:")
    run("parses good skill", test_parse_good)
    run("raises on bad frontmatter", test_parse_no_frontmatter_raises)

    print("\neval_skill.py:")
    run("good skill passes", test_eval_skill_good_passes)
    run("bad skill fails", test_eval_skill_bad_fails)

    print("\nquick_validate.py:")
    run("good skill passes", test_quick_validate_good_passes)
    run("bad skill fails", test_quick_validate_bad_fails)

    print("\ninit_skill.py:")
    run("creates skill structure", test_init_skill_creates_structure)

    print("\npackage_skill.py:")
    run("creates valid .skill zip", test_package_skill_creates_zip)

    print("\naggregate_benchmark.py:")
    run("--help works", test_aggregate_benchmark_help)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'─' * 32}\n{passed}/{total} passed")

    if passed != total:
        print("\nfailures:")
        for label, ok, err in RESULTS:
            if not ok:
                print(f"  - {label}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
