import pytest

from subete import init


@pytest.fixture
def use_database(monkeypatch):
    """Select a temporary database root and install its shared path context."""
    def select(dbroot):
        monkeypatch.setattr(
            "subete.paths.app.execroot.get_execroot",
            lambda: dbroot,
        )
        init.init_system()

    return select
