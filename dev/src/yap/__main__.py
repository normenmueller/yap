"""Run the application through the shared library CLI."""

from .cli import cli


if __name__ == '__main__':
    raise SystemExit(cli())
