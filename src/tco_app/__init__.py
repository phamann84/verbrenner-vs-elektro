"""Elektro vs Verbrenner TCO Rechner."""

__all__ = ["__version__"]
__version__ = "0.1.0"

try:
    import warnings

    warnings.filterwarnings(
        "ignore",
        message="urllib3 v2 only supports OpenSSL 1.1.1+",
    )

    from urllib3.exceptions import NotOpenSSLWarning

    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass
