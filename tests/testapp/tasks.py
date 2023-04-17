import dramatiq

from dramatiq_crontab import cron


@cron("*/5 * * * *")
@dramatiq.actor
def my_task():
    my_task.logger.info("Hello World!")
