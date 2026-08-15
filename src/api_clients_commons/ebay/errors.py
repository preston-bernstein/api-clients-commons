"""Exceptions for the eBay Browse API client."""


class EbayCredentialsMissing(RuntimeError):
    """Raised when EBAY_CLIENT_ID and/or EBAY_CLIENT_SECRET environment
    variables are unset or blank before attempting an OAuth call.

    The exception message names the exact missing variable name(s), e.g.
    "EBAY_CLIENT_ID is unset or blank" or "EBAY_CLIENT_ID and
    EBAY_CLIENT_SECRET are unset or blank", but never includes the actual
    values of either variable.
    """


class EbayApiRequestFailed(RuntimeError):
    """Raised when an HTTP-layer failure occurs on an eBay OAuth token
    request or Browse API request.

    Covers non-2xx HTTP status codes, connection errors, and timeouts.

    Attributes:
        status (int | None): The observed HTTP status code if a response was
            received, or None if the failure occurred at the connection layer.
        body (str): The raw response text if a response was received, or the
            underlying HTTP client exception message if no response was received.
    """

    def __init__(self, message, status=None, body=""):
        """Initialize EbayApiRequestFailed with message and response details.

        Args:
            message: The error message describing the failure.
            status: HTTP status code (int) if a response was received, or None.
            body: Raw response text or exception message.
        """
        super().__init__(message)
        self.status = status
        self.body = body
