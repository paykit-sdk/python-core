"""
Set command implementation

Sets the framework in PayKit configuration.
"""

import click

from paykit.core.config import Config


@click.command()
@click.argument("framework")
def set_command(framework: str):
    """
    Set the framework in PayKit configuration

    Args:
        framework: Framework name to set (e.g., django, flask)
    """
    config = Config()

    # Check if config exists
    if not config.config_exists():
        click.echo("Error: paykit.json not found. Run 'paykit init' first.", err=True)
        return

    try:
        # Load existing config
        config.load_config()

        # Get current framework
        old_framework = config.get_framework()

        # Set new framework
        config.set_framework(framework)

        if old_framework == framework:
            click.echo(f"Framework is already set to: {framework}")
        else:
            click.echo(f"✓ Framework changed: {old_framework} → {framework}")
            click.echo("\nNote: You may need to run 'paykit init --reload' to update providers for the new framework.")

    except FileNotFoundError:
        click.echo("Error: paykit.json not found. Run 'paykit init' first.", err=True)
    except Exception as e:
        click.echo(f"Error setting framework: {e}", err=True)
