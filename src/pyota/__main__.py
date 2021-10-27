"""Command-line interface."""
import click


@click.command()
@click.version_option()
def main() -> None:
    """Pyota."""


if __name__ == "__main__":
    main(prog_name="pyota")  # pragma: no cover
