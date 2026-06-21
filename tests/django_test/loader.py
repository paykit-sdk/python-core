"""
PayKit Provider Loader
Loads payment providers from 3 priority locations
"""

import os
import sys
import json
import importlib.util
from typing import Optional, Dict, Any


class ProviderLoader:
    """Loads payment providers from local storage"""

    def __init__(self, framework: Optional[str] = None):
        """
        Initialize loader

        Args:
            framework: Framework name (django, flask, etc.)
        """
        self.framework = framework
        self.paykit_dir = os.path.dirname(paykit.__file__)
        self.global_providers_dir = os.path.join(self.paykit_dir, 'providers')
        self.cwd = os.getcwd()

    def _get_search_paths(self, provider: str) -> list:
        """
        Get search paths in priority order

        Args:
            provider: Provider name

        Returns:
            List of paths to search
        """
        paths = []

        # Priority 1: Current directory ./payments/
        project_path = os.path.join(self.cwd, 'payments', provider)
        paths.append(('project', project_path))

        # Priority 2: Framework-specific location
        if self.framework:
            # Try common framework locations
            framework_paths = [
                os.path.join(self.cwd, 'myproject', 'payments', provider),  # Django
                os.path.join(self.cwd, 'app', 'payments', provider),  # Flask
                os.path.join(self.cwd, self.framework, 'payments', provider),  # Generic
            ]

            for fpath in framework_paths:
                if os.path.exists(fpath):
                    paths.append(('framework', fpath))
                    break

        # Priority 3: Global providers directory
        global_path = os.path.join(self.global_providers_dir, provider)
        paths.append(('global', global_path))

        return paths

    def find_provider(self, provider: str) -> Optional[Dict[str, str]]:
        """
        Find provider in search paths

        Args:
            provider: Provider name

        Returns:
            Dict with 'location', 'path', 'manifest_path' or None
        """
        search_paths = self._get_search_paths(provider)

        for location, path in search_paths:
            manifest_path = os.path.join(path, 'manifest.json')

            if os.path.exists(manifest_path):
                return {
                    'location': location,
                    'path': path,
                    'manifest_path': manifest_path
                }

        return None

    def load_manifest(self, manifest_path: str) -> Optional[Dict]:
        """Load and parse manifest.json"""
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Failed to load manifest: {e}")
            return None

    def load_provider_module(self, provider: str, module_name: str = "__init__") -> Optional[Any]:
        """
        Load a provider Python module

        Args:
            provider: Provider name
            module_name: Module to load (without .py)

        Returns:
            Loaded module or None
        """
        provider_info = self.find_provider(provider)

        if not provider_info:
            print(f"Provider '{provider}' not found in any location")
            return None

        # Load manifest
        manifest = self.load_manifest(provider_info['manifest_path'])
        if not manifest:
            return None

        # Construct module path
        module_path = os.path.join(provider_info['path'], f"{module_name}.py")

        if not os.path.exists(module_path):
            print(f"Module {module_name}.py not found in {provider}")
            return None

        # Load module dynamically
        spec = importlib.util.spec_from_file_location(
            f"paykit.providers.{provider}.{module_name}",
            module_path
        )

        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            print(f"Loaded {provider} from {provider_info['location']}: {provider_info['path']}")
            return module

        return None

    def load_provider(self, provider: str) -> Optional[Dict[str, Any]]:
        """
        Load complete provider with metadata

        Args:
            provider: Provider name

        Returns:
            Dict with 'module', 'manifest', 'location', 'path' or None
        """
        provider_info = self.find_provider(provider)

        if not provider_info:
            return None

        # Load manifest
        manifest = self.load_manifest(provider_info['manifest_path'])
        if not manifest:
            return None

        # Load main module
        module = self.load_provider_module(provider)
        if not module:
            return None

        return {
            'module': module,
            'manifest': manifest,
            'location': provider_info['location'],
            'path': provider_info['path']
        }

    def get_template_path(self, provider: str, framework: Optional[str] = None) -> Optional[str]:
        """
        Get template directory path for provider and framework

        Args:
            provider: Provider name
            framework: Framework name (uses self.framework if not provided)

        Returns:
            Path to templates directory or None
        """
        framework = framework or self.framework

        if not framework:
            return None

        provider_info = self.find_provider(provider)
        if not provider_info:
            return None

        template_path = os.path.join(
            provider_info['path'],
            'templates',
            framework
        )

        if os.path.exists(template_path):
            return template_path

        return None

    def list_installed_providers(self) -> Dict[str, list]:
        """
        List all installed providers by location

        Returns:
            Dict with 'project', 'framework', 'global' keys containing provider lists
        """
        installed = {
            'project': [],
            'framework': [],
            'global': []
        }

        # Check project location
        project_payments = os.path.join(self.cwd, 'payments')
        if os.path.exists(project_payments):
            installed['project'] = [
                d for d in os.listdir(project_payments)
                if os.path.isdir(os.path.join(project_payments, d))
                and os.path.exists(os.path.join(project_payments, d, 'manifest.json'))
            ]

        # Check framework location (if specified)
        if self.framework:
            framework_paths = [
                os.path.join(self.cwd, 'myproject', 'payments'),
                os.path.join(self.cwd, 'app', 'payments'),
                os.path.join(self.cwd, self.framework, 'payments'),
            ]

            for fpath in framework_paths:
                if os.path.exists(fpath):
                    installed['framework'] = [
                        d for d in os.listdir(fpath)
                        if os.path.isdir(os.path.join(fpath, d))
                        and os.path.exists(os.path.join(fpath, d, 'manifest.json'))
                    ]
                    break

        # Check global location
        if os.path.exists(self.global_providers_dir):
            installed['global'] = [
                d for d in os.listdir(self.global_providers_dir)
                if os.path.isdir(os.path.join(self.global_providers_dir, d))
                and os.path.exists(os.path.join(self.global_providers_dir, d, 'manifest.json'))
            ]

        return installed


# Convenience function
def load_provider(provider: str, framework: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function to load a provider

    Args:
        provider: Provider name
        framework: Optional framework name

    Returns:
        Provider dict or None
    """
    loader = ProviderLoader(framework)
    return loader.load_provider(provider)
