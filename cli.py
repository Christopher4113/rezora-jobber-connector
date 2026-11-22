"""python cli.py transcripts/no_heat.txt --now 2026-11-23T09:00 --tz America/New_York"""

import argparse
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from rezora_jobber.booking import book
from rezora_jobber.env import load_env
from rezora_jobber.extract import extract
from rezora_jobber.jobber import JobberClient

DEMO_NOW = "2026-11-23T09:00"  # fixed so "tomorrow at 10" always means the seeded day


def run(transcript: str, now: str = DEMO_NOW, tz: str = "America/New_York", jobber: JobberClient | None = None):
    t0 = time.perf_counter()
    outcome = extract(transcript, datetime.fromisoformat(now).replace(tzinfo=ZoneInfo(tz)), tz)
    t1 = time.perf_counter()
    result = book(outcome, jobber or JobberClient())
    t2 = time.perf_counter()
    return outcome, result, {"extract_ms": round((t1 - t0) * 1000), "booking_ms": round((t2 - t1) * 1000)}


if __name__ == "__main__":
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("transcript")
    p.add_argument("--now", default=DEMO_NOW)
    p.add_argument("--tz", default="America/New_York")
    a = p.parse_args()
    outcome, result, timing = run(open(a.transcript).read(), a.now, a.tz)
    print("CallOutcome\n" + outcome.model_dump_json(indent=2))
    print("\nBookingResult\n" + result.model_dump_json(indent=2))
    print(f"\nextract {timing['extract_ms']} ms, booking {timing['booking_ms']} ms")
