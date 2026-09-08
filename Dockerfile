FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
	&& useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser . .
RUN mkdir -p /app/instance \
	&& chown appuser:appuser /app/instance

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]