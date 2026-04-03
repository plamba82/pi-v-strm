 FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Install Locust
RUN pip install locust

COPY app/main.py .

# Install browsers
RUN playwright install --with-deps

CMD ["locust", "-f", "locustfile.py", "--host=https://www.youtube.com"]