import time

from config.celery_app import celery_app

@celery_app.task
def slow_runner(number: int):
    print(f"Starting {number}")

    time.sleep(10)

    print(f"Finished {number}")

    return number