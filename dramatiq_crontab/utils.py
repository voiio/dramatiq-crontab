from dramatiq_crontab.conf import get_settings

__all__ = ["LockError", "lock"]


class FakeLock:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def extend(self, additional_time=None, replace_ttl=False):
        pass


if redis_url := get_settings().REDIS_URL:
    import redis
    from redis.exceptions import LockError, LockNotOwnedError  # noqa

    redis_client = redis.Redis.from_url(redis_url)
    lock = redis_client.lock(
        "dramatiq-scheduler",
        blocking_timeout=get_settings().LOCK_BLOCKING_TIMEOUT,
        timeout=get_settings().LOCK_TIMEOUT,
        thread_local=False,
    )
else:

    class LockError(Exception):
        pass

    class LockNotOwnedError(LockError):
        pass

    lock = FakeLock()


def extend_lock(lock, scheduler):
    """Extend the lock for a scheduler or shut it down."""
    try:
        lock.extend(get_settings().LOCK_TIMEOUT, True)
    except LockError:
        scheduler.shutdown()
        raise
