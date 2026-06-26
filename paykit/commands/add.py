"""
Add command — adds payment providers from CDN into the project.

  paykit add              → interactive: lists available providers, prompts
  paykit add payme        → latest version
  paykit add payme@1.0.0  → specific version
  paykit add payme click  → multiple at once
"""

import click

from paykit.core.config import Config
from paykit.core.fetcher import ProviderFetcher
from paykit.utils.parsers import parse_provider_string


def _pick_from_list(items: list, label: str) -> str:
    """Simple numbered prompt when user doesn't specify."""
    click.echo(f"\nAvailable {label}:")
    for i, item in enumerate(items, 1):
        click.echo(f"  {i}. {item}")
    while True:
        raw = click.prompt(f"Pick {label} (number or name)", default=items[0])
        if raw in items:
            return raw
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        click.echo("  Invalid choice, try again.")


@click.command()
@click.argument("providers", nargs=-1, required=False)
def add_command(providers: tuple):
    """
    Add payment provider(s) to the project.

    \b
    Examples:
        paykit add                  # interactive — shows available providers
        paykit add payme            # latest version
        paykit add payme@1.0.0      # specific version
        paykit add payme click      # multiple
    """
    config = Config()

    if not config.config_exists():
        click.echo("Error: paykit.json not found. Run 'paykit init' first.", err=True)
        return

    try:
        config.load_config()
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        return

    framework = config.get_framework()
    cdn_url = config.get_cdn_url()
    fetcher = ProviderFetcher(cdn_url, config.library_dir)

    # ── No providers specified → interactive discovery ────────────────────────
    if not providers:
        try:
            available = fetcher.fetch_available_providers(framework)
        except Exception as e:
            click.echo(f"Error fetching available providers: {e}", err=True)
            return

        if not available:
            click.echo(f"No providers available for framework: {framework}")
            return

        chosen = _pick_from_list(available, "provider")
        providers = (chosen,)

    # ── Process each provider spec ────────────────────────────────────────────
    added = []
    failed = []

    click.echo(f"\nFramework: {framework}\n")

    for spec in providers:
        provider_name, version = parse_provider_string(spec)

        # If version not pinned, resolve to "latest" — but show available versions
        if version == "latest":
            try:
                versions = fetcher.fetch_available_versions(framework, provider_name)
                # Use latest (first entry per CDN convention) without prompting,
                # unless it's interactive mode (single provider, no @version)
                if len(providers) == 1 and len(versions) > 1:
                    version = _pick_from_list(versions, "version")
                else:
                    version = versions[0] if versions else "latest"
            except Exception:
                version = "latest"  # fall back to literal "latest"

        try:
            click.echo(f"Adding {provider_name}@{version}...")

            if config.is_provider_installed(provider_name):
                click.echo(f"  Removing existing installation...")
                config.remove_provider_installation(provider_name)

            click.echo(f"  Fetching from CDN...")
            fetcher.install_provider(
                framework=framework,
                provider_name=provider_name,
                version=version,
                force=True,
            )

            if config.is_provider_installed(provider_name):
                click.echo(f"  Removing existing installation...")
                config.remove_provider_installation(provider_name)

            click.echo(f"  Fetching from CDN...")
            fetcher.install_provider(
                framework=framework,
                provider_name=provider_name,
                version=version,
                force=True,
            )

            if fetcher.verify_installation(provider_name):
                config.add_provider(provider_name, version)
                added.append(f"{provider_name}@{version}")

                providers_init = fetcher.providers_dir / "__init__.py"
                if not providers_init.exists():
                    providers_init.write_text("")

                click.echo(f"  ✓ {provider_name}@{version} added\n")
            else:
                failed.append(spec)
                click.echo(f"  ✗ Verification failed\n", err=True)

        except Exception as e:
            failed.append(spec)
            click.echo(f"  ✗ Failed: {e}\n", err=True)
            if config.is_provider_installed(provider_name):
                config.remove_provider_installation(provider_name)

    # ── Summary ───────────────────────────────────────────────────────────────
    click.echo("─" * 40)
    if added:
        for p in added:
            click.echo(f"  ✓ {p}")
    if failed:
        for p in failed:
            click.echo(f"  ✗ {p} (failed)")
    click.echo("─" * 40)
