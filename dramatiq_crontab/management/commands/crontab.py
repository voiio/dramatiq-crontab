import importlib
import signal

from apscheduler.triggers.interval import IntervalTrigger
from django.apps import apps
from django.core.management import BaseCommand

from ... import conf, utils

try:
    from sentry_sdk import capture_exception
except ImportError:
    capture_exception = lambda e: None

from ... import scheduler


def kill_softly(signum, frame):
    """Raise a KeyboardInterrupt to stop the scheduler and release the lock."""
    raise KeyboardInterrupt("Received SIGTERM!")


class Command(BaseCommand):
    """Run dramatiq task scheduler for all tasks with the `cron` decorator."""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-task-loading",
            action="store_true",
            help="Don't load tasks from installed apps.",
        )
        parser.add_argument(
            "--no-heartbeat",
            action="store_true",
            help="Don't start the heartbeat actor.",
        )

    def handle(self, *args, **options):
        if not options["no_task_loading"]:
            self.load_tasks(options)
        if not options["no_heartbeat"]:
            importlib.import_module("dramatiq_crontab.tasks")
            self.stdout.write("Scheduling heartbeat.")
        try:
            if not isinstance(utils.lock, utils.FakeLock):
                self.stdout.write("Acquiring lock…")
            # Lock scheduler to prevent multiple instances from running.
            with utils.lock:
                self.launch_scheduler()
        except utils.LockError as e:
            capture_exception(e)
            self.stderr.write("Another scheduler is already running.")

    def launch_scheduler(self):
        signal.signal(signal.SIGTERM, kill_softly)
        self.stdout.write(self.style.SUCCESS("Starting scheduler…"))
        # Periodically extend TTL of lock if needed
        # https://redis-py.readthedocs.io/en/stable/lock.html#redis.lock.Lock.extend
        scheduler.add_job(
            utils.lock.extend,
            IntervalTrigger(seconds=conf.get_settings().LOCK_REFRESH_INTERVAL),
            args=(conf.get_settings().LOCK_TIMEOUT, True),
            name="dramatiq_crontab.utils.lock.extend",
        )
        try:
            scheduler.start()
        except KeyboardInterrupt as e:
            self.stdout.write(self.style.WARNING(str(e)))
            self.stdout.write(self.style.NOTICE("Shutting down scheduler…"))
            scheduler.shutdown()

    def load_tasks(self, options):
        """
        Load all tasks modules within installed apps.

        If they are not imported, they will not have registered
        their tasks with the scheduler.
        """
        for app in apps.get_app_configs():
            if app.name == "dramatiq_crontab":
                continue
            if app.ready:
                try:
                    importlib.import_module(f"{app.name}.tasks")
                    self.stdout.write(
                        f"Loaded tasks from {self.style.NOTICE(app.name)}."
                    )
                except ImportError:
                    pass
