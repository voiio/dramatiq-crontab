import datetime

import pytest
from crontask import interval, scheduler, tasks
from django.utils.timezone import make_aware


def test_heartbeat(caplog):
    with caplog.at_level("INFO"):
        tasks.heartbeat.func()
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
