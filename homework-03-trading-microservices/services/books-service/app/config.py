import os

SERVICE_NAME = "books-service"

HOST = os.environ.get('BOOKS_HOST', '0.0.0.0')
PORT = int(os.environ.get('BOOKS_PORT', 8004))

VALID_ASSET_CLASSES = ["EQUITY", "BOND", "FX", "COMMODITY", "FUTURES", "EUROPEAN_OPTION", "IRS"]

# Seeded on startup only when the Books table is empty
DEFAULT_BOOKS = [
    {"name": f"{asset_class}_BOOK_1", "expected_asset_class": asset_class}
    for asset_class in VALID_ASSET_CLASSES
]
