import dramatiq

from . import cron


@cron("* * * * *")
@dramatiq.actor
def heartbeat():
    heartbeat.logger.info("ﮩ٨ـﮩﮩ٨ـ♡ﮩ٨ـﮩﮩ٨ـ")
