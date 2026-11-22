# Demo video

About 48 s, recorded with [reshoot](https://pypi.org/project/reshoot/) in headless Chrome, so only the page is captured. Wide shots by default, with four deliberate zooms: the call transcript, the extracted details, the booking with its green row on the Jobber schedule, and the emergency escalation. The conflict case stays wide because the amber slot can be read without a zoom.

## Reshoot

Each take books real records in the Jobber test account, so every shoot needs a Monday whose week hasn't been used yet. Weeks used so far: 2026-11-30, 2026-12-07, 2026-12-14.

```bash
uv run uvicorn rezora_jobber.server:app --port 8000      # 1. demo server (needs a fresh JOBBER_ACCESS_TOKEN)
tools/demo/shoot.sh 2026-12-21                           # 2. seeds Tue 10:00 for the conflict case, records takes/web.mp4
reshoot check takes/web.assets.json takes/web.mp4 --review takes/review   # 3. look at every sheet
reshoot edit tools/demo/edit.py takes/web.mp4            # 4. cut: takes/rezora-jobber-demo.mp4, .srt, booked GIF
```

- `storyboard.py`: the beats, captions and zooms. `ZOOM = {"scale": 1.0}` turns off zoom-on-every-click, so only the `__demo.zoom()` calls move the camera.
- `edit.py`: trims at the `end` beat and adds an end card in rezora.io's colours.
- The page reads `?now=…&rate=2` to pin the call clock and replay speed.

`takes/` is git-ignored.
