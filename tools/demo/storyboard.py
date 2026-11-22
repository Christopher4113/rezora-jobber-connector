"""Rezora -> Jobber demo, about 60 s. Run through tools/demo/shoot.sh, which seeds the shoot week first.

Wide shots by default. Four deliberate zooms, one per point the viewer must read:
  1. the call transcript playing   2. what was extracted   3. the job landing in Jobber   4. the emergency escalation
Every take books real records in the Jobber test account, so each shoot uses a fresh week (DEMO_NOW).
"""

import os

SIZE = "1280x720@1.5"
SETTLE = 3
# Zoom processing on, automatic zoom-on-every-click off (scale 1.0): only the __demo.zoom() calls below move the camera.
ZOOM = {"scale": 1.0, "watch": False}
NOW = os.environ.get("DEMO_NOW", "2026-11-30T09:00")  # a Monday; shoot.sh seeds a 10:00 visit on the Tuesday

URL = f"http://localhost:8000/?now={NOW}&rate=2"  # pins the call clock to the shoot week, replays at 2x

# window.span(a, b): an invisible box around two elements, so one zoom can frame both.
SPAN = """window.span = (a, b) => {
  const r = [a, b].map((s) => document.querySelector(s).getBoundingClientRect());
  const box = document.getElementById('zbox') || document.body.appendChild(Object.assign(document.createElement('div'), {id: 'zbox'}));
  const L = Math.min(r[0].left, r[1].left), T = Math.min(r[0].top, r[1].top);
  Object.assign(box.style, {position: 'absolute', pointerEvents: 'none', left: L + scrollX + 'px', top: T + scrollY + 'px',
    width: Math.max(r[0].right, r[1].right) - L + 'px', height: Math.max(r[0].bottom, r[1].bottom) - T + 'px'});
  return '#zbox';
}; """
RESULT = "() => document.querySelector('#result .result')"
SECTION = "section[aria-labelledby={}]"

BEATS = [
    # Wide: the pitch.
    ("intro", SPAN + "await __demo.waitFor(() => !document.querySelector('#sched .empty'), 15000); __demo.caption('Rezora calls, booked straight into Jobber', 'Jobber is “coming soon” on rezora.io')", 3.0),
    ("to_demo", "__demo.caption(null); await __demo.scroll(document.querySelector('#demo').getBoundingClientRect().top - 12)", 0.6),

    # Zoom 1: the call itself, so the words are readable.
    ("call", """
        __demo.caption('A caller books an AC tune-up');
        await __demo.click('#play');
        __demo.zoom('.tx-wrap', {scale: 1.6});
    """, 7.0),
    ("call_end", "await __demo.click('#play'); __demo.zoomOut()", 0.5),

    # Wide click, then Zoom 2: what the LLM pulled out. Nothing is guessed.
    ("send", """
        __demo.caption('Call ends, details extracted');
        await __demo.click('#run');
        await __demo.waitFor(""" + RESULT + """, 30000);
        __demo.zoom('""" + SECTION.format("h-heard") + """', {scale: 1.5});
    """, 3.2),

    # Zoom 3: the booking message plus its green row on the live Jobber schedule (not the whole tall card).
    ("booked", """
        __demo.zoomOut();
        await __demo.waitFor('#sched .visit.new', 15000);
        await __demo.sleep(700);
        __demo.caption('Booked into an open Jobber slot');
        __demo.zoom(span('#result .result', '#sched .visit.new'), {scale: 1.5});
    """, 3.4),
    ("booked_out", "__demo.zoomOut(); __demo.caption(null)", 0.6),

    # Wide: the taken slot is visible on the schedule without zooming.
    ("conflict", """
        __demo.caption('Taken slot? It never double-books', 'and offers the next free time');
        await __demo.click('.chip[data-k=leak_inspection_conflict]');
        await __demo.click('#run');
        await __demo.waitFor(() => document.querySelector('#result .t-conflict'), 30000);
    """, 3.4),

    # Zoom 4: the emergency goes to the owner, not onto the calendar.
    ("urgent", """
        __demo.caption('Emergencies go to the owner, now');
        await __demo.click('.chip[data-k=no_heat]');
        await __demo.click('#run');
        await __demo.waitFor(() => document.querySelector('#result .t-urgent_escalated'), 30000);
        __demo.zoom('#result', {scale: 1.7});
    """, 3.4),
    ("urgent_out", "__demo.zoomOut(); __demo.caption(null)", 0.6),

    # Wide: where it plugs in.
    ("fit", """
        await __demo.scroll(document.querySelector('#fit').getBoundingClientRect().top - 40);
        __demo.caption('One more row in setup step 3', 'CallOutcome in, BookingResult out');
    """, 3.2),
    ("end", "__demo.caption('Rezora × Jobber', 'prototype connector'); __demo.hide()", 2.0),
]
