FROM python:3.10-slim

WORKDIR /home/app

COPY services/market-data-service/requirements.txt services/market-data-service/requirements.txt
RUN pip install --no-cache-dir -r services/market-data-service/requirements.txt

COPY shared shared
COPY services/market-data-service/app services/market-data-service/app

WORKDIR /home/app/services/market-data-service/app

EXPOSE 8001

CMD ["python", "main.py"]