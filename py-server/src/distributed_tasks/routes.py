from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import json
from sqlalchemy.exc import IntegrityError
from typing import Annotated
import traceback

from .services import (
    SlowTaskService
)
from src import dependencies


router = APIRouter()


@router.get("/dist/slow-task")
def execute_slow_task(
    slow_task_service: Annotated[
        SlowTaskService,
        Depends(dependencies.get_slow_task_service)
    ]
):
    try:
        slow_task_service.run_service()
        return JSONResponse({"status": "Started !"})
    except Exception as e:
        raise HTTPException(500, str(e))