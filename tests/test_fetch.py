import email.message
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_layers  # noqa: E402

URL = "https://example.org/data/layer?f=json"


def use(monkeypatch, behaviour):
    fetch_layers._robots.clear()
    monkeypatch.setattr(fetch_layers, "_get", behaviour)


def http_error(code):
    def raise_it(url):
        raise urllib.error.HTTPError(url, code, "status", email.message.Message(), None)
    return raise_it


def test_4xx_means_no_rules(monkeypatch):
    use(monkeypatch, http_error(404))
    assert fetch_layers.allowed(URL)
    use(monkeypatch, http_error(403))
    assert fetch_layers.allowed(URL)


def test_5xx_means_complete_disallow(monkeypatch):
    use(monkeypatch, http_error(503))
    assert not fetch_layers.allowed(URL)


def test_unreachable_means_complete_disallow(monkeypatch):
    def unreachable(url):
        raise urllib.error.URLError("no route to host")
    use(monkeypatch, unreachable)
    assert not fetch_layers.allowed(URL)


def test_rules_are_obeyed(monkeypatch):
    use(monkeypatch, lambda url: b"User-agent: *\nDisallow: /data/\n")
    assert not fetch_layers.allowed(URL)
    assert fetch_layers.allowed("https://example.org/other")
