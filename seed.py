"""Seed the Jobber test account: 3 fake clients and one job on the demo's "tomorrow" at 10:00.

python seed.py            # job on 2026-11-24 10:00 (tomorrow relative to the demo's --now)
python seed.py 2026-12-01 # pick another date
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from rezora_jobber.env import load_env
from rezora_jobber.jobber import JobberClient

load_env()
tz = ZoneInfo(os.environ.get("BUSINESS_TZ", "America/New_York"))
day = sys.argv[1] if len(sys.argv) > 1 else "2026-11-24"
j = JobberClient()

clients = [
    ("Dana Whitfield", "+16175550142", "18 Elm St, Newton, MA 02458"),
    ("Marcus Lee", "+16175550177", "402 Beacon St, Boston, MA 02115"),
    ("Priya Raman", "+16175550199", "77 Walnut Park, Newton, MA 02458"),
]
made = []
for name, phone, addr in clients:
    c = j.find_client_by_phone(phone) or j.create_client(name, phone, addr)
    made.append(c)
    print("client", c["name"], c["id"])

start = datetime.fromisoformat(f"{day}T10:00").replace(tzinfo=tz)
existing = j.visits_between(start, start.replace(hour=11))
if existing:
    print("visit already at", start, "->", existing[0]["title"])
else:
    job = j.create_job_with_visit(made[0]["property_id"], "Water heater flush", start, 60, "Seeded for conflict demo")
    print("job", job["jobNumber"], job["jobberWebUri"], job["visits"]["nodes"])
