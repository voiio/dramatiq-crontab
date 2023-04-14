import importlib
import signal

from django.apps import apps
from django.core.cache import cache
from django.core.management import BaseCommand
from redis.exceptions import LockError

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
            "--no-sentry",
            action="store_true",
            help="Don't capture exceptions with sentry.",
        )
        parser.add_argument(
            "--no-redis-lock",
            action="store_true",
            help="Don't lock scheduler to prevent multiple instances from running.",
        )
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
        if options["no_sentry"]:
            capture_exception = lambda e: None
        if not options["no_task_loading"]:
            self.load_tasks(options)
        try:
            # Lock scheduler to prevent multiple instances from running.
            with cache._cache.get_client().lock(
                "dramatiq-scheduler", blocking_timeout=0
            ):
                signal.signal(signal.SIGTERM, kill_softly)
                self.stdout.write(self.style.SUCCESS("Starting scheduler…"))
                try:
                    scheduler.start()
                except KeyboardInterrupt as e:
                    self.stdout.write(self.style.WARNING(str(e)))
                    self.stdout.write(self.style.NOTICE("Shutting down scheduler…"))
                    scheduler.shutdown()
        except LockError as e:
            capture_exception(e)
            self.stderr.write("Another scheduler is already running.")

    def load_tasks(self, options):
        """
        Load all tasks modules within installed apps.

        If they are not imported, they will not have registered
        their tasks with the scheduler.
        """
        for app in apps.get_app_configs():
            if options["no_heartbeat"] and app.name == "dramatiq_crontab":
                continue
            if app.ready:
                try:
                    importlib.import_module(f"{app.name}.tasks")
                    self.stdout.write(
                        f"Loaded tasks from {self.style.NOTICE(app.name)}."
                    )
                except ImportError:
                    pass
