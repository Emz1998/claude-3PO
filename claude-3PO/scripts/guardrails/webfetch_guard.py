"""WebFetchGuard — Validates that a WebFetch URL targets a safe domain."""

from urllib.parse import urlparse

from typing import Literal

from config import Config


Decision = tuple[Literal["allow", "block"], str]


class WebFetchGuard:
    """Validate that a WebFetch URL targets a configured safe domain.

    The safe-domain check accepts both exact host equality and subdomain
    matches (``foo.example.com`` is allowed when ``example.com`` is in the
    safe list), so callers can whitelist a domain once and pick up its
    subdomains automatically.

    Example:
        >>> guard = WebFetchGuard(hook_input, config)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config):
        """
        Cache the URL string and config.

        Args:
            hook_input (dict): Raw PreToolUse hook payload.
            config (Config): Workflow configuration (provides ``safe_domains``).

        Example:
            >>> guard = WebFetchGuard(hook_input, config)  # doctest: +SKIP
            >>> guard.url  # doctest: +SKIP
            'https://example.com'
        """
        self.config = config
        self.url = hook_input.get("tool_input", {}).get("url", "")

    def _check_url_present(self) -> None:
        """
        Reject empty URLs.

        Raises:
            ValueError: If ``self.url`` is empty.

        Example:
            >>> # Raises ValueError when self.url is empty:
            >>> guard._check_url_present()  # doctest: +SKIP
        """
        if not self.url:
            raise ValueError("URL is empty")

    def _check_hostname_parseable(self) -> str:
        """
        Extract the URL's hostname.

        Returns:
            str: The lowercase hostname.

        Raises:
            ValueError: If the URL has no parseable hostname.

        Example:
            >>> host = guard._check_hostname_parseable()  # doctest: +SKIP
        """
        host = urlparse(self.url).hostname or ""
        if not host:
            raise ValueError(f"Could not parse hostname from URL: {self.url}")
        return host

    def _check_domain_safe(self, host: str) -> None:
        """
        Confirm the hostname matches a safe domain (exact or subdomain).

        Args:
            host (str): Hostname extracted from the URL.

        Raises:
            ValueError: If no safe domain matches.

        Example:
            >>> # Raises ValueError when host isn't in the safe-domain list:
            >>> guard._check_domain_safe("evil.example")  # doctest: +SKIP
        """
        for domain in self.config.safe_domains:
            if host == domain or host.endswith("." + domain):
                return
        raise ValueError(f"Domain '{host}' is not in the safe domains list")

    def validate(self) -> Decision:
        """
        Validate the URL and return an allow/block decision.

        Returns:
            Decision: ``("allow", message)`` if the URL is non-empty,
            parseable, and on the safe-domain list. Otherwise
            ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            self._check_url_present()
            host = self._check_hostname_parseable()
            self._check_domain_safe(host)
            return "allow", f"Domain '{host}' is safe"
        except ValueError as e:
            return "block", str(e)
