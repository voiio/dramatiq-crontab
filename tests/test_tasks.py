import datetime

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

import pytest

from dramatiq_crontab import scheduler, tasks


def test_heartbeat(caplog):
    with caplog.at_level("INFO"):
        tasks.heartbeat()
    assert "ﮩ٨ـﮩﮩ٨ـ♡ﮩ٨ـﮩﮩ٨ـ" in caplog.text


def test_cron__stars():
    assert not scheduler.remove_all_jobs()
    assert tasks.cron("* * * * *")(tasks.heartbeat)
    init = datetime.datetime(2021, 1, 1, 0, 0, 0)
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(
        init, init
    ) == datetime.datetime(
        2021, 1, 1, 0, 1, tzinfo=zoneinfo.ZoneInfo(key="Europe/Berlin")
    )


def test_cron__day_of_week():
    assert not scheduler.remove_all_jobs()
    assert tasks.cron("* * * * Mon")(tasks.heartbeat)
    init = datetime.datetime(2021, 1, 1, 0, 0, 0)
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(
        init, init
    ) == datetime.datetime(
        2021, 1, 4, 0, 0, tzinfo=zoneinfo.ZoneInfo(key="Europe/Berlin")
    )


def test_cron__every_15_minutes():
    assert not scheduler.remove_all_jobs()
    assert tasks.cron("*/15 * * * *")(tasks.heartbeat)
    init = datetime.datetime(2021, 1, 1, 0, 0, 0)
    assert scheduler.get_jobs()[0].trigger.get_next_fire_time(
        init, init
    ) == datetime.datetime(
        2021, 1, 1, 0, 15, tzinfo=zoneinfo.ZoneInfo(key="Europe/Berlin")
    )


def test_cron__error():
    assert not scheduler.remove_all_jobs()
    with pytest.raises(ValueError) as e:
        tasks.cron("* * * * 1")(tasks.heartbeat)
    assert (
        "Please use a literal day of week (Mon, Tue, Wed, Thu, Fri, Sat, Sun) or *"
        in str(e.value)
    )
