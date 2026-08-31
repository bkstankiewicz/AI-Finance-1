FROM python:3.10-slim

WORKDIR /home/app

COPY services/monitoring_service/requirements.txt services/monitoring_service/requirements.txt
RUN pip install --no-cache-dir -r services/monitoring_service/requirements.txt

COPY shared shared
COPY services/monitoring_service/app services/monitoring_service/app

WORKDIR /home/app/services/monitoring_service/app

EXPOSE 8003

CMD ["python", "main.py"]