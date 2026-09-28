FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKSPACE_HOST=0.0.0.0 \
    WORKSPACE_PORT=5200 \
    WORKSPACE_DATA_DIR=/var/lib/personal-workspace/data

WORKDIR /app
COPY workspace_server.py ./
COPY workspace ./workspace
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /var/lib/personal-workspace/data \
    && chown -R appuser:appuser /app /var/lib/personal-workspace
USER appuser
EXPOSE 5200
VOLUME ["/var/lib/personal-workspace/data"]
CMD ["python", "workspace_server.py"]
