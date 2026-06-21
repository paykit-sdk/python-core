"""
ClickConfig — per-instance config for Click.uz (Django).

Resolution order (first wins):
  1. Explicit kwargs
  2. paykit.json  providers.click.config
  3. Django settings
  4. Environment variables
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional


def _django_setting(name: str, default=None):
    try:
        from django.conf import settings
        return getattr(settings, name, default)
    except Exception:
        return default


def _paykit_config() -> dict:
    try:
        from paykit.core.config import Config
        cfg = Config()
        if cfg.config_exists():
            cfg.load_config()
            return cfg.get_provider_config("click")
    except Exception:
        pass
    return {}


@dataclass
class ClickConfig:
    """
    Holds Click.uz merchant credentials.

    Usage:
        cfg = ClickConfig()                    # auto-resolve
        cfg = ClickConfig(secret_key="...", service_id=1234)   # explicit
    """
    secret_key:  Optional[str] = None
    service_id:  Optional[int] = None
    merchant_id: Optional[int] = None  # optional, for some Click flows

    def __post_init__(self):
        pk = _paykit_config()

        if self.secret_key is None:
            self.secret_key = (
                pk.get("CLICK_SECRET_KEY")
                or _django_setting("CLICK_SECRET_KEY")
                or os.environ.get("CLICK_SECRET_KEY", "")
            )
        if self.service_id is None:
            raw = (
                pk.get("CLICK_SERVICE_ID")
                or _django_setting("CLICK_SERVICE_ID")
                or os.environ.get("CLICK_SERVICE_ID")
            )
            self.service_id = int(raw) if raw else None

        if self.merchant_id is None:
            raw = (
                pk.get("CLICK_MERCHANT_ID")
                or _django_setting("CLICK_MERCHANT_ID")
                or os.environ.get("CLICK_MERCHANT_ID")
            )
            self.merchant_id = int(raw) if raw else None

    def validate(self):
        if not self.secret_key:
            raise RuntimeError(
                "CLICK_SECRET_KEY not configured. Set in Django settings, "
                "environment, or paykit.json providers.click.config."
            )
        if not self.service_id:
            raise RuntimeError("CLICK_SERVICE_ID not configured.")
