import asyncio
from datetime import datetime
from fastapi import HTTPException
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import time

from src.tasks.slow_task import slow_runner

class SlowTaskService():
    def run_service(self):
        slow_runner.delay(5)