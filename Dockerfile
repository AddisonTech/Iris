FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY iris ./iris

EXPOSE 8011

# Override the broker/topic/clio args via the compose `command:` as needed.
CMD ["python", "-m", "iris", "serve", "--api-host", "0.0.0.0", "--api-port", "8011"]
