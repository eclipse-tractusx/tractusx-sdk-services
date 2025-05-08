"""Tests for the DT Pull Service's DTR endpoints
"""

from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.parametrize(
    'params,expected',
    [
        ({
            'dataplane_url': 'localhost',
         },
         {'test': 'example'})
    ]
)
def test_get_shell_descriptors(test_client, params, expected):
    """Should return the returned value of the shell_descriptor request."""

    handler_mock = MagicMock()
    handler_mock.dtr_find_shell_descriptor.return_value = expected

    with patch('dt_pull_service.api.dtr.get_dtr_handler', return_value=handler_mock):
        response = test_client.get('/dtr/shell-descriptors/',
                                   params=params)

    assert response.status_code == 200
    assert response.json() == expected
