import io
from unittest.mock import Mock

import pytest
from crontask import utils
from crontask.management.commands import crontask
from django.core.management import call_command


def test_kill_softly():
    with pytest.raises(KeyboardInterrupt) as e:
        crontask.kill_softly(15, None)
    assert "Received SIGTERM (15), shutting down…" in str(e.value)


class Testcrontask:
    @pytest.fixture()
    def patch_launch(self, monkeypatch):
        monkeypatch.setattr(
            "crontask.management.commands.crontask.Command.launch_scheduler",
            lambda *args, **kwargs: None,
        )

    def test_default(self, patch_launch):
        with io.StringIO() as stdout:
            call_command("crontask", stdout=stdout)
            assert "Loaded tasks from tests.testapp." in stdout.getvalue()
            assert "Scheduling heartbeat." in stdout.getvalue()

    def test_no_task_loading(self, patch_launch):
        with io.StringIO() as stdout:
            call_command("crontask", "--no-task-loading", stdout=stdout)
            assert "Loaded tasks from tests.testapp." not in stdout.getvalue()
            assert "Scheduling heartbeat." in stdout.getvalue()

    def test_no_heartbeat(self, patch_launch):
        with io.StringIO() as stdout:
            call_command("crontask", "--no-heartbeat", stdout=stdout)
            assert "Loaded tasks from tests.testapp." in stdout.getvalue()
            assert "Scheduling heartbeat." not in stdout.getvalue()

    def test_locked(self):
        """A lock was already acquired by another process."""
        pytest.importorskip("redis", reason="redis is not installed")
        with utils.redis_client.lock("crontask-lock", blocking_timeout=0):
            with io.StringIO() as stderr:
                call_command("crontask", stderr=stderr)
                assert "Another scheduler is already running." in stderr.getvalue()

    def test_locked_no_refresh(self, monkeypatch):
        """A lock was acquired, but it was not refreshed."""
        pytest.importorskip("redis", reason="redis is not installed")
        scheduler = Mock()
        monkeypatch.setattr(crontask, "scheduler", scheduler)
        utils.redis_client.lock(
            "crontask-lock", blocking_timeout=0, timeout=1
        ).acquire()
        with io.StringIO() as stdout:
            call_command("crontask", stdout=stdout)
            assert "Starting scheduler…" in stdout.getvalue()

    def test_handle(self, monkeypatch):
        scheduler = Mock()
        monkeypatch.setattr(crontask, "scheduler", scheduler)
        with io.StringIO() as stdout:
            call_command("crontask", stdout=stdout)
            assert "Starting scheduler…" in stdout.getvalue()
        scheduler.start.assert_called_once()

    def test_handle__keyboard_interrupt(self, monkeypatch):
        scheduler = Mock()
        scheduler.start.side_effect = KeyboardInterrupt()
        monkeypatch.setattr(crontask, "scheduler", scheduler)
        with io.StringIO() as stdout:
            call_command("crontask", stdout=stdout)
            assert "Shutting down scheduler…" in stdout.getvalue()
        scheduler.shutdown.assert_called_once()
        scheduler.start.assert_called_once()
