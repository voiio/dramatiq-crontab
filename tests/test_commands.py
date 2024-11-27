import io
from unittest.mock import Mock

import pytest
from django.core.management import call_command
from dramatiq_crontab import utils
from dramatiq_crontab.management.commands import crontab


def test_kill_softly():
    with pytest.raises(KeyboardInterrupt) as e:
        crontab.kill_softly(15, None)
    assert "Received SIGTERM (15), shutting down…" in str(e.value)


class TestCrontab:
    @pytest.fixture()
    def patch_launch(self, monkeypatch):
        monkeypatch.setattr(
            "dramatiq_crontab.management.commands.crontab.Command.launch_scheduler",
            lambda s: None,
        )

    def test_default(self, patch_launch):
        with io.StringIO() as stdout:
            call_command("crontab", stdout=stdout)
            assert "Loaded tasks from tests.testapp." in stdout.getvalue()
            assert "Scheduling heartbeat." in stdout.getvalue()

    def test_no_task_loading(self, patch_launch):
        with io.StringIO() as stdout:
            call_command("crontab", "--no-task-loading", stdout=stdout)
            assert "Loaded tasks from tests.testapp." not in stdout.getvalue()
            assert "Scheduling heartbeat." in stdout.getvalue()

    def test_no_heartbeat(self, patch_launch):
        with io.StringIO() as stdout:
            call_command("crontab", "--no-heartbeat", stdout=stdout)
            assert "Loaded tasks from tests.testapp." in stdout.getvalue()
            assert "Scheduling heartbeat." not in stdout.getvalue()

    def test_locked(self):
        """A lock was already acquired by another process."""
        pytest.importorskip("redis", reason="redis is not installed")
        with utils.redis_client.lock("dramatiq-scheduler", blocking_timeout=0):
            with io.StringIO() as stderr:
                call_command("crontab", stderr=stderr)
                assert "Another scheduler is already running." in stderr.getvalue()

    def test_locked_no_refresh(self, monkeypatch):
        """A lock was acquired, but it was not refreshed."""
        pytest.importorskip("redis", reason="redis is not installed")
        scheduler = Mock()
        monkeypatch.setattr(crontab, "scheduler", scheduler)
        utils.redis_client.lock(
            "dramatiq-scheduler", blocking_timeout=0, timeout=1
        ).acquire()
        with io.StringIO() as stdout:
            call_command("crontab", stdout=stdout)
            assert "Starting scheduler…" in stdout.getvalue()

    def test_handle(self, monkeypatch):
        scheduler = Mock()
        monkeypatch.setattr(crontab, "scheduler", scheduler)
        with io.StringIO() as stdout:
            call_command("crontab", stdout=stdout)
            assert "Starting scheduler…" in stdout.getvalue()
        scheduler.start.assert_called_once()

    def test_handle__keyboard_interrupt(self, monkeypatch):
        scheduler = Mock()
        scheduler.start.side_effect = KeyboardInterrupt()
        monkeypatch.setattr(crontab, "scheduler", scheduler)
        with io.StringIO() as stdout:
            call_command("crontab", stdout=stdout)
            assert "Shutting down scheduler…" in stdout.getvalue()
        scheduler.shutdown.assert_called_once()
        scheduler.start.assert_called_once()
