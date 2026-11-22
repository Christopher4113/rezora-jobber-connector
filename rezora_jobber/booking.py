"""CallOutcome -> BookingResult. Decision logic only; all I/O goes through the JobberClient passed in."""

from datetime import datetime, time, timedelta

from .jobber import JobberClient
from .models import BookingResult, CallOutcome

OPEN, CLOSE = time(8), time(18)  # business hours; ponytail: per-business setting in production
STEP = timedelta(minutes=30)


def overlaps(start: datetime, end: datetime, visits: list[dict]) -> bool:
    return any(v["startAt"] < end and start < v["endAt"] for v in visits)


def next_free_slot(start: datetime, minutes: int, visits: list[dict], days: int = 7) -> datetime | None:
    """First slot at or after `start`, on a 30-min grid, fully inside business hours, overlapping no visit."""
    dur = timedelta(minutes=minutes)
    t = start
    limit = start + timedelta(days=days)
    while t < limit:
        day_open = t.replace(hour=OPEN.hour, minute=0, second=0, microsecond=0)
        day_close = t.replace(hour=CLOSE.hour, minute=0, second=0, microsecond=0)
        if t < day_open:
            t = day_open
        elif t + dur > day_close:
            t = day_open + timedelta(days=1)
        elif overlaps(t, t + dur, visits):
            t += STEP
        else:
            return t
    return None


def details(o: CallOutcome) -> str:
    lines = [f"Caller: {o.caller_name or 'unknown'} ({o.phone})", f"Service: {o.service}"]
    if o.address:
        lines.append(f"Address: {o.address}")
    if o.urgency_reason:
        lines.append(f"Urgent: {o.urgency_reason}")
    if o.notes:
        lines.append(f"Notes: {o.notes}")
    if o.language == "es":
        lines.append("Caller speaks Spanish.")
    return "\n".join(lines) + "\nBooked by Rezora AI receptionist."


def book(o: CallOutcome, j: JobberClient) -> BookingResult:
    # 1. Never guess: missing phone or an unanswered question goes to a human, nothing touches Jobber.
    if o.needs_human or not o.phone:
        why = "no callback number" if not o.phone else "caller asked something the agent couldn't answer"
        return BookingResult(action="needs_human", message=f"Call back needed ({why}): {o.service}.")

    # 3 (before 2, because a Request needs a client). Find or create the client by phone.
    c = j.find_client_by_phone(o.phone) or j.create_client(o.caller_name, o.phone, o.address)

    # 2. Emergencies go to the owner now, never onto next week's schedule.
    if o.urgent:
        r = j.create_request(c["id"], f"URGENT: {o.service}", details(o))
        return BookingResult(action="urgent_escalated", jobber_client_id=c["id"], jobber_request_id=r["id"],
                             jobber_url=r["jobberWebUri"],
                             message=f"Owner should call back now: {o.urgency_reason or o.service}.")

    # 4. No agreed slot -> a Request the office can quote/schedule.
    if not o.requested_start:
        r = j.create_request(c["id"], o.service, details(o))
        return BookingResult(action="request_created", jobber_client_id=c["id"], jobber_request_id=r["id"],
                             jobber_url=r["jobberWebUri"], message=f"New request from {c['name']}: {o.service}.")

    # A Job needs a property; add the address from the call if the client has none.
    prop = c.get("property_id") or (j.add_property(c["id"], o.address) if o.address else None)
    if not prop:
        r = j.create_request(c["id"], o.service, details(o) + "\nNo service address given; confirm before scheduling.")
        return BookingResult(action="request_created", jobber_client_id=c["id"], jobber_request_id=r["id"],
                             jobber_url=r["jobberWebUri"],
                             message=f"Request created for {c['name']}: no service address, confirm before booking.")

    # 5. Only book open slots.
    start = o.requested_start
    end = start + timedelta(minutes=o.duration_minutes)
    visits = j.visits_between(start.replace(hour=0, minute=0), start + timedelta(days=8))
    if overlaps(start, end, visits):
        nxt = next_free_slot(start, o.duration_minutes, visits)
        when = nxt.strftime("%a %b %-d, %-I:%M %p") if nxt else "none in the next 7 days"
        return BookingResult(action="conflict", jobber_client_id=c["id"], scheduled_start=nxt,
                             message=f"{start:%a %-I:%M %p} is taken; next free slot: {when}.")

    # 6. Book it.
    job = j.create_job_with_visit(prop, o.service, start, o.duration_minutes, details(o))
    return BookingResult(action="job_booked", jobber_client_id=c["id"], jobber_job_id=job["id"],
                         jobber_url=job["jobberWebUri"], scheduled_start=start,
                         message=f"Booked {o.service} for {c['name']}, {start:%a %b %-d at %-I:%M %p}.")
