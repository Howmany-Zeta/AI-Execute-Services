#!/usr/bin/env python
from app.tasks import celery_app

# This file allows you to run the Celery worker directly with:
# python celery_worker.py
# It's also used in docker-compose.yml

if __name__ == '__main__':
    celery_app.worker_main(["worker", "--loglevel=info"])