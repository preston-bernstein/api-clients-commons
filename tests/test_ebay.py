"""Tests for api_clients_commons.ebay.

All HTTP calls are mocked — no test hits a live eBay endpoint. The
`network` marker is reserved for a future genuinely-live test, none exist
today.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api_clients_commons.ebay import client
from api_clients_commons.ebay.errors import EbayApiRequestFailed, EbayCredentialsMissing


@pytest.fixture(autouse=True)
def _reset_token_cache():
    client._reset_token_cache_for_tests()
    yield
    client._reset_token_cache_for_tests()


@pytest.fixture(autouse=True)
def _set_credentials(monkeypatch):
    monkeypatch.setenv("EBAY_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "test-client-secret")


# ---- URL parsing -----------------------------------------------------------


class TestExtractSearchTerm:
    def test_present(self):
        url = "https://www.ebay.com/sch/i.html?_nkw=corduroy+jacket"
        assert client._extract_search_term(url) == "corduroy jacket"

    def test_absent(self):
        url = "https://www.ebay.com/itm/123456789"
        assert client._extract_search_term(url) is None

    def test_multiple_values_takes_first(self):
        url = "https://www.ebay.com/sch/i.html?_nkw=first&_nkw=second"
        assert client._extract_search_term(url) == "first"

    def test_empty_value(self):
        url = "https://www.ebay.com/sch/i.html?_nkw="
        assert client._extract_search_term(url) is None


class TestExtractItemId:
    def test_plain(self):
        assert client._extract_item_id("https://www.ebay.com/itm/123456789") == "123456789"

    def test_with_slug(self):
        url = "https://www.ebay.com/itm/some-title-slug/123456789"
        assert client._extract_item_id(url) == "123456789"

    def test_no_marker(self):
        assert client._extract_item_id("https://www.ebay.com/sch/i.html") is None

    def test_non_digit_trailing_segment(self):
        assert client._extract_item_id("https://www.ebay.com/itm/not-a-number") is None

    def test_trailing_slash_empty_segment(self):
        assert client._extract_item_id("https://www.ebay.com/itm/123456789/") == "123456789"

    def test_marker_with_nothing_after(self):
        assert client._extract_item_id("https://www.ebay.com/itm/") is None


# ---- Credentials ------------------------------------------------------------


class TestRequireCredentials:
    def test_both_present(self, monkeypatch):
        monkeypatch.setenv("EBAY_CLIENT_ID", "id-value")
        monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret-value")
        assert client._require_credentials() == ("id-value", "secret-value")

    def test_id_missing(self, monkeypatch):
        monkeypatch.delenv("EBAY_CLIENT_ID", raising=False)
        with pytest.raises(EbayCredentialsMissing, match="EBAY_CLIENT_ID is unset or blank"):
            client._require_credentials()

    def test_secret_missing(self, monkeypatch):
        monkeypatch.delenv("EBAY_CLIENT_SECRET", raising=False)
        with pytest.raises(EbayCredentialsMissing, match="EBAY_CLIENT_SECRET is unset or blank"):
            client._require_credentials()

    def test_both_missing(self, monkeypatch):
        monkeypatch.delenv("EBAY_CLIENT_ID", raising=False)
        monkeypatch.delenv("EBAY_CLIENT_SECRET", raising=False)
        with pytest.raises(
            EbayCredentialsMissing, match="EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are unset or blank"
        ):
            client._require_credentials()

    def test_whitespace_only_is_blank(self, monkeypatch):
        monkeypatch.setenv("EBAY_CLIENT_ID", "   ")
        with pytest.raises(EbayCredentialsMissing, match="EBAY_CLIENT_ID"):
            client._require_credentials()

    def test_error_never_includes_values(self, monkeypatch):
        monkeypatch.delenv("EBAY_CLIENT_ID", raising=False)
        monkeypatch.setenv("EBAY_CLIENT_SECRET", "super-secret-value")
        try:
            client._require_credentials()
        except EbayCredentialsMissing as exc:
            assert "super-secret-value" not in str(exc)


# ---- Token caching -----------------------------------------------------------


def _token_response(access_token="tok-1", expires_in=7200):
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = {"access_token": access_token, "expires_in": expires_in}
    return resp


class TestGetToken:
    def test_fetches_fresh_token(self):
        with patch.object(client.requests, "post", return_value=_token_response("tok-fresh")) as mock_post:
            token = client._get_token(10.0)
        assert token == "tok-fresh"
        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == client._TOKEN_URL
        assert mock_post.call_args.kwargs["auth"] == ("test-client-id", "test-client-secret")

    def test_reuses_cached_token(self):
        with patch.object(client.requests, "post", return_value=_token_response("tok-a")) as mock_post:
            first = client._get_token(10.0)
            second = client._get_token(10.0)
        assert first == second == "tok-a"
        mock_post.assert_called_once()

    def test_expired_token_triggers_refetch(self):
        with patch.object(client.requests, "post", return_value=_token_response("tok-b", expires_in=100)):
            client._get_token(10.0)

        with patch.object(client, "time") as mock_time:
            mock_time.monotonic.return_value = 1_000_000.0
            with patch.object(client.requests, "post", return_value=_token_response("tok-c")) as mock_post:
                token = client._get_token(10.0)
        assert token == "tok-c"
        mock_post.assert_called_once()

    def test_connection_error_raises(self):
        import requests as real_requests

        with (
            patch.object(
                client.requests, "post", side_effect=real_requests.exceptions.ConnectionError("boom")
            ),
            pytest.raises(EbayApiRequestFailed) as exc_info,
        ):
            client._get_token(10.0)
        assert exc_info.value.status is None
        assert "boom" in exc_info.value.body

    def test_non_2xx_raises(self):
        resp = MagicMock(ok=False, status_code=401, text="unauthorized")
        with (
            patch.object(client.requests, "post", return_value=resp),
            pytest.raises(EbayApiRequestFailed) as exc_info,
        ):
            client._get_token(10.0)
        assert exc_info.value.status == 401
        assert exc_info.value.body == "unauthorized"

    def test_missing_credentials_raises_before_any_request(self, monkeypatch):
        monkeypatch.delenv("EBAY_CLIENT_ID", raising=False)
        with (
            patch.object(client.requests, "post") as mock_post,
            pytest.raises(EbayCredentialsMissing),
        ):
            client._get_token(10.0)
        mock_post.assert_not_called()


class TestInvalidateTokenCache:
    def test_invalidate_clears_cache(self):
        with patch.object(client.requests, "post", return_value=_token_response()):
            client._get_token(10.0)
        assert client._token_cache is not None
        client._invalidate_token_cache()
        assert client._token_cache is None

    def test_reset_for_tests_is_an_alias(self):
        with patch.object(client.requests, "post", return_value=_token_response()):
            client._get_token(10.0)
        client._reset_token_cache_for_tests()
        assert client._token_cache is None


# ---- search() / get_item() ---------------------------------------------------


def _browse_response(status_code=200, text='{"itemSummaries": []}'):
    resp = MagicMock()
    resp.ok = 200 <= status_code < 300
    resp.status_code = status_code
    resp.text = text
    return resp


class TestSearch:
    def test_calls_search_endpoint_with_query_param(self):
        with (
            patch.object(client.requests, "post", return_value=_token_response()),
            patch.object(client.requests, "get", return_value=_browse_response()) as mock_get,
        ):
            status, text = client.search("corduroy jacket", timeout_s=10.0)
        assert status == 200
        assert text == '{"itemSummaries": []}'
        assert mock_get.call_args.args[0] == client._SEARCH_URL
        assert mock_get.call_args.kwargs["params"] == {"q": "corduroy jacket"}

    def test_sends_bearer_and_marketplace_headers(self):
        with (
            patch.object(client.requests, "post", return_value=_token_response("tok-x")),
            patch.object(client.requests, "get", return_value=_browse_response()) as mock_get,
        ):
            client.search("jacket")
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer tok-x"
        assert headers["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_US"


class TestGetItem:
    def test_calls_item_by_legacy_id_endpoint_with_item_id_param(self):
        with (
            patch.object(client.requests, "post", return_value=_token_response()),
            patch.object(client.requests, "get", return_value=_browse_response()) as mock_get,
        ):
            status, _text = client.get_item("123456789012", timeout_s=10.0)
        assert status == 200
        assert mock_get.call_args.args[0] == client._ITEM_BY_LEGACY_ID_URL
        assert mock_get.call_args.kwargs["params"] == {"legacy_item_id": "123456789012"}


class TestBrowseApiRetryAndFailure:
    def test_401_retries_once_with_fresh_token(self):
        token_responses = [_token_response("tok-old"), _token_response("tok-new")]
        browse_responses = [_browse_response(status_code=401, text="expired"), _browse_response()]

        with (
            patch.object(client.requests, "post", side_effect=token_responses),
            patch.object(client.requests, "get", side_effect=browse_responses) as mock_get,
        ):
            status, _text = client.search("jacket")

        assert status == 200
        assert mock_get.call_count == 2
        first_headers = mock_get.call_args_list[0].kwargs["headers"]
        second_headers = mock_get.call_args_list[1].kwargs["headers"]
        assert first_headers["Authorization"] == "Bearer tok-old"
        assert second_headers["Authorization"] == "Bearer tok-new"

    def test_second_consecutive_401_raises(self):
        token_responses = [_token_response("tok-a"), _token_response("tok-b")]
        browse_responses = [
            _browse_response(status_code=401, text="expired"),
            _browse_response(status_code=401, text="still expired"),
        ]
        with (
            patch.object(client.requests, "post", side_effect=token_responses),
            patch.object(client.requests, "get", side_effect=browse_responses) as mock_get,
            pytest.raises(EbayApiRequestFailed) as exc_info,
        ):
            client.search("jacket")
        assert mock_get.call_count == 2
        assert exc_info.value.status == 401

    def test_non_401_non_2xx_raises_without_retry(self):
        with (
            patch.object(client.requests, "post", return_value=_token_response()),
            patch.object(
                client.requests, "get", return_value=_browse_response(status_code=500, text="server error")
            ) as mock_get,
            pytest.raises(EbayApiRequestFailed) as exc_info,
        ):
            client.search("jacket")
        assert mock_get.call_count == 1
        assert exc_info.value.status == 500
        assert exc_info.value.body == "server error"

    def test_connection_error_raises(self):
        import requests as real_requests

        with (
            patch.object(client.requests, "post", return_value=_token_response()),
            patch.object(
                client.requests, "get", side_effect=real_requests.exceptions.Timeout("timed out")
            ),
            pytest.raises(EbayApiRequestFailed) as exc_info,
        ):
            client.search("jacket")
        assert exc_info.value.status is None
        assert "timed out" in exc_info.value.body


# ---- fetch_url() dispatch -----------------------------------------------------


class TestFetchUrl:
    def test_dispatches_to_search_for_search_url(self):
        url = "https://www.ebay.com/sch/i.html?_nkw=corduroy+jacket"
        with patch.object(client, "search", return_value=(200, "search-result")) as mock_search:
            status, text = client.fetch_url(url, timeout_s=5.0)
        assert (status, text) == (200, "search-result")
        mock_search.assert_called_once_with("corduroy jacket", timeout_s=5.0)

    def test_dispatches_to_get_item_for_item_url(self):
        url = "https://www.ebay.com/itm/123456789012"
        with patch.object(client, "get_item", return_value=(200, "item-result")) as mock_get_item:
            status, text = client.fetch_url(url, timeout_s=5.0)
        assert (status, text) == (200, "item-result")
        mock_get_item.assert_called_once_with("123456789012", timeout_s=5.0)

    def test_raises_value_error_for_neither_shape(self):
        with pytest.raises(ValueError, match="matches neither"):
            client.fetch_url("https://www.ebay.com/some/other/page")
