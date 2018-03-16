from __future__ import absolute_import

import mock

import pytest

from requests_core.http_manager import HTTPConnectionPool
from requests_core.http_manager.exceptions import EmptyPoolError
from requests_core.http_manager.packages.six.moves import queue


class BadError(Exception):
    """
    This should not be raised.
    """
    pass


class TestMonkeypatchResistance(object):
    """
    Test that connection pool works even with a monkey patched Queue module,
    see obspy/obspy#1599, kennethreitz/requests#3742, shazow/urllib3#1061.
    """
    def test_queue_monkeypatching(self):
        with mock.patch.object(queue, 'Empty', BadError):
            with HTTPConnectionPool(host="localhost", block=True) as http:
                http._get_conn(timeout=1)
                with pytest.raises(EmptyPoolError):
                    http._get_conn(timeout=1)
