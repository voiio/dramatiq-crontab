import datetime
from unittest import mock

import dramatiq_crontab
import pytest
from django.utils.timezone import make_aware
from dramatiq_crontab import interval, scheduler, tasks


def test_heartbeat(caplog):
    with caplog.at_level("INFO"):
        tasks.heartbeat()
    assert "ﮩ٨ـﮩﮩ٨ـ♡ﮩ٨ـﮩﮩ٨ـ" in caplog.text


def test_cron__stars():
    assert not scheduler.remove_all_jobs()
    assert tasks.cron("* * * * *")(tasks.heartbeat)
    init = make_aware(datetime.datetime(2021, 1, 1, 0, 0, 0))
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(init, init) == make_aware(
        datetime.datetime(2021, 1, 1, 0, 1)
    )


def test_cron__day_of_week():
    assert not scheduler.remove_all_jobs()
    assert tasks.cron("* * * * Mon")(tasks.heartbeat)
    init = make_aware(datetime.datetime(2021, 1, 1, 0, 0, 0))  # Friday
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(init, init) == make_aware(
        datetime.datetime(2021, 1, 4, 0, 0)
    )


@pytest.mark.parametrize(
    "schedule",
    [
        "0 0 * * Tue-Wed",
        "0 0 * * Tue,Wed",
    ],
)
def test_cron_day_range(schedule):
    assert not scheduler.remove_all_jobs()
    assert tasks.cron(schedule)(tasks.heartbeat)
    init = make_aware(datetime.datetime(2021, 1, 1, 0, 0, 0))  # Friday
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(init, init) == make_aware(
        datetime.datetime(2021, 1, 5, 0, 0)
    )
    init = make_aware(datetime.datetime(2021, 1, 5, 0, 0, 0))  # Tuesday
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(init, init) == make_aware(
        datetime.datetime(2021, 1, 6, 0, 0)
    )


def test_cron__every_15_minutes():
    assert not scheduler.remove_all_jobs()
    assert tasks.cron("*/15 * * * *")(tasks.heartbeat)
    init = make_aware(datetime.datetime(2021, 1, 1, 0, 0, 0))
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(init, init) == make_aware(
        datetime.datetime(2021, 1, 1, 0, 15)
    )


@pytest.mark.parametrize(
    "schedule",
    [
        "* * * * 1",
        "* * * * 2-3",
        "* * * * 1,7",
    ],
)
def test_cron__error(schedule):
    assert not scheduler.remove_all_jobs()
    with pytest.raises(ValueError) as e:
        tasks.cron(schedule)(tasks.heartbeat)
    assert (
        "Please use a literal day of week (Mon, Tue, Wed, Thu, Fri, Sat, Sun) or *"
        in str(e.value)
    )


def test_interval__seconds():
    assert not scheduler.remove_all_jobs()
    assert interval(seconds=30)(tasks.heartbeat)
    init = make_aware(datetime.datetime(2021, 1, 1, 0, 0, 0))
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(init, init) == make_aware(
        datetime.datetime(2021, 1, 1, 0, 0, 30)
    )


def _fake_monitor():
    fake = mock.MagicMock()
    fake.return_value = lambda fn: fn
    return fake


def test_cron__sentry_monitor_config(monkeypatch):
    assert not scheduler.remove_all_jobs()
    fake = _fake_monitor()
    monkeypatch.setattr(dramatiq_crontab, "monitor", fake)
    tasks.cron("0 2 * * *")(tasks.heartbeat)
    fake.assert_called_once()
    args, kwargs = fake.call_args
    assert args == (tasks.heartbeat.actor_name,)
    assert kwargs["monitor_config"]["schedule"] == {
        "type": "crontab",
        "value": "0 2 * * *",
    }
    assert kwargs["monitor_config"]["timezone"]


def test_interval__sentry_monitor_config_minute(monkeypatch):
    assert not scheduler.remove_all_jobs()
    fake = _fake_monitor()
    monkeypatch.setattr(dramatiq_crontab, "monitor", fake)
    interval(seconds=300)(tasks.heartbeat)
    fake.assert_called_once()
    _, kwargs = fake.call_args
    assert kwargs["monitor_config"]["schedule"] == {
        "type": "interval",
        "value": 5,
        "unit": "minute",
    }


def test_interval__sentry_monitor_config_hour(monkeypatch):
    assert not scheduler.remove_all_jobs()
    fake = _fake_monitor()
    monkeypatch.setattr(dramatiq_crontab, "monitor", fake)
    interval(seconds=3600)(tasks.heartbeat)
    fake.assert_called_once()
    _, kwargs = fake.call_args
    assert kwargs["monitor_config"]["schedule"] == {
        "type": "interval",
        "value": 1,
        "unit": "hour",
    }


def test_interval__sentry_no_config_for_sub_minute(monkeypatch):
    assert not scheduler.remove_all_jobs()
    fake = _fake_monitor()
    monkeypatch.setattr(dramatiq_crontab, "monitor", fake)
    interval(seconds=30)(tasks.heartbeat)
    fake.assert_called_once()
    _, kwargs = fake.call_args
    assert "monitor_config" not in kwargs


def test_cron__sentry_not_installed(monkeypatch):
    assert not scheduler.remove_all_jobs()
    monkeypatch.setattr(dramatiq_crontab, "monitor", None)
    assert tasks.cron("0 2 * * *")(tasks.heartbeat)


def test_interval__sentry_not_installed(monkeypatch):
    assert not scheduler.remove_all_jobs()
    monkeypatch.setattr(dramatiq_crontab, "monitor", None)
    assert interval(seconds=30)(tasks.heartbeat)
