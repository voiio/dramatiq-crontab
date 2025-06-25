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
