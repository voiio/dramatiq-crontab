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

_jobs = []


def _schedule_jobs():
    for args, kwargs in _jobs:
        scheduler.add_job(*args, **kwargs)


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
            actor.fn = monitor(actor.actor_name)(actor.fn)

        _jobs.append(
            (
                (
                    actor.send,
                    CronTrigger.from_crontab(
                        schedule,
                        timezone=timezone.get_default_timezone(),
                    ),
                ),
                {
                    "name": actor.actor_name,
                },
            )
        )
        # We don't add the Sentry monitor on the actor itself, because we only want to
        # monitor the cron job, not the actor itself, or it's direct invocations.
        return actor

    return decorator
