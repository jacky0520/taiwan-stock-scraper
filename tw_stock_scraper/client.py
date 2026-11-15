"""HTTP client shared by both exchanges."""

import random
import time

import requests

# Use the operating system's certificate store when available. The TPEx
# server does not always send its full certificate chain; the OS store can
# complete it, while Python's default certificate bundle cannot.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0 Safari/537.36"),
}


class Client:
    """
    A requests session that is polite to the servers: it waits a random
    3-6 seconds between requests (both exchanges temporarily block clients
    that request too quickly) and retries failed requests.
    """

    def __init__(self, min_delay=3.0, max_delay=6.0, retries=3, timeout=30):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.retries = retries
        self.timeout = timeout
        self._last_request = 0.0

    def _wait(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        elapsed = time.monotonic() - self._last_request
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def get_json(self, url, **params):
        """GET `url` with query parameters and return the decoded JSON."""
        last_error = None
        for attempt in range(1, self.retries + 1):
            self._wait()
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                self._last_request = time.monotonic()
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as err:
                self._last_request = time.monotonic()
                last_error = err
                print(f"  request failed (attempt {attempt}/{self.retries}): {err}")
        raise RuntimeError(f"Request failed after {self.retries} attempts: {last_error}")
