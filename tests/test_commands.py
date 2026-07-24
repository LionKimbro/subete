"""Integration checks for Subete's Lion execution-root binding."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import lionscliapp as app
from lionscliapp.application import application

from subete import commands
from subete import state
from subete.paths import path
from lionscliapp.paths import get_lock_path, get_project_root


SOURCE_ROOT = Path(__file__).parents[1] / "src"
SERVICE_HOLDER = """
import sys
import time
from pathlib import Path

from subete import commands

ready = Path(sys.argv[1])
release = Path(sys.argv[2])
database_root = sys.argv[3]

def hold_service():
    ready.write_text("ready", encoding="utf-8")
    while not release.exists():
        time.sleep(0.01)

commands.run_service = hold_service
sys.argv = ["subete", "--execroot", database_root, "service"]
commands.main()
"""


def run_subete(arguments, cwd=None):
    """Run the current Subete source in a fresh command process."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SOURCE_ROOT)

    return subprocess.run(
        [sys.executable, "-m", "subete.commands", *arguments],
        capture_output=True,
        cwd=cwd,
        env=environment,
        text=True,
        timeout=10,
    )


def start_lock_holding_service(dbroot):
    """Start a real locked service command with a test-controlled lifetime."""
    ready = dbroot.parent / "service-ready"
    release = dbroot.parent / "service-release"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SOURCE_ROOT)

    process = subprocess.Popen(
        [sys.executable, "-c", SERVICE_HOLDER, str(ready), str(release), str(dbroot)],
        env=environment,
        text=True,
    )

    deadline = time.monotonic() + 10
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.01)

    if not ready.exists():
        process.kill()
        process.wait(timeout=10)
        raise AssertionError("service did not begin holding its lock")

    return process, release


def stop_lock_holding_service(process, release):
    """Release a controlled service and require framework lock cleanup."""
    release.write_text("release", encoding="utf-8")
    process.wait(timeout=10)
    assert process.returncode == 0


def test_setup_locks_the_selected_execution_root(monkeypatch, tmp_path):
    launch = tmp_path / "launch"
    dbroot = tmp_path / "database"
    launch.mkdir()
    dbroot.mkdir()
    observed = {}

    def fake_setup_database():
        state.g["database-id"] = "test-database"
        observed["root"] = path("root")
        observed["project_root"] = get_project_root()
        observed["lock_path"] = get_lock_path()
        observed["lock_exists"] = get_lock_path().is_file()
        return "created"

    app.reset()
    monkeypatch.chdir(launch)
    monkeypatch.setattr(commands, "setup_database", fake_setup_database)
    monkeypatch.setattr(sys, "argv", ["subete", "--execroot", str(dbroot), "setup"])
    try:
        commands.main()
        assert observed == {
            "root": dbroot,
            "project_root": dbroot,
            "lock_path": dbroot / "lock.json",
            "lock_exists": True,
        }
        assert not (dbroot / "lock.json").exists()
        assert not (dbroot / "config.json").exists()
    finally:
        app.reset()


def test_relative_execution_root_becomes_an_absolute_path(monkeypatch, tmp_path):
    launch = tmp_path / "launch"
    dbroot = launch / "database"
    launch.mkdir()
    dbroot.mkdir()
    observed = {}

    def fake_setup_database():
        state.g["database-id"] = "test-database"
        observed["root"] = path("root")
        observed["lock_path"] = get_lock_path().resolve()
        return "created"

    app.reset()
    monkeypatch.chdir(launch)
    monkeypatch.setattr(commands, "setup_database", fake_setup_database)
    monkeypatch.setattr(sys, "argv", ["subete", "--execroot", "database", "setup"])
    try:
        commands.main()
        assert observed == {
            "root": dbroot.resolve(),
            "lock_path": dbroot.resolve() / "lock.json",
        }
    finally:
        app.reset()


def test_service_is_declared_lock_requiring():
    app.reset()
    try:
        commands.declare_application()
        assert application["commands"]["service"]["flags"]["locking"] is True
    finally:
        app.reset()


def test_installed_help_lists_the_intended_subete_commands():
    result = subprocess.run(
        ["subete", "help"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    for command in ("setup", "service", "gui", "checkpoint", "remove-old", "stop"):
        assert command in result.stdout


def test_project_dir_cannot_redirect_the_database_root_or_lock(tmp_path):
    dbroot = tmp_path / "database"
    dbroot.mkdir()

    result = run_subete([
        "--execroot", str(dbroot),
        "--project-dir", ".redirected",
        "setup",
    ])

    assert result.returncode != 0
    assert not (dbroot / "lock.json").exists()
    assert not (dbroot / ".redirected").exists()


def test_service_holds_the_database_lock_for_its_entire_lifetime(tmp_path):
    dbroot = tmp_path / "database"
    dbroot.mkdir()
    process, release = start_lock_holding_service(dbroot)

    try:
        assert (dbroot / "lock.json").is_file()
    finally:
        stop_lock_holding_service(process, release)

    assert not (dbroot / "lock.json").exists()


def test_second_locking_command_against_one_database_is_rejected(tmp_path):
    dbroot = tmp_path / "database"
    dbroot.mkdir()
    process, release = start_lock_holding_service(dbroot)

    try:
        result = run_subete(["--execroot", str(dbroot), "setup"])
    finally:
        stop_lock_holding_service(process, release)

    assert result.returncode != 0
    assert "Project is locked" in result.stderr


def test_different_database_roots_use_independent_locks(tmp_path):
    locked_root = tmp_path / "locked-database"
    other_root = tmp_path / "other-database"
    locked_root.mkdir()
    other_root.mkdir()
    process, release = start_lock_holding_service(locked_root)

    try:
        result = run_subete(["--execroot", str(other_root), "setup"])
    finally:
        stop_lock_holding_service(process, release)

    assert result.returncode == 0
    assert "Subete database created:" in result.stdout
    assert not (other_root / "lock.json").exists()


def test_unlock_removes_only_the_selected_database_lock(tmp_path):
    selected_root = tmp_path / "selected-database"
    other_root = tmp_path / "other-database"
    selected_root.mkdir()
    other_root.mkdir()
    payload = {"lock_id": "stale"}
    (selected_root / "lock.json").write_text(json.dumps(payload), encoding="utf-8")
    (other_root / "lock.json").write_text(json.dumps(payload), encoding="utf-8")

    result = run_subete(["--execroot", str(selected_root), "unlock"])

    assert result.returncode == 0
    assert not (selected_root / "lock.json").exists()
    assert (other_root / "lock.json").is_file()


def test_importing_subete_commands_has_no_filesystem_side_effects(tmp_path):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SOURCE_ROOT)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from subete import commands; commands.declare_application()",
        ],
        capture_output=True,
        cwd=tmp_path,
        env=environment,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert list(tmp_path.iterdir()) == []
