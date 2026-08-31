import os

SERVICE_NAME = "books-service"

HOST = os.environ.get('BOOKS_HOST', '0.0.0.0')
PORT = int(os.environ.get('BOOKS_PORT', 8004))
