from threading import Event, Thread
from unittest.mock import Mock

import pytest
from apscheduler.events import EVENT_JOB_ERROR
from dramatiq_crontab import LazyBlockingScheduler, utils


def test_extend_lock():
    lock = Mock()
    scheduler = Mock()
    utils.extend_lock(lock, scheduler)
    assert lock.extend.call_count == 1
    assert scheduler.shutdown.call_count == 0


def test_extend_lock__error():
    lock = Mock()
    lock.extend.side_effect = utils.LockError()
    scheduler = Mock()
    with pytest.raises(utils.LockError):
        utils.extend_lock(lock, scheduler)
    assert lock.extend.call_count == 1
    assert scheduler.shutdown.call_count == 1


def test_extend_lock__lost_lock_stops_scheduler():
    lock = Mock()
    error = utils.LockNotOwnedError("Lock ownership lost")
    lock.extend.side_effect = error
    scheduler = LazyBlockingScheduler()
    job_finished = Event()
    errors = []

    def record_error(event):
        errors.append(event.exception)
        job_finished.set()

    scheduler.add_listener(record_error, EVENT_JOB_ERROR)
    scheduler.add_job(
        utils.extend_lock, "interval", seconds=0.01, args=(lock, scheduler)
    )
    thread = Thread(target=scheduler.start, daemon=True)
    thread.start()
    try:
        assert job_finished.wait(timeout=3), "Lock refresh job did not finish"
        thread.join(timeout=3)
        assert not thread.is_alive(), "Blocking scheduler did not terminate"
        assert not scheduler.running
        assert errors == [error]
        lock.extend.assert_called_once()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        # A failed shutdown can leave the blocking loop asleep.
        scheduler.wakeup()
        thread.join(timeout=3)


class TestFakeLock:
    def test_enter(self):
        fake_lock = utils.FakeLock()
        assert fake_lock.__enter__() is fake_lock

    def test_exit(self):
        fake_lock = utils.FakeLock()
        assert fake_lock.__exit__(None, None, None) is None

    def test_extend(self):
        fake_lock = utils.FakeLock()
        assert fake_lock.extend(additional_time=10, replace_ttl=True)
