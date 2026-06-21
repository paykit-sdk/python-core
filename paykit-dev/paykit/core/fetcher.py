"""
Provider fetcher — downloads and installs providers from CDN.
"""

import json
import os
import shutil
import tarfile
import time
import zipfile
from pathlib import Path
from typing import Dict, List

import requests


class ProviderFetcher:
    def __init__(self, cdn_url: str, library_dir: Path):
        raw = cdn_url.rstrip("/")
        if not raw.startswith(("http://", "https://")):
            raw = "https://" + raw
        self.cdn_url = raw
        self.library_dir = library_dir
        self.providers_dir = library_dir / "providers"
        self.providers_dir.mkdir(parents=True, exist_ok=True)

    # ── CDN discovery ─────────────────────────────────────────────────────────

    def fetch_available_providers(self, framework: str) -> List[str]:
        """GET /providers/{framework}/available → list of provider names."""
        url = f"{self.cdn_url}/providers/{framework}/available"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"Expected list from {url}, got {type(data)}")
        return data

    def fetch_available_versions(self, framework: str, provider_name: str) -> List[str]:
        """GET /providers/{framework}/{provider}/available → list of versions."""
        url = f"{self.cdn_url}/providers/{framework}/{provider_name}/available"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"Expected list from {url}, got {type(data)}")
        return data

    def fetch_metadata(self, framework: str, provider_name: str, version: str) -> Dict:
        """GET /providers/{framework}/{provider}/{version} → metadata dict with download_url."""
        url = f"{self.cdn_url}/providers/{framework}/{provider_name}/{version}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ── Install ───────────────────────────────────────────────────────────────

    def install_provider(
        self,
        framework: str,
        provider_name: str,
        version: str,
        force: bool = False,
    ) -> Path:
        provider_dir = self.providers_dir / provider_name

        if provider_dir.exists() and not force:
            return provider_dir

        metadata = self.fetch_metadata(framework, provider_name, version)
        download_url = metadata.get("download_url", "").strip()
        if not download_url:
            raise ValueError(
                f"CDN returned no download_url for {provider_name}@{version}"
            )
        if not download_url.startswith(("http://", "https://")):
            download_url = "https://" + download_url

        resp = requests.get(download_url, timeout=60, stream=True)
        resp.raise_for_status()

        # Unique temp paths — safe against concurrent paykit runs
        uid = f"{os.getpid()}_{int(time.time() * 1000)}"
        is_tar = ".tar" in download_url or download_url.endswith(".tgz")
        suffix = ".tar.gz" if is_tar else ".zip"
        tmp_archive = self.providers_dir / f"_{provider_name}_{uid}{suffix}"
        tmp_dir = self.providers_dir / f"_{provider_name}_{uid}_extract"

        try:
            with open(tmp_archive, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)

            tmp_dir.mkdir(parents=True, exist_ok=True)

            if is_tar:
                with tarfile.open(tmp_archive, "r:gz") as tf:
                    tf.extractall(tmp_dir)
            else:
                with zipfile.ZipFile(tmp_archive, "r") as zf:
                    zf.extractall(tmp_dir)

            # The archive may wrap everything in a single top-level dir — unwrap it
            extracted = list(tmp_dir.iterdir())
            if len(extracted) == 1 and extracted[0].is_dir():
                actual_dir = extracted[0]
            else:
                actual_dir = tmp_dir

            if provider_dir.exists():
                shutil.rmtree(provider_dir)
            actual_dir.rename(provider_dir)

        except Exception:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
        finally:
            if tmp_archive.exists():
                tmp_archive.unlink()
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

        return provider_dir

    def verify_installation(self, provider_name: str) -> bool:
        provider_dir = self.providers_dir / provider_name
        if not provider_dir.is_dir():
            return False
        if not (provider_dir / "__init__.py").exists():
            return False
        manifest = provider_dir / "manifest.json"
        if not manifest.exists():
            return False
        try:
            with open(manifest) as fh:
                json.load(fh)
        except (json.JSONDecodeError, OSError):
            return False
        return True
