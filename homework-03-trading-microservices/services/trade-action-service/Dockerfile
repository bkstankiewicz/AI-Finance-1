FROM python:3.10-slim

WORKDIR /home/app

COPY services/trade-action-service/requirements.txt services/trade-action-service/requirements.txt
RUN pip install --no-cache-dir -r services/trade-action-service/requirements.txt

COPY shared shared
COPY services/trade-action-service/app services/trade-action-service/app

WORKDIR /home/app/services/trade-action-service/app

EXPOSE 8008

CMD ["python", "main.py"]