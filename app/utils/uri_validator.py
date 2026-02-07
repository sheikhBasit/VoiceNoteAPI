"""URI validation utilities for client-side storage."""

from urllib.parse import urlparse

from fastapi import HTTPException


def validate_client_uri(uri: str) -> bool:
    """
    Validate that URI is a valid Android content/file URI.

    Allowed schemes:
    - content:// (Android Content Provider)
    - file:// (File system path)

    Examples:
    - content://media/external/files/12345
    - content://com.voicenote.provider/documents/uuid
    - file:///storage/emulated/0/Documents/doc.pdf
    """
    if not uri:
        return False

    allowed_schemes = ["content", "file"]

    try:
        parsed = urlparse(uri)

        if parsed.scheme not in allowed_schemes:
            raise ValueError(
                f"Invalid URI scheme: {parsed.scheme}. Allowed: {allowed_schemes}"
            )

        # Additional validation for content URIs
        if parsed.scheme == "content":
            if not uri.startswith("content://"):
                raise ValueError("Invalid content URI format")
            # Content URIs should have an authority
            if not parsed.netloc:
                raise ValueError("Content URI missing authority")

        # Additional validation for file URIs
        if parsed.scheme == "file":
            if not uri.startswith("file://"):
                raise ValueError("Invalid file URI format")
            # File URIs should have a path
            if not parsed.path:
                raise ValueError("File URI missing path")

        return True

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid client URI: {str(e)}")


def validate_uri_list(uris: list[str]) -> bool:
    """Validate a list of URIs."""
    if not uris:
        return True

    for uri in uris:
        validate_client_uri(uri)

    return True
