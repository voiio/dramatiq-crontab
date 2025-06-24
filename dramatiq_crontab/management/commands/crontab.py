import importlib
import signal
import time

from apscheduler.triggers.interval import IntervalTrigger
from django.apps import apps
from django.core.management import BaseCommand

from ... import conf, utils

settings = conf.get_settings()

try:
    from sentry_sdk import capture_exception
except ImportError:
    capture_exception = lambda e: None  # noqa: E731

from ... import scheduler


def kill_softly(signum, frame):
    """Raise a KeyboardInterrupt to stop the scheduler and release the lock."""
    signame = signal.Signals(signum).name
    raise KeyboardInterrupt(f"Received {signame} ({signum}), shutting down…")


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
        autoretry = settings.LOCK_AUTORETRY
        while True:
            try:
                if not isinstance(utils.lock, utils.FakeLock):
                    self.stdout.write("Acquiring lock…")
                with utils.lock:
                    self.launch_scheduler()
                return  # graceful stop
            except utils.LockError:
                if not autoretry:
                    raise
                self.stderr.write("Failed to acquire or lost lock – retrying…")
                time.sleep(settings.LOCK_REFRESH_INTERVAL)

    def launch_scheduler(self):
        signal.signal(signal.SIGHUP, kill_softly)
        signal.signal(signal.SIGTERM, kill_softly)
        signal.signal(signal.SIGINT, kill_softly)
        self.stdout.write(self.style.SUCCESS("Starting scheduler…"))
        self._lost_lock_exc = None

        def _extend_lock():
            try:
                utils.lock.extend(settings.LOCK_TIMEOUT, replace_ttl=True)
            except utils.LockError as exc:
                self._lost_lock_exc = exc
                scheduler.shutdown(wait=False)

        scheduler.add_job(
            _extend_lock,
            IntervalTrigger(seconds=settings.LOCK_REFRESH_INTERVAL),
            id="dramatiq_crontab_lock_extend",
            replace_existing=True,
            name="dramatiq_crontab.utils.lock.extend",
        )
        try:
            scheduler.start()
        except KeyboardInterrupt as e:
            self.stdout.write(self.style.WARNING(str(e)))
            self.stdout.write(self.style.NOTICE("Shutting down scheduler…"))
            scheduler.shutdown()
        if self._lost_lock_exc:
            raise self._lost_lock_exc

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
