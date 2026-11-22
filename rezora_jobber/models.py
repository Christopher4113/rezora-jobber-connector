from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CallOutcome(BaseModel):
    caller_name: str | None = None
    phone: str | None = None  # E.164 if possible; None when the caller never gave one
    address: str | None = None
    service: str  # "AC not cooling", "leak inspection", ...
    urgent: bool = False  # emergency per the business's rules
    urgency_reason: str | None = None  # "no heat, elderly resident"
    requested_start: datetime | None = None  # slot agreed on the call, business timezone
    duration_minutes: int = 60
    language: Literal["en", "es"] = "en"
    notes: str | None = None  # anything else worth passing to the tech
    needs_human: bool = False  # caller asked for something the agent couldn't answer


class BookingResult(BaseModel):
    action: Literal["job_booked", "request_created", "urgent_escalated", "conflict", "needs_human"]
    jobber_client_id: str | None = None
    jobber_job_id: str | None = None
    jobber_request_id: str | None = None
    jobber_url: str | None = None
    scheduled_start: datetime | None = None
    message: str  # one plain sentence for the owner/dashboard
