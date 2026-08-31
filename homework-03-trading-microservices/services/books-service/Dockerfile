FROM python:3.10-slim

WORKDIR /home/app

COPY services/books-service/requirements.txt services/books-service/requirements.txt
RUN pip install --no-cache-dir -r services/books-service/requirements.txt

COPY shared shared
COPY services/books-service/app services/books-service/app

WORKDIR /home/app/services/books-service/app

EXPOSE 8004

CMD ["python", "main.py"]