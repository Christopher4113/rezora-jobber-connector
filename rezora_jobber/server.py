"""uvicorn rezora_jobber.server:app --reload   ->  http://localhost:8000 (demo UI)

POST /calls/completed is the webhook Rezora would call when a call ends.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .booking import book
from .env import load_env
from .extract import extract
from .jobber import JobberClient, JobberError
from .models import BookingResult, CallOutcome

load_env()
ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Rezora → Jobber connector")


class CallCompleted(BaseModel):
    transcript: str
    now: str = "2026-11-23T09:00"
    timezone: str = "America/New_York"


class DemoRun(BaseModel):
    outcome: CallOutcome
    result: BookingResult
    extract_ms: int
    booking_ms: int


def _run(body: CallCompleted) -> DemoRun:
    now = datetime.fromisoformat(body.now)
    now = now if now.tzinfo else now.replace(tzinfo=ZoneInfo(body.timezone))
    try:
        t0 = time.perf_counter()
        outcome = extract(body.transcript, now, body.timezone)
        t1 = time.perf_counter()
        result = book(outcome, JobberClient())
    except JobberError as e:
        raise HTTPException(502, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    t2 = time.perf_counter()
    return DemoRun(outcome=outcome, result=result,
                   extract_ms=round((t1 - t0) * 1000), booking_ms=round((t2 - t1) * 1000))


@app.post("/calls/completed", response_model=BookingResult)
def calls_completed(body: CallCompleted):
    return _run(body).result


# --- demo UI helpers -------------------------------------------------------

@app.post("/demo/run", response_model=DemoRun)
def demo_run(body: CallCompleted):
    return _run(body)


@app.get("/demo/transcripts")
def transcripts():
    return {p.stem: p.read_text() for p in sorted((ROOT / "transcripts").glob("*.txt"))}


@app.get("/demo/schedule")
def schedule(start: str = "2026-11-23", days: int = 7, tz: str = "America/New_York"):
    s = datetime.fromisoformat(start).replace(tzinfo=ZoneInfo(tz))
    try:
        visits = JobberClient().visits_between(s, s + timedelta(days=days))
    except JobberError as e:
        raise HTTPException(502, str(e))
    return [{"title": v["title"], "client": v["client"]["name"],
             "start": v["startAt"].astimezone(ZoneInfo(tz)).isoformat(),
             "end": v["endAt"].astimezone(ZoneInfo(tz)).isoformat()} for v in sorted(visits, key=lambda v: v["startAt"])]


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")
