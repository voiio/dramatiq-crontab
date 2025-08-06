from unittest.mock import Mock

import pytest
from dramatiq_crontab import utils


def test_extend_lock():
    lock = Mock()
    scheduler = Mock()
    utils.extend_lock(lock, scheduler)
    assert lock.extend.call_count == 1
    assert scheduler.shutdown.call_count == 0


def test_extend_lock__error():
    lock = Mock()
    lock.extend.side_effect = utils.LockError()
    scheduler = Mock()
    with pytest.raises(utils.LockError):
        utils.extend_lock(lock, scheduler)
    assert lock.extend.call_count == 1
    assert scheduler.shutdown.call_count == 1


class TestFakeLock:
    def test_enter(self):
        fake_lock = utils.FakeLock()
        assert fake_lock.__enter__() is fake_lock

    def test_exit(self):
        fake_lock = utils.FakeLock()
        assert fake_lock.__exit__(None, None, None) is None

    def test_extend(self):
        fake_lock = utils.FakeLock()
        assert fake_lock.extend(additional_time=10, replace_ttl=True)
