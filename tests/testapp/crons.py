"""Alternative crontab module for testing the CRONTAB_MODULE setting."""
import dramatiq
from dramatiq_crontab import cron


@cron("*/5 * * * *")
@dramatiq.actor
def my_task():
    my_task.logger.info("Hello Cron World!")
