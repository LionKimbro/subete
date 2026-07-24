"""Integration checks for Subete's Lion execution-root binding."""

import sys

import lionscliapp as app
from lionscliapp.application import application

from subete import commands
from subete.paths import path
from lionscliapp.paths import get_lock_path, get_project_root


def test_setup_locks_the_selected_execution_root(monkeypatch, tmp_path):
    launch = tmp_path / "launch"
    dbroot = tmp_path / "database"
    launch.mkdir()
    dbroot.mkdir()
    observed = {}

    def fake_setup_database():
        observed["root"] = path("root")
        observed["project_root"] = get_project_root()
        observed["lock_path"] = get_lock_path()
        observed["lock_exists"] = get_lock_path().is_file()
        return {"status": "created", "database-id": "test-database"}

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


def test_service_is_declared_lock_requiring():
    app.reset()
    try:
        commands.declare_application()
        assert application["commands"]["service"]["flags"]["locking"] is True
    finally:
        app.reset()
