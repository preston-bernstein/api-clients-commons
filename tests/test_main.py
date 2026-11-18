"""Characterization tests for the `python -m api_clients_commons.ebay` CLI."""

from __future__ import annotations

import importlib.metadata
from unittest.mock import patch

from api_clients_commons.ebay import __main__ as cli


def test_plain_query_goes_to_search(capsys):
    with patch.object(cli, "search", return_value=(200, '{"ok": 1}')) as mock_search:
        code = cli.main(["corduroy jacket", "--timeout-s", "3"])
    out = capsys.readouterr()
    assert code == 0
    assert out.out == '{"ok": 1}\n'
    assert out.err == ""
    mock_search.assert_called_once_with("corduroy jacket", timeout_s=3.0)


def test_ebay_url_goes_to_fetch_url(capsys):
    url = "https://www.ebay.com/itm/123"
    with patch.object(cli, "fetch_url", return_value=(200, "body")) as mock_fetch:
        code = cli.main([url])
    assert code == 0
    assert capsys.readouterr().out == "body\n"
    mock_fetch.assert_called_once_with(url, timeout_s=10.0)


def test_failure_prints_error_and_version(capsys):
    with (
        patch.object(cli, "search", side_effect=ValueError("boom")),
        patch.object(importlib.metadata, "version", return_value="9.9.9"),
    ):
        code = cli.main(["q"])
    out = capsys.readouterr()
    assert code == 1
    assert out.out == ""
    assert out.err == "ValueError: boom\napi-clients-commons version: 9.9.9\n"


def test_failure_without_installed_package_prints_path(capsys):
    with (
        patch.object(cli, "search", side_effect=ValueError("boom")),
        patch.object(
            importlib.metadata,
            "version",
            side_effect=importlib.metadata.PackageNotFoundError("x"),
        ),
    ):
        code = cli.main(["q"])
    out = capsys.readouterr()
    assert code == 1
    assert out.out == ""
    assert out.err == f"ValueError: boom\nrunning from: {cli.__file__}\n"
