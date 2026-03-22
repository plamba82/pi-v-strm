# pi-v-strm
docker build -t hello-world-app .

docker run --rm hello-world-app

#UI Mode
docker run -p 8081:8081 hello-world-app --host=https://www.youtube.com

#Headlesss
docker run locust-hls-test \
  --headless \
  -u 10000 \
  -r 200 \
  --host=https://yourdomain.com


# Master container
docker run -p 8089:8089 locust-hls-test \
  --master \
  --host=https://yourdomain.com
# Worker containers
(Replace <MASTER_IP> with your machine IP)
docker run locust-hls-test \
  --worker \
  --master-host=<MASTER_IP>

docker run locust-hls-test --worker --master-host=<MASTER_IP>
docker run locust-hls-test --worker --master-host=<MASTER_IP>
docker run locust-hls-test --worker --master-host=<MASTER_IP>

Docker YML:

version: "3"

services:
  master:
    build: .
    command: locust -f locustfile.py --master --host=https://yourdomain.com
    ports:
      - "8089:8089"

  worker:
    build: .
    command: locust -f locustfile.py --worker --master-host=master
    depends_on:
      - master
    deploy:
      replicas: 3

Run:

docker compose up --scale worker=5


docker stats
