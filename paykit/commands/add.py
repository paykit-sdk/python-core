"""
Add command implementation

Adds and installs payment providers to PayKit configuration.
"""

import click

from paykit.core.config import Config
from paykit.core.fetcher import ProviderFetcher
from paykit.utils.parsers import parse_provider_string



@click.command()
@click.argument("providers", nargs=-1, required=True)
def add_command(providers: tuple):
    """
    Add payment provider(s) to PayKit configuration

    Fetches providers from CDN and adds them to paykit.json.
    Supports version specifications using @ symbol.

    Args:
        providers: One or more provider specifications
                  (e.g., "payme", "payme@1", "click@3.4.0")

    Examples:
        paykit add payme
        paykit add payme@1 click@3.4
        paykit add stripe@2.1.5
    """
    config = Config()

    # Check if config exists
    if not config.config_exists():
        click.echo("Error: paykit.json not found. Run 'paykit init' first.", err=True)
        return

    try:
        # Load existing config
        config.load_config()
        framework = config.get_framework()
        cdn_url = config.get_cdn_url()

        # Initialize fetcher
        fetcher = ProviderFetcher(cdn_url, config.library_dir)

        # Track results
        added = []
        failed = []

        click.echo(f"Adding {len(providers)} provider(s) for framework: {framework}\n")

        # Process each provider
        for provider_spec in providers:
            provider_name, version = parse_provider_string(provider_spec)

            try:
                click.echo(f"Processing {provider_name} @ {version}...")

                # Remove existing installation if present
                if config.is_provider_installed(provider_name):
                    click.echo(f"  Removing existing installation...")
                    config.remove_provider_installation(provider_name)

                # Install provider
                click.echo(f"  Fetching from CDN...")
                fetcher.install_provider(
                    framework=framework,
                    provider_name=provider_name,
                    version=version,
                    force=True
                )

                # Verify installation
                if fetcher.verify_installation(provider_name):
                    # Add to configuration
                    config.add_provider(provider_name, version)
                    added.append(f"{provider_name} @ {version}")
                    click.echo(f"  ✓ Successfully added {provider_name}\n")
                else:
                    failed.append(f"{provider_name} @ {version}")
                    click.echo(f"  ✗ Installation verification failed\n", err=True)

            except Exception as e:
                failed.append(f"{provider_name} @ {version}")
                click.echo(f"  ✗ Failed: {e}\n", err=True)

                # Clean up on failure
                if config.is_provider_installed(provider_name):
                    config.remove_provider_installation(provider_name)

        # Summary
        click.echo(f"{'=' * 50}")
        if added:
            click.echo(f"Successfully added {len(added)} provider(s):")
            for provider in added:
                click.echo(f"  ✓ {provider}")

        if failed:
            click.echo(f"\nFailed to add {len(failed)} provider(s):")
            for provider in failed:
                click.echo(f"  ✗ {provider}")

        click.echo(f"{'=' * 50}")

    except FileNotFoundError:
        click.echo("Error: paykit.json not found. Run 'paykit init' first.", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
