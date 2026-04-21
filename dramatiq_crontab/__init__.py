"""Cron style scheduler for asynchronous Dramatiq tasks in Django."""

from unittest.mock import Mock

from apscheduler.schedulers.base import STATE_STOPPED
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone

from . import _version

try:
    from sentry_sdk.crons import monitor
except ImportError:
    monitor = None

__version__ = _version.version
VERSION = _version.version_tuple

__all__ = ["cron", "interval", "scheduler"]


class LazyBlockingScheduler(BlockingScheduler):
    """Avoid annoying info logs for pending jobs."""

    def add_job(self, *args, **kwargs):
        logger = self._logger
        if self.state == STATE_STOPPED:
            # We don't want to schedule jobs before the scheduler is started.
            self._logger = Mock()
        super().add_job(*args, **kwargs)
        self._logger = logger


scheduler = LazyBlockingScheduler()


def _interval_schedule(seconds):
    """Convert an interval in seconds to a Sentry monitor schedule, if expressible."""
    # Sentry also supports week/month/year, omitted as unrealistic for dramatiq intervals.
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size and seconds % size == 0:
            return {"type": "interval", "value": seconds // size, "unit": unit}
    return None


def cron(schedule):
    """
    Run task on a scheduler with a cron schedule.

    Usage:
        @cron("0 0 * * *")
        @dramatiq.actor
        def cron_test():
            print("Cron test")

    If ``sentry-sdk`` is installed, a Sentry cron monitor is automatically
    upserted on the first check-in using the actor name as the monitor slug.
    """

    def decorator(actor):
        *_, day_schedule = schedule.split(" ")

        # CronTrigger uses Python's timezone dependent first weekday,
        # so in Berlin monday is 0 and sunday is 6. We use literals to avoid
        # confusion. Literals are also more readable and crontab conform.
        if any(i.isdigit() for i in day_schedule):
            raise ValueError(
                "Please use a literal day of week (Mon, Tue, Wed, Thu, Fri, Sat, Sun) or *"
            )

        if monitor is not None:
            monitor_config = {
                "schedule": {"type": "crontab", "value": schedule},
                "timezone": str(timezone.get_default_timezone()),
            }
            actor.fn = monitor(
                actor.actor_name, monitor_config=monitor_config
            )(actor.fn)

        scheduler.add_job(
            actor.send,
            CronTrigger.from_crontab(
                schedule,
                timezone=timezone.get_default_timezone(),
            ),
            name=actor.actor_name,
        )
        # We don't add the Sentry monitor on the actor itself, because we only want to
        # monitor the cron job, not the actor itself, or it's direct invocations.
        return actor

    return decorator


def interval(*, seconds):
    """
    Run task on a periodic interval.

    Usage:
        @interval(seconds=30)
        @dramatiq.actor
        def interval_test():
            print("Interval test")

    Please note that the interval is relative to the time the scheduler is started. For
    example, if you start the scheduler at 12:00:00, the first run will be at 12:00:30.
    However, if you restart the scheduler at 12:00:15, the first run will be at
    12:00:45.

    For an interval that is consistent with the clock, use the `cron` decorator instead.

    If ``sentry-sdk`` is installed, a Sentry cron monitor is automatically
    upserted on the first check-in using the actor name as the monitor slug.
    Sub-minute intervals skip the auto-upsert (Sentry's smallest unit is minute)
    and fall back to check-ins only.
    """

    def decorator(actor):
        if monitor is not None:
            monitor_kwargs = {}
            schedule = _interval_schedule(seconds)
            if schedule is not None:
                monitor_kwargs["monitor_config"] = {
                    "schedule": schedule,
                    "timezone": str(timezone.get_default_timezone()),
                }
            actor.fn = monitor(actor.actor_name, **monitor_kwargs)(actor.fn)

        scheduler.add_job(
            actor.send,
            IntervalTrigger(
                seconds=seconds,
                timezone=timezone.get_default_timezone(),
            ),
            name=actor.actor_name,
        )
        return actor

    return decorator
