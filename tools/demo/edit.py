"""Cut the web take into the finished demo: the take up to its end beat, then an end card, plus one GIF and subtitles.

    reshoot edit tools/demo/edit.py takes/web.mp4

Writes takes/rezora-jobber-demo.mp4, takes/rezora-jobber-demo.srt and takes/rezora-jobber-booked.gif.
"""
import sys, tempfile
from pathlib import Path

from reshoot import cut

# The words on screen
TITLE = "Rezora × Jobber"
TAGLINE = "Calls land as booked jobs. Emergencies go to the owner."
SMALL = "Prototype connector · CallOutcome in, BookingResult out"
BG, INK, GREY, PURPLE = (253, 252, 249), (17, 17, 20), (110, 106, 118), (146, 52, 234)  # rezora.io colours
W, H = 1920, 1080


def main(web):
    web = Path(web)
    b = cut.beats(web)
    out = web.parent
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        body = cut.trim(web, 0, b["end"], t / "web.mp4", fade_out=0.4)
        card = (cut.Card(W, H, BG).text(None, 400, TITLE, 104, 600, INK)
                .text(None, 560, TAGLINE, 44, 500, GREY).text(None, 660, SMALL, 30, 500, PURPLE))
        end = cut.still(card.save(t / "end.png"), 3, t / "end.mp4")
        cut.concat([body, end], out / "rezora-jobber-demo.mp4")
    cut.write_srt(cut.cues(web, 0, b["end"]), out / "rezora-jobber-demo.srt")
    cut.gif(web, b["call"], b["booked_out"], out / "rezora-jobber-booked.gif")  # call -> booked, for the README
    for f in ("rezora-jobber-demo.mp4", "rezora-jobber-booked.gif"):
        print(f"  {out / f}  {cut.duration(out / f):5.1f}s")


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["takes/web.mp4"]))
