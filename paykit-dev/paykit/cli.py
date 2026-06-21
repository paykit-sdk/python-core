"""
Main CLI entry point
"""

import click
from paykit.commands.init import init_command
from paykit.commands.set import set_command
from paykit.commands.add import add_command


@click.group()
@click.version_option()
def cli():
    """PayKit - Payment provider integration toolkit"""
    pass

cli.add_command(init_command, name="init")
cli.add_command(set_command, name="set")
cli.add_command(add_command, name="add")


if __name__ == "__main__":
    cli()
