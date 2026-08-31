FROM python:3.10-slim

WORKDIR /home/app

COPY services/blotter-service/requirements.txt services/blotter-service/requirements.txt
RUN pip install --no-cache-dir -r services/blotter-service/requirements.txt

COPY shared shared
COPY services/blotter-service/app services/blotter-service/app

WORKDIR /home/app/services/blotter-service/app

EXPOSE 8006

CMD ["python", "main.py"]