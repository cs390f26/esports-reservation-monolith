"""Run the scripts in scripts/ the way a person would, against a temporary database."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def run(name, *args, answer=None):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / f"{name}.py"), *args],
        input=answer,
        capture_output=True,
        text=True,
    )


def test_seed_then_refuse_then_reset(db_name):
    first = run("seed")
    assert first.returncode == 0, first.stderr
    assert "Spaces: 6" in first.stdout

    second = run("seed")
    assert second.returncode == 1
    assert "already has data" in second.stderr

    reset = run("seed", "--reset", "--dataset", "overwatch")
    assert reset.returncode == 0, reset.stderr
    assert "(overwatch)" in reset.stdout


def test_clear_reservations_then_everything(db_name):
    run("seed")
    partial = run("clear", "-y", "--reservations")
    assert partial.returncode == 0, partial.stderr
    assert "Spaces" not in partial.stdout

    full = run("clear", "-y")
    assert full.returncode == 0, full.stderr
    assert "Spaces: deleted 6" in full.stdout


def test_clear_asks_first(db_name):
    run("seed")
    cancelled = run("clear", answer="n\n")
    assert cancelled.returncode == 1
    assert "Cancelled" in cancelled.stdout


def test_clear_needs_tables(db_name):
    result = run("clear", "-y")
    assert result.returncode == 1
    assert "no tables" in result.stderr


def test_init_db_asks_before_wiping_data(db_name):
    run("seed")
    cancelled = run("init_db", answer="no\n")
    assert cancelled.returncode == 1

    wiped = run("init_db", "-y")
    assert wiped.returncode == 0, wiped.stderr
    assert "Spaces: 6" in run("seed").stdout
