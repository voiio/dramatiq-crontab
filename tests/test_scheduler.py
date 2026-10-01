import threading

import pytest
from apscheduler.events import EVENT_SCHEDULER_STARTED
from apscheduler.jobstores.base import ConflictingIdError
from dramatiq_crontab import LazyBlockingScheduler


def test_add_pending_job(caplog):
    scheduler = LazyBlockingScheduler()
    with caplog.at_level("INFO", logger="apscheduler.scheduler"):
        job = scheduler.add_job(lambda: None, "interval", seconds=30, id="task")

    assert caplog.messages == []
    assert job is scheduler.get_job("task")
    job.modify(name="renamed task")
    assert scheduler.get_job("task").name == "renamed task"
    with caplog.at_level("INFO", logger="apscheduler.scheduler"):
        job.remove()
    assert "Removed job task" in caplog.messages
    assert scheduler.get_jobs() == []


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"func": None}, TypeError),
        ({"func": lambda: None, "trigger": "unknown"}, LookupError),
    ],
)
def test_failed_registration_preserves_logging(options, error, caplog):
    scheduler = LazyBlockingScheduler()
    with caplog.at_level("INFO", logger="apscheduler.scheduler"):
        with pytest.raises(error):
            scheduler.add_job(**options)
        scheduler.add_job(lambda: None, id="task")
        scheduler.remove_job("task")

    assert "Removed job task" in caplog.messages
    assert scheduler.get_jobs() == []


def test_add_job_after_start(caplog):
    scheduler = LazyBlockingScheduler()
    started = threading.Event()
    scheduler.add_listener(lambda event: started.set(), EVENT_SCHEDULER_STARTED)
    thread = threading.Thread(target=scheduler.start, kwargs={"paused": True})
    thread.start()
    try:
        assert started.wait(5)
        with caplog.at_level("INFO", logger="apscheduler.scheduler"):
            job = scheduler.add_job(lambda: None, id="task", next_run_time=None)
            assert job is scheduler.get_job("task")
            with pytest.raises(ConflictingIdError):
                scheduler.add_job(lambda: None, id="task", next_run_time=None)
            job.remove()

        assert any(message.startswith("Added job ") for message in caplog.messages)
        assert "Removed job task" in caplog.messages
        assert scheduler.get_jobs() == []
    finally:
        scheduler.shutdown()
        thread.join(5)
        assert not thread.is_alive()
