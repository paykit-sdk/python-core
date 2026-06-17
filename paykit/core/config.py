"""
Core configuration management for PayKit

Handles loading, saving, and validating paykit.json configuration,
as well as managing provider installations in the library directory.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Optional, Set


class Config:
    """Manages PayKit configuration and provider state"""

    CONFIG_FILENAME = "paykit.json"
    DEFAULT_CDN_URL = "paykit.rf.gd"

    def __init__(self, project_dir: Optional[Path] = None):
        """
        Initialize configuration manager

        Args:
            project_dir: Project directory path (defaults to current directory)
        """
        self.project_dir = project_dir or Path.cwd()
        self.config_path = self.project_dir / self.CONFIG_FILENAME
        self.library_dir = self._get_library_dir()
        self.providers_dir = self.library_dir / "providers"
        self._config_data: Optional[Dict] = None

    @staticmethod
    def _get_library_dir() -> Path:
        """Get the PayKit library installation directory"""
        import paykit
        return Path(paykit.__file__).parent

    def load_config(self) -> Dict:
        """
        Load configuration from paykit.json

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config_data = json.load(f)

        return self._config_data

    def save_config(self, config: Optional[Dict] = None) -> None:
        """
        Save configuration to paykit.json

        Args:
            config: Configuration dictionary (uses cached if None)
        """
        data = config or self._config_data
        if data is None:
            raise ValueError("No configuration data to save")

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self._config_data = data

    def initialize(self, framework: str = "django", cdn_url: Optional[str] = None) -> Dict:
        """
        Initialize a new paykit.json configuration

        Args:
            framework: Default framework to use
            cdn_url: CDN URL for fetching providers

        Returns:
            Initial configuration dictionary
        """
        config = {
            "cdn_url": cdn_url or self.DEFAULT_CDN_URL,
            "framework": framework,
            "providers": {}
        }

        self.save_config(config)
        return config

    def get_framework(self) -> str:
        """
        Get the currently configured framework

        Returns:
            Framework name
        """
        config = self._config_data or self.load_config()
        return config.get("framework", "django")

    def set_framework(self, framework: str) -> None:
        """
        Set the framework in configuration

        Args:
            framework: Framework name to set
        """
        config = self._config_data or self.load_config()
        config["framework"] = framework
        self.save_config(config)

    def get_cdn_url(self) -> str:
        """
        Get the CDN URL from configuration

        Returns:
            CDN URL
        """
        config = self._config_data or self.load_config()
        return config.get("cdn_url", self.DEFAULT_CDN_URL)

    def get_providers(self) -> Dict[str, str]:
        """
        Get configured providers and their versions

        Returns:
            Dictionary mapping provider names to versions
        """
        config = self._config_data or self.load_config()
        return config.get("providers", {})

    def add_provider(self, provider_name: str, version: str) -> None:
        """
        Add or update a provider in configuration

        Args:
            provider_name: Provider name (e.g., "payme:uz")
            version: Provider version
        """
        config = self._config_data or self.load_config()
        if "providers" not in config:
            config["providers"] = {}

        config["providers"][provider_name] = version
        self.save_config(config)

    def remove_provider(self, provider_name: str) -> None:
        """
        Remove a provider from configuration

        Args:
            provider_name: Provider name to remove
        """
        config = self._config_data or self.load_config()
        if "providers" in config and provider_name in config["providers"]:
            del config["providers"][provider_name]
            self.save_config(config)

    def get_installed_providers(self) -> Set[str]:
        """
        Get list of providers installed in library directory

        Returns:
            Set of installed provider names
        """
        if not self.providers_dir.exists():
            return set()

        installed = set()
        for item in self.providers_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                installed.add(item.name)

        return installed

    def is_provider_installed(self, provider_name: str) -> bool:
        """
        Check if a provider is installed in library directory

        Args:
            provider_name: Provider name to check

        Returns:
            True if provider is installed
        """
        provider_path = self.providers_dir / provider_name
        return provider_path.exists() and provider_path.is_dir()

    def remove_provider_installation(self, provider_name: str) -> None:
        """
        Remove provider installation from library directory

        Args:
            provider_name: Provider name to remove
        """
        provider_path = self.providers_dir / provider_name
        if provider_path.exists():
            shutil.rmtree(provider_path)

    def get_python_version(self) -> str:
        """
        Get current Python version

        Returns:
            Python version string (e.g., "3.11")
        """
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}"

    def validate_config(self) -> bool:
        """
        Validate configuration structure

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        config = self._config_data or self.load_config()

        required_fields = ["cdn_url", "framework", "providers"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(config["providers"], dict):
            raise ValueError("'providers' must be a dictionary")

        return True

    def config_exists(self) -> bool:
        """
        Check if configuration file exists

        Returns:
            True if paykit.json exists
        """
        return self.config_path.exists()
