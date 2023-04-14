# Dramatiq Crontab

![dramtiq-crontab logo: person in front of a schedule](https://raw.githubusercontent.com/voiio/dramatiq-crontab/main/dramatiq-crontab.png)

Cron style scheduler for asynchronous Dramatiq tasks in Django.

* setup recurring tasks via crontab syntax
* lightweight helpers build on robust tools like [Dramatiq][dramatiq] and [APScheduler][apscheduler]
* [Sentry][sentry] monitor support

[dramatiq]: https://dramatiq.io/
[apscheduler]: https://apscheduler.readthedocs.io/en/stable/
[sentry]: https://sentry.io/


[![PyPi Version](https://img.shields.io/pypi/v/dramatiq-crontab.svg)](https://pypi.python.org/pypi/dramatiq-crontab/)
[![Test Coverage](https://codecov.io/gh/voiio/dramatiq-crontab/branch/main/graph/badge.svg)](https://codecov.io/gh/voiio/dramatiq-crontab)
[![GitHub License](https://img.shields.io/github/license/voiio/dramatiq-crontab)](https://raw.githubusercontent.com/voiio/dramatiq-crontab/master/LICENSE)

## Setup

```ShellSession
python3 -m pip install dramatiq-crontab
# or
python3 -m pip install dramatiq-crontab[django]  # with django support
# or
python3 -m pip install dramatiq-crontab[sentry]  # with sentry support
```

If you use Django:

```python
# settings.py
INSTALLED_APPS = [
    'dramatiq_crontab',
    # ...
]
```

## Usage

```python
# tasks.py
import dramatiq
from dramatiq_crontab import cron


@cron("*/5 * * * *")  # every 5 minutes
@dramatiq.actor
def my_task():
    my_task.logger.info("Hello World")
```
