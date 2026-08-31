FROM python:3.10-slim

WORKDIR /home/app

COPY services/pricing-service/requirements.txt services/pricing-service/requirements.txt
RUN pip install --no-cache-dir -r services/pricing-service/requirements.txt

COPY shared shared
COPY services/pricing-service/app services/pricing-service/app

WORKDIR /home/app/services/pricing-service/app

EXPOSE 8002

CMD ["python", "main.py"]