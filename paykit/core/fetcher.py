"""
Provider fetcher for downloading and installing providers from CDN

Handles fetching provider metadata and downloading provider packages
from the configured CDN server.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Dict
import requests


class ProviderFetcher:
    """Manages fetching and installing providers from CDN"""

    def __init__(self, cdn_url: str, library_dir: Path):
        """
        Initialize provider fetcher

        Args:
            cdn_url: Base CDN URL for fetching providers
            library_dir: PayKit library installation directory
        """
        self.cdn_url = cdn_url.rstrip("/")
        self.library_dir = library_dir
        self.providers_dir = library_dir / "providers"
        self.providers_dir.mkdir(parents=True, exist_ok=True)

    def _build_metadata_url(self, framework: str, provider_name: str, version: str) -> str:
        """
        Build URL for provider metadata

        Args:
            framework: Framework name
            provider_name: Provider name
            version: Provider version

        Returns:
            Full metadata URL
        """
        # URL format: cdn_url/providers/<framework>/<provider_name>/<version>
        path = f"providers/{framework}/{provider_name}/{version}"
        return f"{self.cdn_url}/{path}"

    def fetch_metadata(self, framework: str, provider_name: str, version: str) -> Dict:
        """
        Fetch provider metadata from CDN

        Args:
            framework: Framework name
            provider_name: Provider name
            version: Provider version

        Returns:
            Metadata dictionary containing version info and download link

        Raises:
            requests.RequestException: If fetching fails
            json.JSONDecodeError: If metadata is invalid
        """
        url = self._build_metadata_url(framework, provider_name, version)

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        metadata = response.json()
        return metadata

    def download_provider(
        self,
        framework: str,
        provider_name: str,
        version: str,
        force: bool = False
    ) -> Path:
        """
        Download and install provider from CDN

        Args:
            framework: Framework name
            provider_name: Provider name
            version: Provider version
            force: Force re-download if already installed

        Returns:
            Path to installed provider directory

        Raises:
            requests.RequestException: If download fails
            ValueError: If metadata is invalid
        """
        provider_dir = self.providers_dir / provider_name

        # Check if already installed
        if provider_dir.exists() and not force:
            return provider_dir

        # Remove existing installation if forcing
        if provider_dir.exists():
            shutil.rmtree(provider_dir)

        # Fetch metadata to get download link
        metadata = self.fetch_metadata(framework, provider_name, version)

        if "download_url" not in metadata:
            raise ValueError(f"Invalid metadata: missing download_url for {provider_name}")

        download_url = metadata["download_url"]

        # Download provider package
        response = requests.get(download_url, timeout=60, stream=True)
        response.raise_for_status()

        # Save to temporary file
        temp_file = self.providers_dir / f"{provider_name}_temp.zip"

        try:
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extract provider
            provider_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(temp_file, "r") as zip_ref:
                zip_ref.extractall(provider_dir)

        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()

        return provider_dir

    def install_provider(
        self,
        framework: str,
        provider_name: str,
        version: str,
        force: bool = False
    ) -> bool:
        """
        Install provider with error handling

        Args:
            framework: Framework name
            provider_name: Provider name
            version: Provider version
            force: Force re-installation

        Returns:
            True if installation successful
        """
        try:
            self.download_provider(framework, provider_name, version, force)
            return True
        except Exception as e:
            # Clean up on failure
            provider_dir = self.providers_dir / provider_name
            if provider_dir.exists():
                shutil.rmtree(provider_dir)
            raise

    def verify_installation(self, provider_name: str) -> bool:
        """
        Verify that a provider is properly installed

        Args:
            provider_name: Provider name to verify

        Returns:
            True if provider appears to be properly installed
        """
        provider_dir = self.providers_dir / provider_name

        if not provider_dir.exists() or not provider_dir.is_dir():
            return False

        # Check for essential files
        required_files = ["__init__.py", "manifest.json"]

        for filename in required_files:
            if not (provider_dir / filename).exists():
                return False

        return True
