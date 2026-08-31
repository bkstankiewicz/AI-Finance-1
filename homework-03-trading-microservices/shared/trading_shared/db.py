import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://trading:trading@localhost:5432/trading"
)

engine = create_engine(DATABASE_URL)
SessionFactory = sessionmaker(bind=engine)
