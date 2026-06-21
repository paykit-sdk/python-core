"""
Init command implementation

Initializes PayKit configuration and synchronizes providers with library.
"""

import click
from pathlib import Path

from paykit.core.config import Config
from paykit.core.fetcher import ProviderFetcher


@click.command()
@click.option(
    "--framework",
    default="django",
    help="Framework to use (default: django)"
)
@click.option(
    "--reload",
    is_flag=True,
    help="Force reload all providers from CDN"
)
def init_command(framework: str, reload: bool):
    """
    Initialize PayKit configuration

    Creates paykit.json in the current directory and synchronizes
    providers with the library installation.
    """
    config = Config()

    # Initialize or load configuration
    if config.config_exists():
        click.echo("Found existing paykit.json")
        try:
            config.load_config()
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            return
    else:
        click.echo("Initializing new paykit.json...")
        config.initialize(framework=framework)
        click.echo(f"✓ Created paykit.json with framework: {framework}")

    # Get configuration details
    cdn_url = config.get_cdn_url()
    current_framework = config.get_framework()
    providers = config.get_providers()

    if not providers:
        click.echo("No providers configured")
        return

    click.echo(f"\nSynchronizing {len(providers)} provider(s)...")

    # Initialize fetcher
    fetcher = ProviderFetcher(cdn_url, config.library_dir)

    # Track success/failure
    installed = []
    failed = []

    # Process each provider
    for provider_name, version in providers.items():
        try:
            # Check if provider needs installation/reload
            needs_install = reload or not config.is_provider_installed(provider_name)

            if needs_install:
                if reload and config.is_provider_installed(provider_name):
                    click.echo(f"  Removing {provider_name} for reload...")
                    config.remove_provider_installation(provider_name)

                click.echo(f"  Fetching {provider_name} @ {version}...")
                fetcher.install_provider(
                    framework=current_framework,
                    provider_name=provider_name,
                    version=version,
                    force=reload
                )

                # Verify installation
                if fetcher.verify_installation(provider_name):
                    installed.append(provider_name)
                    click.echo(f"  ✓ Installed {provider_name}")
                else:
                    failed.append(provider_name)
                    click.echo(f"  ✗ Installation verification failed for {provider_name}", err=True)
            else:
                click.echo(f"  ✓ {provider_name} already installed")
                installed.append(provider_name)

        except Exception as e:
            failed.append(provider_name)
            click.echo(f"  ✗ Failed to install {provider_name}: {e}", err=True)

    # Remove obsolete providers (installed but not in config)
    installed_providers = config.get_installed_providers()
    configured_providers = set(providers.keys())
    obsolete = installed_providers - configured_providers

    if obsolete:
        click.echo(f"\nRemoving {len(obsolete)} obsolete provider(s)...")
        for provider_name in obsolete:
            try:
                config.remove_provider_installation(provider_name)
                click.echo(f"  ✓ Removed {provider_name}")
            except Exception as e:
                click.echo(f"  ✗ Failed to remove {provider_name}: {e}", err=True)

    # Summary
    click.echo(f"\n{'=' * 50}")
    click.echo(f"Framework: {current_framework}")
    click.echo(f"Successfully installed: {len(installed)}")
    if failed:
        click.echo(f"Failed: {len(failed)}")
    if obsolete:
        click.echo(f"Removed obsolete: {len(obsolete)}")
    click.echo(f"{'=' * 50}")
