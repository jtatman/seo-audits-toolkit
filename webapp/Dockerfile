FROM python:3.12-slim

WORKDIR /opt/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

VOLUME ["/data"]
EXPOSE 5000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
