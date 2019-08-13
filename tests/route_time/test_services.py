from unittest.mock import MagicMock, patch
import sys;

import pytest

print(sys.path)
from route_time.bot import services


def _check_response_with_error(res):
    res = services.list_routes(1)
    res_data, res_error = res
    assert res_data == []
    assert res_error


@pytest.fixture
def error_response():
    return MagicMock(
        json=MagicMock(return_value={'error': 'Not found'})
    )


@pytest.fixture
def empty_response():
    return MagicMock(
        json=MagicMock(return_value={'result': {'routes': []}})
    )


def test_list_routes_not_found(error_response, empty_response):
    with patch('requests.get', return_value=error_response()):
        res = services.list_routes(1)
        res_data, res_error = res
        assert res_data == []
        assert res_error

    with patch('requests.get', return_value=empty_response()):
        res = services.list_routes(1)
        _check_response_with_error(res)
