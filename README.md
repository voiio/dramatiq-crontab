# Dramatiq Crontab

![dramtiq-crontab logo: person in front of a schedule](https://raw.githubusercontent.com/voiio/dramatiq-crontab/main/dramatiq-crontab.png)

**Cron style scheduler for asynchronous Dramatiq tasks in Django.**

* setup recurring tasks via crontab syntax
* lightweight helpers build on robust tools like [Dramatiq][dramatiq] and [APScheduler][apscheduler]
* [Sentry][sentry] cron monitor support

[![PyPi Version](https://img.shields.io/pypi/v/dramatiq-crontab.svg)](https://pypi.python.org/pypi/dramatiq-crontab/)
[![Test Coverage](https://codecov.io/gh/voiio/dramatiq-crontab/branch/main/graph/badge.svg)](https://codecov.io/gh/voiio/dramatiq-crontab)
[![GitHub License](https://img.shields.io/github/license/voiio/dramatiq-crontab)](https://raw.githubusercontent.com/voiio/dramatiq-crontab/master/LICENSE)

## Setup

You need to have [Dramatiq][dramatiq] installed and setup properly.

```ShellSession
python3 -m pip install dramatiq-crontab
# or
python3 -m pip install dramatiq-crontab[sentry]  # with sentry cron monitor support
```

Add `dramatiq_crontab` to your `INSTALLED_APPS` in `settings.py`:

```python
# settings.py
INSTALLED_APPS = [
    'dramatiq_crontab',
    # ...
]
```

Finally, you lauch the scheduler in a separate process:

```ShellSession
python3 manage.py crontab
```

### Setup Redis as a lock backend (optional)

If you use Redis as a broker, you can use Redis as a lock backend as well.
The lock backend is used to prevent multiple instances of the scheduler
from running at the same time. This is important if you have multiple
instances of your application running.

```python
# settings.py
DRAMATIQ_CRONTAB = {
    "REDIS_URL": "redis://localhost:6379/0",
}
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

### Interval

If you want to run a task more frequently than once a minute, you can use the
`interval` decorator.

```python
# tasks.py
import dramatiq
from dramatiq_crontab import interval


@interval(seconds=30)
@dramatiq.actor
def my_task():
    my_task.logger.info("Hello World")
```

Please note that the interval is relative to the time the scheduler is started.
For example, if you start the scheduler at 12:00:00, the first run will be at
12:00:30. However, if you restart the scheduler at 12:00:15, the first run will
be at 12:00:45.

### Sentry Cron Monitors

If you use [Sentry][sentry] you can add cron monitors to your tasks.
The monitor's slug will be the actor's name. Like `my_task` in the example above.

### The crontab command

```ShellSession
$ python3 manage.py crontab --help
usage: manage.py crontab [-h] [--no-task-loading] [--no-heartbeat] [--version] [-v {0,1,2,3}]
                         [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color]
                         [--force-color] [--skip-checks]

Run dramatiq task scheduler for all tasks with the `cron` decorator.

options:
  -h, --help            show this help message and exit
  --no-task-loading     Don't load tasks from installed apps.
  --no-heartbeat        Don't start the heartbeat actor.
```

[dramatiq]: https://dramatiq.io/
[apscheduler]: https://apscheduler.readthedocs.io/en/stable/
[sentry]: https://docs.sentry.io/product/crons/
