FROM python:3.12-alpine
WORKDIR /app
RUN addgroup -S app && adduser -S -G app app && mkdir -p /data && chown app:app /data
COPY common.py service.py /app/
COPY data /app/data
USER app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
EXPOSE 8000
CMD ["python", "/app/service.py"]
