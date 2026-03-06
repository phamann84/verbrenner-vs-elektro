from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Any

import requests

from .cache import JsonTTLCache


class ApiUnavailableError(RuntimeError):
    """Raised when API data cannot be fetched and no fallback is available."""


@dataclass
class ApiFetchMeta:
    source: str
    cache_status: str
    details: dict[str, Any]


class HttpJsonClient:
    def __init__(
        self,
        cache: JsonTTLCache,
        timeout_seconds: float = 10.0,
        retries: int = 3,
        backoff_seconds: float = 0.8,
    ) -> None:
        self.cache = cache
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()

    def _fetch_json(
        self,
        *,
        cache_key: str,
        url: str,
        params: dict[str, Any],
        ttl_seconds: int,
        source_label: str,
    ) -> tuple[dict[str, Any], ApiFetchMeta]:
        cached = self.cache.get(cache_key, ttl_seconds)
        if cached and cached.is_fresh:
            return (
                cached.data,
                ApiFetchMeta(
                    source=source_label,
                    cache_status="fresh",
                    details={"age_seconds": round(cached.age_seconds, 2)},
                ),
            )

        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout_seconds)
                if resp.status_code == 429:
                    raise requests.HTTPError("HTTP 429 (Rate Limit)")
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {resp.status_code} (Server Error)")
                resp.raise_for_status()
                data = resp.json()
                self.cache.set(cache_key, data)
                cache_state = "refresh" if cached else "miss"
                return (
                    data,
                    ApiFetchMeta(
                        source=source_label,
                        cache_status=cache_state,
                        details={"attempt": attempt + 1},
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.retries - 1:
                    time.sleep(self.backoff_seconds * (2**attempt))

        if cached:
            return (
                cached.data,
                ApiFetchMeta(
                    source=source_label,
                    cache_status="stale",
                    details={
                        "age_seconds": round(cached.age_seconds, 2),
                        "warning": str(last_error),
                    },
                ),
            )

        raise ApiUnavailableError(
            f"API-Aufruf fehlgeschlagen ({source_label}): {last_error}"
        )


class AwattarClient(HttpJsonClient):
    BASE_URL = "https://api.awattar.at/v1/marketdata"

    def _average_market_price_eur_per_kwh(
        self,
        start_ms: int,
        end_ms: int,
        ttl_seconds: int,
        cache_suffix: str,
    ) -> tuple[float, ApiFetchMeta]:
        params = {
            "start": start_ms,
            "end": end_ms,
        }
        cache_key = f"awattar:{cache_suffix}:{start_ms}:{end_ms}"
        data, meta = self._fetch_json(
            cache_key=cache_key,
            url=self.BASE_URL,
            params=params,
            ttl_seconds=ttl_seconds,
            source_label="aWATTar Marketdata",
        )

        entries = data.get("data") or []
        market_prices = [
            float(item.get("marketprice"))
            for item in entries
            if isinstance(item.get("marketprice"), (float, int))
        ]
        if not market_prices:
            raise ApiUnavailableError("aWATTar lieferte keine gueltigen Marktpreise.")

        avg_eur_per_mwh = float(statistics.mean(market_prices))
        avg_eur_per_kwh = avg_eur_per_mwh / 1000.0
        meta.details["points"] = len(market_prices)
        meta.details["avg_eur_per_mwh"] = round(avg_eur_per_mwh, 4)
        return avg_eur_per_kwh, meta

    def get_average_next24h_eur_per_kwh(
        self,
        ttl_seconds: int,
        now_ts: float | None = None,
    ) -> tuple[float, ApiFetchMeta]:
        now = int((now_ts if now_ts is not None else time.time()) * 1000)
        end = now + 24 * 60 * 60 * 1000
        return self._average_market_price_eur_per_kwh(now, end, ttl_seconds, "next24h")

    def get_average_last7d_eur_per_kwh(
        self,
        ttl_seconds: int,
        now_ts: float | None = None,
    ) -> tuple[float, ApiFetchMeta]:
        now = int((now_ts if now_ts is not None else time.time()) * 1000)
        start = now - 7 * 24 * 60 * 60 * 1000
        return self._average_market_price_eur_per_kwh(start, now, ttl_seconds, "last7d")
