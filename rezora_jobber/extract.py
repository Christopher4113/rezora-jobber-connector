"""transcript -> CallOutcome. The only file that knows which LLM we use (Groq via its OpenAI-compatible API)."""

import json
import os
from datetime import datetime, timedelta

from openai import OpenAI
from pydantic import ValidationError

from .models import CallOutcome

SYSTEM = """You turn a phone call transcript between an AI receptionist ("Agent") and a caller into JSON.
The business is a home services company (HVAC, plumbing, roofing).

Output ONE JSON object matching this JSON schema exactly:
{schema}

Rules:
- Never invent a phone number, address or time. If the caller did not clearly say it, use null.
- phone: E.164 (+1XXXXXXXXXX for US numbers) when the digits are clear.
- urgent = true ONLY for: active water leak or burst pipe, no heat in cold weather, no AC in extreme heat,
  gas smell, sparking or electrical burning, roof open to rain. Put the reason in urgency_reason.
- requested_start: the appointment time the agent and caller AGREED on, as ISO 8601 with offset, in the
  business timezone. Resolve relative times ("tomorrow at 10", "Wednesday") against now = {now} ({tz}),
  using this calendar of the coming days: {days}. Null if no time was agreed.
- duration_minutes: 60 unless the agent stated a different length.
- Spanish calls: write every field in English and set language = "es".
- needs_human = true if the caller asked something the agent could not answer and promised a callback or transfer.
- service: short English label of the work, e.g. "AC tune-up", "leak inspection".
- notes: anything else the technician should know (gate code, pets, access), or null.
"""


def extract(transcript: str, now: datetime, tz: str) -> CallOutcome:
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"])
    messages = [
        {"role": "system", "content": SYSTEM.format(
            schema=json.dumps(CallOutcome.model_json_schema()), now=f"{now:%A} {now.isoformat()}", tz=tz,
            # LLMs get weekday arithmetic wrong; spell out the next week instead.
            days=", ".join(f"{d:%A} = {d:%Y-%m-%d}" for d in (now + timedelta(days=i) for i in range(8))))},
        {"role": "user", "content": transcript},
    ]
    for attempt in range(2):
        resp = client.chat.completions.create(
            model=os.environ["GROQ_MODEL"],
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        try:
            return CallOutcome.model_validate_json(raw)
        except ValidationError as e:
            if attempt:
                raise ValueError(f"LLM output failed validation twice: {e}") from e
            messages += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": f"That JSON failed validation:\n{e}\nReturn corrected JSON only."}]
