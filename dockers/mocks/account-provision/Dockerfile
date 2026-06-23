FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY provision_loop.py .

ENV UPSTREAM_API_URL=http://backend:8080
ENV AGENT_PSK=change-me-in-production
ENV PROVISION_POLL_INTERVAL=10
ENV MOCK_SERVER_COUNT=100

CMD ["python", "provision_loop.py"]
