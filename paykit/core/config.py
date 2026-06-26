"""
Core configuration management for PayKit.

Changes over original:
- Atomic config saves (write temp → rename, no corrupt paykit.json on crash)
- get_cdn_url() normalises scheme so fetcher always gets a valid URL
- Multi-merchant: providers block supports per-provider config dict
  { "payme": { "version": "latest", "config": { "PAYME_KEY": "..." } } }
  as well as the original flat string form { "payme": "latest" }
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Set


class Config:
    """Manages PayKit configuration and provider state."""

    CONFIG_FILENAME = "paykit.json"
    DEFAULT_CDN_URL = "http://cdn.paykit.qzz.io"

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self.config_path = self.project_dir / self.CONFIG_FILENAME
        self.library_dir = self._get_library_dir()
        self.providers_dir = self.library_dir / "providers"
        self._config_data: Optional[Dict] = None

    @staticmethod
    def _get_library_dir() -> Path:
        import paykit

        return Path(paykit.__file__).parent

    # ── Load / save ──────────────────────────────────────────────────────────

    def load_config(self) -> Dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"paykit.json not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as fh:
            self._config_data = json.load(fh)
        return self._config_data

    def save_config(self, config: Optional[Dict] = None) -> None:
        """Atomic save: write to .tmp then rename — crash-safe."""
        data = config or self._config_data
        if data is None:
            raise ValueError("No configuration data to save")
        tmp = self.config_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        # os.replace is atomic on POSIX; near-atomic on Windows
        os.replace(tmp, self.config_path)
        self._config_data = data

    def initialize(
        self, framework: str = "django", cdn_url: Optional[str] = None
    ) -> Dict:
        config = {
            "framework": framework,
            "providers": {},
        }
        self.save_config(config)
        return config

    # ── Getters ──────────────────────────────────────────────────────────────

    def _data(self) -> Dict:
        return self._config_data or self.load_config()

    def get_framework(self) -> str:
        return self._data().get("framework", "django")

    def set_framework(self, framework: str) -> None:
        cfg = self._data()
        cfg["framework"] = framework
        self.save_config(cfg)

    def get_provider_defaults(self, provider_name: str) -> Dict[str, Any]:
        return self._data().get("defaults", {}).get(provider_name, {})

    def get_cdn_url(self) -> str:
        url = self._data().get("cdn_url", self.DEFAULT_CDN_URL).rstrip("/")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    # ── Provider config (multi-merchant aware) ───────────────────────────────

    def get_providers(self) -> Dict[str, str]:
        """
        Returns {provider_name: version} — same shape as before.
        Works whether the stored value is a plain version string or a dict.
        """
        raw: Dict[str, Any] = self._data().get("providers", {})
        out: Dict[str, str] = {}
        for name, val in raw.items():
            if isinstance(val, dict):
                out[name] = val.get("version", "latest")
            else:
                out[name] = str(val)
        return out

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Returns per-provider runtime config dict if present, else {}.
        This is where multi-merchant keys live, e.g.:
          { "PAYME_KEY": "...", "CLICK_SECRET_KEY": "..." }
        """
        raw: Dict[str, Any] = self._data().get("providers", {})
        val = raw.get(provider_name, {})
        if isinstance(val, dict):
            return val.get("config", {})
        return {}

    def add_provider(
        self, provider_name: str, version: str, config: Optional[Dict] = None
    ) -> None:
        """
        Add or update a provider.
        If config is given the entry is stored as a dict, otherwise as a plain version string.
        """
        cfg = self._data()
        cfg.setdefault("providers", {})
        if config:
            existing = cfg["providers"].get(provider_name)
            if isinstance(existing, dict):
                existing["version"] = version
                existing["config"] = config
            else:
                cfg["providers"][provider_name] = {"version": version, "config": config}
        else:
            cfg["providers"][provider_name] = version
        self.save_config(cfg)

    def remove_provider(self, provider_name: str) -> None:
        cfg = self._data()
        cfg.get("providers", {}).pop(provider_name, None)
        self.save_config(cfg)

    # ── Installation state ───────────────────────────────────────────────────

    def get_installed_providers(self) -> Set[str]:
        if not self.providers_dir.exists():
            return set()
        return {
            p.name
            for p in self.providers_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        }

    def is_provider_installed(self, provider_name: str) -> bool:
        return (self.providers_dir / provider_name).is_dir()

    def remove_provider_installation(self, provider_name: str) -> None:
        path = self.providers_dir / provider_name
        if path.exists():
            shutil.rmtree(path)

    # ── Misc ─────────────────────────────────────────────────────────────────

    def get_python_version(self) -> str:
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}"

    def validate_config(self) -> bool:
        cfg = self._data()
        for field in ("framework", "providers"):
            if field not in cfg:
                raise ValueError(f"Missing required field: {field}")
        if not isinstance(cfg["providers"], dict):
            raise ValueError("'providers' must be a dict")
        return True

    def config_exists(self) -> bool:
        return self.config_path.exists()


config = Config()
