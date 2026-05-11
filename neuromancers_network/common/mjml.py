"""
MJML Python SDK - Async client for MJML API
"""

from typing import Any

import requests
from requests.auth import HTTPBasicAuth

INVALID_REQUEST = 400
INVALID = 401
FORBIDDEN = 403
INTERNAL_ERROR = 500
OK = 200


class MJMLClient:
    """
    Python client for the MJML API.

    API Reference: https://mjml.io/api/documentation/
    Endpoint: https://api.mjml.io/v1/render
    """

    def __init__(
        self,
        application_id: str | None = None,
        secret_key: str | None = None,
        base_url: str = "https://api.mjml.io/v1",
        timeout: int = 30,
    ):
        """
        Initialize the MJML API client.

        Args:
            application_id: Your MJML Application ID
            secret_key: Your MJML Secret Key (use Secret Key for backend usage)
            base_url: Base URL of the MJML API (defaults to official endpoint)
            timeout: Request timeout in seconds

        The application ID acts as a username and the API key acts as a password.
        The Secret Key should be used from a back-end application. The Public Key
        can be used from a web browser but is less secure for server-side use.

        Credentials can also be provided via environment variables:
            MJML_APP_ID
            MJML_SECRET_KEY
        """
        self.application_id = application_id
        self.secret_key = secret_key

        if not self.application_id or not self.secret_key:
            msg = "Missing MJML credentials"
            raise ValueError(msg, )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def render(self, mjml_content: str) -> dict[str, Any]:
        """
        Convert MJML markup to responsive HTML.

        Args:
            mjml_content: String containing valid MJML markup

        Returns:
            Dictionary containing:
                - html: The rendered HTML
                - mjml: The original MJML input
                - mjml_version: MJML version used
                - errors: List of validation errors (if any)

        Raises:
            requests.RequestException: For network or HTTP errors
            ValueError: For invalid responses

        Example:
            >>> client = MJMLClient()
            >>> result = client.render("<mjml><mj-body>...</mjml>")
            >>> print(result["html"])
        """
        url = f"{self.base_url}/render"
        payload = {"mjml": mjml_content}

        response = requests.post(
            url,
            json=payload,
            auth=HTTPBasicAuth(self.application_id, self.secret_key),
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )

        # Handle HTTP errors
        if response.status_code == INVALID:
            msg = (
                f"Authentication failed: Invalid Application ID or Secret Key. "
                f"Response: {response.text}")
            raise PermissionError(msg, )
        if response.status_code == FORBIDDEN:
            msg = (f"Unauthorized access. Check your API permissions. "
                   f"Response: {response.text}")
            raise PermissionError(msg, )
        if response.status_code == INVALID_REQUEST:
            error_data = response.json()
            msg = (f"Invalid request. The MJML content may be malformed. "
                   f"Details: {error_data.get('message', response.text)}")
            raise ValueError(msg, )
        if response.status_code == INTERNAL_ERROR:
            error_data = response.json()
            msg = (f"MJML API internal server error. "
                   f"Request ID: {error_data.get('request_id', 'unknown')}. "
                   f"Message: {error_data.get('message', response.text)}")
            raise RuntimeError(msg, )
        if response.status_code != OK:
            msg = f"""
            MJML API returned unexpected status {response.status_code}: {response.text}
"""
            raise requests.RequestException(msg, )

        result = response.json()

        # Validate response structure
        if "html" not in result:
            msg = f"Unexpected API response format: {result}"
            raise ValueError(msg)

        return result

    def render_to_html(self, mjml_content: str) -> str:
        """
        Convenience method that returns only the rendered HTML string.

        Args:
            mjml_content: String containing valid MJML markup

        Returns:
            The rendered responsive HTML as a string

        Raises:
            Same exceptions as render()
        """
        return self.render(mjml_content)["html"]
