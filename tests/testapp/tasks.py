from crontask import cron
from django.tasks import task


@cron("*/5 * * * *")
@task
def my_task():
    my_task.logger.info("Hello World!")
