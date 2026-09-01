FROM python:3.10-slim

WORKDIR /home/app

COPY db/requirements.txt db/requirements.txt
RUN pip install --no-cache-dir -r db/requirements.txt

COPY shared shared
COPY db db

WORKDIR /home/app/db

CMD ["alembic", "upgrade", "head"]
