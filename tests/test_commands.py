import io
from unittest.mock import Mock

import pytest
from django.core.management import call_command

from dramatiq_crontab.management.commands import crontab


def test_kill_softly():
    with pytest.raises(KeyboardInterrupt):
        crontab.kill_softly(None, None)


def test_get_redis_client__none(settings):
    settings.DRAMATIQ_CRONTAB = {}
    assert crontab.get_redis_client() is None


@pytest.mark.skipif(crontab.redis is None, reason="redis is not installed")
def test_get_redis_client():
    assert crontab.get_redis_client() is not None


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

    @pytest.mark.skipif(crontab.redis is None, reason="redis is not installed")
    def test_locked(self):
        with crontab.get_redis_client().lock("dramatiq-scheduler", blocking_timeout=0):
            with io.StringIO() as stderr:
                call_command("crontab", stderr=stderr)
                assert "Another scheduler is already running." in stderr.getvalue()

    def test_handle(self, monkeypatch):
        scheduler = Mock()
        monkeypatch.setattr(crontab, "scheduler", scheduler)
        with io.StringIO() as stdout:
            call_command("crontab", stdout=stdout)
            assert "Starting scheduler…" in stdout.getvalue()
        assert scheduler.start.called_once()

    def test_handle__keyboard_interrupt(self, monkeypatch):
        scheduler = Mock()
        scheduler.start.side_effect = KeyboardInterrupt()
        monkeypatch.setattr(crontab, "scheduler", scheduler)
        with io.StringIO() as stdout:
            call_command("crontab", stdout=stdout)
            assert "Shutting down scheduler…" in stdout.getvalue()
        assert scheduler.start.called_once()
        assert scheduler.shutdown.called_once()
