from dramatiq_crontab.conf import get_settings

if redis_url := get_settings().REDIS_URL:
    import redis
    from redis.exceptions import LockError  # noqa

    redis_client = redis.Redis.from_url(redis_url)
    lock = redis_client.lock("dramatiq-scheduler", blocking_timeout=0)
else:

    class FakeLock:
        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class LockError(Exception):
        pass

    lock = FakeLock()

__all__ = ["LockError", "lock"]
