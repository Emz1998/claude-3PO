"""WebFetchValidator — Validates that a WebFetch URL targets a safe domain."""

from urllib.parse import urlparse

from config import Config


Result = tuple[bool, str]


class WebFetchValidator:
    """Validate that a WebFetch URL targets a safe domain."""

    def __init__(self, hook_input: dict, config: Config):
        self.config = config
        self.url = hook_input.get("tool_input", {}).get("url", "")

    def _check_url_present(self) -> None:
        if not self.url:
            raise ValueError("URL is empty")

    def _check_hostname_parseable(self) -> str:
        host = urlparse(self.url).hostname or ""
        if not host:
            raise ValueError(f"Could not parse hostname from URL: {self.url}")
        return host

    def _check_domain_safe(self, host: str) -> None:
        for domain in self.config.safe_domains:
            if host == domain or host.endswith("." + domain):
                return
        raise ValueError(f"Domain '{host}' is not in the safe domains list")

    def validate(self) -> Result:
        self._check_url_present()
        host = self._check_hostname_parseable()
        self._check_domain_safe(host)
        return True, f"Domain '{host}' is safe"
