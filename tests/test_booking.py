"""booking.py with a fake JobberClient: no network, no LLM."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest

from rezora_jobber.booking import book, next_free_slot
from rezora_jobber.jobber import JobberClient, JobberError, digits
from rezora_jobber.models import CallOutcome

NY = ZoneInfo("America/New_York")
TUE_10 = datetime(2026, 11, 24, 10, tzinfo=NY)


class FakeJobber:
    def __init__(self, clients=None, visits=None):
        self.clients = clients or []
        self.visits = visits or []
        self.calls = []

    def find_client_by_phone(self, phone):
        self.calls.append("find")
        return next((c for c in self.clients if digits(c["phone"]) == digits(phone)), None)

    def create_client(self, name, phone, address):
        self.calls.append("create_client")
        c = {"id": "C-new", "name": name, "phone": phone, "property_id": "P-new" if address else None}
        self.clients.append(c)
        return c

    def add_property(self, client_id, address):
        self.calls.append("add_property")
        return "P-added"

    def visits_between(self, start, end):
        self.calls.append("visits")
        return self.visits

    def create_job_with_visit(self, property_id, title, start, minutes, instructions):
        self.calls.append("create_job")
        return {"id": "J1", "jobberWebUri": "https://jobber/j1"}

    def create_request(self, client_id, title, details):
        self.calls.append(("create_request", title))
        return {"id": "R1", "jobberWebUri": "https://jobber/r1"}


def outcome(**kw):
    base = dict(caller_name="Dana Whitfield", phone="+16175550142", address="18 Elm St", service="Leak inspection")
    return CallOutcome(**{**base, **kw})


def visit(start, minutes=60):
    return {"startAt": start, "endAt": start + timedelta(minutes=minutes)}


def test_job_booked():
    j = FakeJobber()
    r = book(outcome(requested_start=TUE_10), j)
    assert r.action == "job_booked" and r.jobber_job_id == "J1" and r.scheduled_start == TUE_10


def test_request_created_when_no_slot():
    j = FakeJobber()
    r = book(outcome(), j)
    assert r.action == "request_created" and r.jobber_request_id == "R1"
    assert "create_job" not in j.calls


def test_urgent_never_creates_job():
    j = FakeJobber()
    r = book(outcome(urgent=True, urgency_reason="no heat, 84-year-old resident", requested_start=TUE_10), j)
    assert r.action == "urgent_escalated" and "call back now" in r.message
    assert ("create_request", "URGENT: Leak inspection") in j.calls
    assert "create_job" not in j.calls and "visits" not in j.calls


def test_conflict_suggests_next_free_slot():
    j = FakeJobber(visits=[visit(TUE_10)])
    r = book(outcome(requested_start=TUE_10), j)
    assert r.action == "conflict"
    assert r.scheduled_start == TUE_10 + timedelta(hours=1)
    assert "create_job" not in j.calls  # never double-book


def test_needs_human_when_phone_missing_never_touches_jobber():
    j = FakeJobber()
    r = book(outcome(phone=None, requested_start=TUE_10), j)
    assert r.action == "needs_human" and j.calls == []


def test_needs_human_flag():
    j = FakeJobber()
    assert book(outcome(needs_human=True), j).action == "needs_human" and j.calls == []


def test_phone_normalization_matches_existing_client():
    j = FakeJobber(clients=[{"id": "C1", "name": "Dana", "phone": "(617) 555-0142", "property_id": "P1"}])
    r = book(outcome(phone="+1 617.555.0142", requested_start=TUE_10), j)
    assert r.jobber_client_id == "C1" and "create_client" not in j.calls


def test_next_slot_stays_inside_business_hours():
    late = datetime(2026, 11, 24, 17, tzinfo=NY)
    slot = next_free_slot(late, 60, [visit(late)])
    assert slot == datetime(2026, 11, 25, 8, tzinfo=NY)  # 17:00 taken, 17:30 would end after 18:00
    # a block of visits pushes the slot forward in 30-min steps
    slot = next_free_slot(TUE_10, 60, [visit(TUE_10, 90)])
    assert slot == TUE_10 + timedelta(minutes=90)


def test_user_errors_raise_clear_exception():
    def handler(request):
        return httpx.Response(200, json={"data": {"jobCreate": {"job": None, "userErrors": [
            {"message": "Property can't be blank", "path": ["propertyId"]}]}}})

    j = JobberClient(token="t", version="2026-11-18")
    j.http = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(JobberError, match="Property can't be blank"):
        j.create_job_with_visit("P1", "x", TUE_10, 60, None)
