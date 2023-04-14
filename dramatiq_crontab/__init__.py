"""Cron style scheduler for asynchronous Dramatiq tasks in Django."""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from . import _version

try:
    from sentry_sdk.crons import monitor
except ImportError:
    monitor = None

__version__ = _version.version
VERSION = _version.version_tuple


__all__ = ["cron", "scheduler"]

try:
    from django.utils import timezone
except ImportError:
    timezone = None


__all__ = ["cron"]

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
        minute, hour, day_of_month, month, day_of_week = schedule.split(" ")

        try:
            day_of_week = {
                "mon": 0,
                "tue": 1,
                "wed": 2,
                "thu": 3,
                "fri": 4,
                "sat": 5,
                "sun": 6,
                "*": "*",
            }[day_of_week.lower()]
        except KeyError as e:
            # CronTrigger uses Python's timezone dependent first weekday,
            # so in Berlin monday is 0 and sunday is 6. We use literals to avoid
            # confusion. Literals are also more readable and crontab conform.
            raise ValueError(
                "Please use a literal day of week (Mon, Tue, Wed, Thu, Fri, Sat, Sun) or *"
            ) from e

        fn = getattr(func, "send")
        if monitor is not None:
            fn = monitor(func.actor_name)(fn)

        scheduler.add_job(
            fn,
            CronTrigger(
                hour=hour,
                minute=minute,
                day=day_of_month,
                month=month,
                day_of_week=day_of_week,
                timezone=timezone.get_default_timezone(),
            ),
            name=func.actor_name,
        )
        # We don't add the Sentry monitor on the actor itself, because we only want to
        # monitor the cron job, not the actor itself, or it's direct invocations.
        return func

    return decorator
