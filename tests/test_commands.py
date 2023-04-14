import io

import pytest
from django.core.management import call_command

from dramatiq_crontab.management.commands.crontab import (
    get_redis_client,
    kill_softly,
    redis,
)


def test_kill_softly():
    with pytest.raises(KeyboardInterrupt):
        kill_softly(None, None)


def test_get_redis_client__none(settings):
    settings.DRAMATIQ_CRONTAB = {}
    assert get_redis_client() is None


@pytest.mark.skipif(redis is None, reason="redis is not installed")
def test_get_redis_client():
    assert get_redis_client() is not None


class TestCrontab:
    @pytest.fixture(autouse=True)
    def patch_launch(self, monkeypatch):
        monkeypatch.setattr(
            "dramatiq_crontab.management.commands.crontab.Command.launch_scheduler",
            lambda s: None,
        )

    def test_default(self):
        with io.StringIO() as stdout:
            call_command("crontab", stdout=stdout)
            assert "Loaded tasks from tests.testapp." in stdout.getvalue()
            assert "Scheduling heartbeat." in stdout.getvalue()

    def test_no_task_loading(self):
        with io.StringIO() as stdout:
            call_command("crontab", "--no-task-loading", stdout=stdout)
            assert "Loaded tasks from tests.testapp." not in stdout.getvalue()
            assert "Scheduling heartbeat." in stdout.getvalue()

    def test_no_heartbeat(self):
        with io.StringIO() as stdout:
            call_command("crontab", "--no-heartbeat", stdout=stdout)
            assert "Loaded tasks from tests.testapp." in stdout.getvalue()
            assert "Scheduling heartbeat." not in stdout.getvalue()

    @pytest.mark.skipif(redis is None, reason="redis is not installed")
    def test_locked(self):
        with get_redis_client().lock("dramatiq-scheduler", blocking_timeout=0):
            with io.StringIO() as stderr:
                call_command("crontab", stderr=stderr)
                assert "Another scheduler is already running." in stderr.getvalue()
