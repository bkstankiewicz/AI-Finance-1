FROM python:3.10-slim

WORKDIR /home/app

COPY services/trade-generation-service/requirements.txt services/trade-generation-service/requirements.txt
RUN pip install --no-cache-dir -r services/trade-generation-service/requirements.txt

COPY shared shared
COPY services/trade-generation-service/app services/trade-generation-service/app

WORKDIR /home/app/services/trade-generation-service/app

EXPOSE 8007

CMD ["python", "main.py"]