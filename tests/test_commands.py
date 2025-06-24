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
            with pytest.raises(utils.LockError):
                call_command("crontab")

    def test_locked_no_refresh(self, monkeypatch):
        """A lock was acquired, but it was not refreshed."""
        pytest.importorskip("redis", reason="redis is not installed")
        scheduler = Mock()
        monkeypatch.setattr(crontab.settings, "LOCK_AUTORETRY", True, raising=False)
        monkeypatch.setattr(crontab.time, "sleep", lambda _: None)
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

    def test_locked_autoretry(self, monkeypatch):
        """Scheduler keeps retrying to get the lock when autoretry = True."""
        pytest.importorskip("redis", reason="redis is not installed")
        lock = utils.redis_client.lock("dramatiq-scheduler", blocking_timeout=0)
        lock.acquire()  # ensure first attempt fails
        monkeypatch.setattr(crontab.settings, "LOCK_AUTORETRY", True, raising=False)
        monkeypatch.setattr(
            crontab.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt())
        )
        monkeypatch.setattr(crontab, "scheduler", Mock())  # prevent real start
        with pytest.raises(KeyboardInterrupt):
            call_command("crontab")
        lock.release()

    def test_extend_lock_error_retry(self, monkeypatch):
        """When `extend` fails, the command retries while LOCK_AUTORETRY=True."""
        # enable autoretry and short-circuit the sleep-call so the loop exits
        monkeypatch.setattr(crontab.settings, "LOCK_AUTORETRY", True, raising=False)
        monkeypatch.setattr(
            crontab.time,
            "sleep",
            lambda _: (_ for _ in ()).throw(KeyboardInterrupt()),
        )

        # lock whose `extend` always fails
        class DummyLock(utils.FakeLock):
            def extend(self, *_, **__):
                raise utils.LockError("lost lock")

        monkeypatch.setattr(utils, "lock", DummyLock())

        # scheduler that immediately runs the extension job once
        class DummyScheduler:
            def __init__(self):
                self._jobs = []

            def add_job(self, func, *args, **kwargs):  # noqa: D401
                self._jobs.append(func)

            def start(self):
                for job in self._jobs:
                    job()  # triggers DummyLock.extend → LockError

            def shutdown(self, wait=True):
                pass

        monkeypatch.setattr(crontab, "scheduler", DummyScheduler())

        # command should retry (→ sleep) and the patched sleep raises KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            call_command("crontab")


def test_locked_no_autoretry(monkeypatch):
    """Lock acquisition fails while LOCK_AUTORETRY=False → LockError must bubble up."""

    # lock that always fails to acquire
    class DummyLock(utils.FakeLock):
        def __enter__(self):
            raise utils.LockError("already locked")  # triggers the except-branch

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False  # propagate exception

    # make the command use the dummy lock and disable autoretry
    monkeypatch.setattr(utils, "lock", DummyLock())
    monkeypatch.setattr(crontab.settings, "LOCK_AUTORETRY", False, raising=False)

    # the command must raise the LockError immediately
    with pytest.raises(utils.LockError):
        call_command("crontab")
