"""Opt-in: pytest -m live. Runs every transcript through Groq + the real Jobber test account.
Run `python seed.py` first. Creates real jobs/requests, so job_booked cases turn into conflicts on a rerun."""

from pathlib import Path

import pytest

from cli import run
from rezora_jobber.env import load_env

EXPECTED = {
    "ac_tune_up": "job_booked",
    "leak_inspection_conflict": "conflict",
    "no_heat": "urgent_escalated",
    "quote_no_time": "request_created",
    "plomeria_es": "job_booked",
}


@pytest.mark.live
@pytest.mark.parametrize("name,action", EXPECTED.items())
def test_transcript_end_to_end(name, action):
    load_env()
    text = (Path(__file__).resolve().parent.parent / "transcripts" / f"{name}.txt").read_text()
    outcome, result, timing = run(text)
    print(name, result.action, timing, result.message)
    assert result.action == action
