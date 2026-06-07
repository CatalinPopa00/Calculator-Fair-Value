import pytest
from unittest.mock import patch, MagicMock
import os
import requests
import json

from utils.kv import kv_get

@patch('utils.kv.requests.post')
@patch('utils.kv.KV_REST_API_URL', 'http://test-url.com')
@patch('utils.kv.KV_REST_API_TOKEN', 'test-token')
def test_kv_get_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": '{"foo": "bar"}'}
    mock_post.return_value = mock_response

    result = kv_get("test_key")

    assert result == {"foo": "bar"}
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == 'http://test-url.com'
    assert kwargs['headers'] == {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }
    assert kwargs['json'] == ["GET", "test_key"]

@patch('utils.kv.requests.post')
@patch('utils.kv.KV_REST_API_URL', 'http://test-url.com')
@patch('utils.kv.KV_REST_API_TOKEN', 'test-token')
def test_kv_get_success_not_json(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": 'plain_string_result'}
    mock_post.return_value = mock_response

    result = kv_get("test_key")

    assert result == 'plain_string_result'
    mock_post.assert_called_once()

@patch('utils.kv.KV_REST_API_URL', None)
@patch('utils.kv.KV_REST_API_TOKEN', 'test-token')
def test_kv_get_missing_env_url():
    result = kv_get("test_key")
    assert result is None

@patch('utils.kv.KV_REST_API_URL', 'http://test-url.com')
@patch('utils.kv.KV_REST_API_TOKEN', None)
def test_kv_get_missing_env_token():
    result = kv_get("test_key")
    assert result is None

@patch('utils.kv.requests.post')
@patch('utils.kv.KV_REST_API_URL', 'http://test-url.com')
@patch('utils.kv.KV_REST_API_TOKEN', 'test-token')
def test_kv_get_missing_key(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": None}
    mock_post.return_value = mock_response

    result = kv_get("missing_key")

    assert result is None
    mock_post.assert_called_once()

@patch('utils.kv.requests.post')
@patch('utils.kv.KV_REST_API_URL', 'http://test-url.com')
@patch('utils.kv.KV_REST_API_TOKEN', 'test-token')
def test_kv_get_api_error(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    with pytest.raises(Exception, match="KV API Error: 500 - Internal Server Error"):
        kv_get("test_key")

    mock_post.assert_called_once()

@patch('utils.kv.requests.post')
@patch('utils.kv.KV_REST_API_URL', 'http://test-url.com')
@patch('utils.kv.KV_REST_API_TOKEN', 'test-token')
def test_kv_get_request_exception(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

    with pytest.raises(requests.exceptions.Timeout, match="Request timed out"):
        kv_get("test_key")

    mock_post.assert_called_once()
