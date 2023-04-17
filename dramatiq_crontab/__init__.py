"""Cron style scheduler for asynchronous Dramatiq tasks in Django."""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone

from . import _version

try:
    from sentry_sdk.crons import monitor
except ImportError:
    monitor = None

__version__ = _version.version
VERSION = _version.version_tuple


__all__ = ["cron", "scheduler"]


scheduler = BlockingScheduler()


def cron(schedule):
    """
    Run task on a scheduler with a cron schedule.

    Usage:
        @cron("0 0 * * *")
        @dramatiq.actor
        def cron_test():
            print("Cron test")


    Please don't forget to set up a sentry monitor for the actor, otherwise you won't
    get any notifications if the cron job fails.

    The monitor slug is your actor name, the schedule should be set to the same
    cron schedule as the cron decorator. The schedule type should be set to cron.
    The monitors timezone should be set to Europe/Berlin.
    """

    def decorator(func):
        *_, day_of_week = schedule.split(" ")

        if day_of_week.lower() not in (
            "*",
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
            "sun",
        ):
            # CronTrigger uses Python's timezone dependent first weekday,
            # so in Berlin monday is 0 and sunday is 6. We use literals to avoid
            # confusion. Literals are also more readable and crontab conform.
            raise ValueError(
                "Please use a literal day of week (Mon, Tue, Wed, Thu, Fri, Sat, Sun) or *"
            )

        fn = getattr(func, "send")
        if monitor is not None:
            fn = monitor(func.actor_name)(fn)

        scheduler.add_job(
            fn,
            CronTrigger.from_crontab(
                schedule,
                timezone=timezone.get_default_timezone(),
            ),
            name=func.actor_name,
        )
        # We don't add the Sentry monitor on the actor itself, because we only want to
        # monitor the cron job, not the actor itself, or it's direct invocations.
        return func

    return decorator
