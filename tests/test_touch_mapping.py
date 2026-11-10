"""Exercise the production aspect-fit touch mapping without UIKit."""

from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "source" / "Showcase.m").read_text()
geometry = source[source.index("/* BEGIN CarPlay touch geometry */"):
                  source.index("/* END CarPlay touch geometry */")]

harness = r"""
#include <assert.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
""" + geometry + r"""
int main(void) {
    uint16_t x, y;

    /* A wide CarPlay stream in a phone view with the notch inset on one side.
     * Coordinates here are local to the video view in either orientation. */
    assert(map_carplay_touch(796, 390, 2240, 1008, 398, 195, false, &x, &y));
    assert(x == 1120 && y == 504);
    assert(!map_carplay_touch(796, 390, 2240, 1008, 398, 2, false, &x, &y));
    assert(map_carplay_touch(796, 390, 2240, 1008, 398, 2, true, &x, &y));
    assert(x == 1120 && y == 0);
    assert(map_carplay_touch(796, 390, 2240, 1008, 820, 390, true, &x, &y));
    assert(x == 2240 && y == 1008);

    /* A narrower stream leaves black bars on the left and right. */
    assert(!map_carplay_touch(796, 390, 1024, 768, 20, 195, false, &x, &y));
    assert(map_carplay_touch(796, 390, 1024, 768, 20, 195, true, &x, &y));
    assert(x == 0 && y == 384);
    assert(map_carplay_touch(796, 390, 1024, 768, 780, 195, true, &x, &y));
    assert(x == 1024 && y == 384);

    /* Nothing can start before the stream and its display have valid sizes. */
    assert(!map_carplay_touch(0, 390, 2240, 1008, 398, 195, false, &x, &y));
    assert(!map_carplay_touch(796, 390, 0, 0, 398, 195, false, &x, &y));
    assert(!map_carplay_touch(796, 390, 2240, 1008, NAN, 195, true, &x, &y));
    puts("PASS: aspect-fit coordinates, black bars and drag release at the video edge");
}
"""

with tempfile.TemporaryDirectory(prefix="showcase-touch-") as directory:
    path = Path(directory)
    (path / "test.c").write_text(harness)
    subprocess.run(["clang", "-Wall", "-Wextra", "-Werror", str(path / "test.c"),
                    "-lm", "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True)
