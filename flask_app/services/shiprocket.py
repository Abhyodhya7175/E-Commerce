from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import requests
from flask import current_app

BASE_URL = "https://apiv2.shiprocket.in/v1/external"

_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expires_at": None}
_TOKEN_LOCK = Lock()


def _config_value(key: str, default: Any = None, required: bool = False) -> Any:
    value = current_app.config.get(key, default)
    if required and not value:
        raise RuntimeError(f"Missing required config: {key}")
    return value


def _request_timeout() -> float:
    return float(_config_value("SHIPROCKET_TIMEOUT_SECONDS", 8))


def _token_ttl_seconds() -> int:
    return int(_config_value("SHIPROCKET_TOKEN_TTL_SECONDS", 24 * 3600))


def get_shiprocket_token(force_refresh: bool = False) -> str:
    """Return a cached Shiprocket token or fetch a new one when expired."""
    now = datetime.utcnow()
    with _TOKEN_LOCK:
        token = _TOKEN_CACHE.get("token")
        expires_at = _TOKEN_CACHE.get("expires_at")
        if token and expires_at and expires_at > now and not force_refresh:
            return token

    email = _config_value("SHIPROCKET_EMAIL", required=True)
    password = _config_value("SHIPROCKET_PASSWORD", required=True)

    url = f"{BASE_URL}/auth/login"
    payload = {"email": email, "password": password}

    try:
        response = requests.post(url, json=payload, timeout=_request_timeout())
        response.raise_for_status()
    except requests.RequestException as exc:
        current_app.logger.exception("Shiprocket auth failed")
        raise RuntimeError("Unable to authenticate with Shiprocket") from exc

    data = response.json() if response.content else {}
    token = data.get("token")
    if not token:
        current_app.logger.error("Shiprocket auth response missing token: %s", data)
        raise RuntimeError("Shiprocket authentication did not return a token")

    expires_at = now + timedelta(seconds=max(_token_ttl_seconds() - 60, 60))
    with _TOKEN_LOCK:
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expires_at"] = expires_at
    return token


def _request_shiprocket(
    method: str,
    url: str,
    token: str,
    *,
    params: Optional[dict] = None,
    json_payload: Optional[dict] = None,
    retry_on_unauthorized: bool = True,
) -> Tuple[int, dict]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.request(
            method,
            url,
            params=params,
            json=json_payload,
            headers=headers,
            timeout=_request_timeout(),
        )
    except requests.RequestException as exc:
        current_app.logger.exception("Shiprocket request failed: %s", url)
        raise RuntimeError("Shiprocket request failed") from exc

    if response.status_code == 401 and retry_on_unauthorized:
        token = get_shiprocket_token(force_refresh=True)
        return _request_shiprocket(
            method,
            url,
            token,
            params=params,
            json_payload=json_payload,
            retry_on_unauthorized=False,
        )

    try:
        data = response.json() if response.content else {}
    except ValueError:
        data = {}

    if response.status_code >= 400:
        current_app.logger.error("Shiprocket API error %s: %s", response.status_code, data)
    return response.status_code, data


def _parse_eta_days(courier: dict) -> Optional[int]:
    for key in ("estimated_delivery_days", "estimated_delivery_days_min", "estimated_delivery_days_max"):
        value = courier.get(key)
        if isinstance(value, (int, float)):
            return max(1, int(round(value)))
        if isinstance(value, str) and value.isdigit():
            return max(1, int(value))

    etd = courier.get("etd")
    if isinstance(etd, str):
        try:
            target = datetime.strptime(etd[:10], "%Y-%m-%d")
            delta = (target.date() - datetime.utcnow().date()).days
            return max(1, delta)
        except ValueError:
            return None
    return None


def check_serviceability(
    pincode: str,
    weight_kg: float,
    *,
    pickup_pincode: Optional[str] = None,
    cod: bool = True,
) -> dict:
    """Check delivery serviceability for a pincode using Shiprocket."""
    if not pickup_pincode:
        pickup_pincode = _config_value("SHIPROCKET_PICKUP_PINCODE")
    if not pickup_pincode:
        raise RuntimeError("Missing pickup pincode configuration")

    weight_kg = max(float(weight_kg or 0.5), 0.1)
    url = f"{BASE_URL}/courier/serviceability/"
    params = {
        "pickup_postcode": str(pickup_pincode),
        "delivery_postcode": str(pincode),
        "weight": round(weight_kg, 2),
        "cod": 1 if cod else 0,
    }

    token = get_shiprocket_token()
    status_code, payload = _request_shiprocket("GET", url, token, params=params)

    if status_code >= 400:
        raise RuntimeError("Shiprocket serviceability check failed")

    data = payload.get("data") or {}
    couriers = data.get("available_courier_companies") or []
    if isinstance(data, list):
        couriers = data

    if not couriers:
        return {
            "available": False,
            "courier": None,
            "eta_days": None,
            "eta_text": None,
            "cod": False,
            "estimated_date": None,
            "pickup_pincode": pickup_pincode,
        }

    best_courier = None
    best_eta = None
    for courier in couriers:
        eta_days = _parse_eta_days(courier)
        if eta_days is None:
            continue
        if best_eta is None or eta_days < best_eta:
            best_eta = eta_days
            best_courier = courier

    if best_courier is None:
        best_courier = couriers[0]

    eta_days = best_eta or _parse_eta_days(best_courier)
    eta_text = f"{eta_days} Days" if eta_days else None
    estimated_date = None
    if eta_days:
        estimated_date = (datetime.utcnow().date() + timedelta(days=eta_days)).isoformat()

    cod_available = any(bool(courier.get("cod")) for courier in couriers)
    courier_name = best_courier.get("courier_name") or best_courier.get("name")

    return {
        "available": True,
        "courier": courier_name,
        "eta_days": eta_days,
        "eta_text": eta_text,
        "cod": cod_available,
        "estimated_date": estimated_date,
        "pickup_pincode": pickup_pincode,
    }