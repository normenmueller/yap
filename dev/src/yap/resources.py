"""Application resources are independent of the selected portfolio."""
from pathlib import Path

APPLICATION = Path(__file__).resolve().parents[3]
DEVELOPMENT = APPLICATION / 'dev'
SOURCE = DEVELOPMENT / 'src'
RESOURCES = DEVELOPMENT / 'acc'
TEMPLATES = RESOURCES / 'templates'
ASSETS = RESOURCES / 'assets'
