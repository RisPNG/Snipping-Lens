import sqlite3

import click

from .manager import default_db_path


@click.group()
@click.version_option()
def main():
    """Jupyter File ID server extension CLI."""
    pass


@main.command("drop")
def drop():
    """Drops the file ID table at the default path."""
    con = sqlite3.connect(default_db_path)
    con.execute("DROP TABLE Files;")
    con.commit()
    con.close()
    click.echo(f"Successfully dropped file ID table at path {default_db_path}")
