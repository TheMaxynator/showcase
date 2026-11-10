"""Exercise the production bundle ID guard for local playback commands."""

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "source" / "Showcase.m").read_text()
policy = source[source.index("/* BEGIN Spotify target */"):source.index("/* END Spotify target */")]

harness = r"""
#import <Foundation/Foundation.h>
#include <assert.h>

""" + policy + r"""
int main(void) {
    @autoreleasepool {
        NSString *spotify = @"com.spotify.client";
        NSString *sideload = @"com.spotify.client.custom";
        NSString *music = @"com.apple.Music";

        assert(showcase_spotify_matches(spotify, nil));
        assert(showcase_spotify_matches(sideload, nil));
        assert(!showcase_spotify_matches(nil, nil));
        assert(!showcase_spotify_matches(music, nil));
        assert(!showcase_spotify_matches(@"com.spotify.clientfake", nil));
        assert(!showcase_spotify_matches(@"com.spotify.client.", nil));

        /* Changing players between the snapshot and the tap drops the command. */
        assert(showcase_spotify_matches(sideload, sideload));
        assert(!showcase_spotify_matches(spotify, sideload));
        assert(!showcase_spotify_matches(music, sideload));
        assert(!showcase_spotify_matches(nil, sideload));
        assert(!showcase_spotify_matches(music, music));
    }
}
"""

if sys.platform == "darwin":
    compile_flags, link_flags = ["-fobjc-arc"], ["-framework", "Foundation"]
else:
    compile_flags = shlex.split(os.environ["OBJCFLAGS"])
    link_flags = shlex.split(os.environ["OBJCLIBS"])

with tempfile.TemporaryDirectory(prefix="showcase-spotify-") as directory:
    path = Path(directory)
    (path / "test.m").write_text(harness)
    subprocess.run(["clang", *compile_flags, str(path / "test.m"),
                    "-o", str(path / "test"), *link_flags], check=True)
    subprocess.run([str(path / "test")], check=True)

print("PASS: local Spotify identity, repackaged bundle IDs and app-switch rejection")
