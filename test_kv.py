import unittest
from unittest.mock import patch, MagicMock
import json
import os
import utils.kv

class TestKV(unittest.TestCase):

    @patch('utils.kv.KV_REST_API_URL', '')
    @patch('utils.kv.KV_REST_API_TOKEN', '')
    def test_kv_set_missing_env_vars(self):
        result = utils.kv.kv_set("test_key", "test_value")
        self.assertFalse(result)

    @patch('utils.kv.KV_REST_API_URL', 'http://test.url')
    @patch('utils.kv.KV_REST_API_TOKEN', 'test_token')
    @patch('utils.kv.requests.post')
    def test_kv_set_success_no_ex(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = utils.kv.kv_set("test_key", "test_value")
        self.assertTrue(result)

        mock_post.assert_called_once_with(
            'http://test.url',
            headers={"Authorization": "Bearer test_token", "Content-Type": "application/json"},
            json=["SET", "test_key", json.dumps("test_value")],
            timeout=5
        )

    @patch('utils.kv.KV_REST_API_URL', 'http://test.url/') # test strip
    @patch('utils.kv.KV_REST_API_TOKEN', 'test_token')
    @patch('utils.kv.requests.post')
    def test_kv_set_success_with_ex(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = utils.kv.kv_set("test_key", "test_value", ex=60)
        self.assertTrue(result)

        mock_post.assert_called_once_with(
            'http://test.url',
            headers={"Authorization": "Bearer test_token", "Content-Type": "application/json"},
            json=["SET", "test_key", json.dumps("test_value"), "EX", "60"],
            timeout=5
        )

    @patch('utils.kv.KV_REST_API_URL', 'http://test.url')
    @patch('utils.kv.KV_REST_API_TOKEN', 'test_token')
    @patch('utils.kv.requests.post')
    def test_kv_set_failure_status_code(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        result = utils.kv.kv_set("test_key", "test_value")
        self.assertFalse(result)

    @patch('utils.kv.KV_REST_API_URL', 'http://test.url')
    @patch('utils.kv.KV_REST_API_TOKEN', 'test_token')
    @patch('utils.kv.requests.post')
    def test_kv_set_exception(self, mock_post):
        mock_post.side_effect = Exception("Test Exception")

        result = utils.kv.kv_set("test_key", "test_value")
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
