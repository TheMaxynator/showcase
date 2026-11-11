"""Exercise the production preference store with independent app launches.

Run with clang on macOS or provide OBJCFLAGS and OBJCLIBS for GNUstep.
"""

import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "source" / "Showcase.m").read_text()
START = SOURCE.index("@interface ShowcasePreferences")
END = SOURCE.index("static ShowcasePreferences *showcase_preferences", START)
READER_START = SOURCE.index("static NSDictionary *read_preferences_file")
READER_END = SOURCE.index("static NSDictionary *legacy_showcase_preferences", READER_START)
LEGACY = SOURCE[READER_END:START]
# Supply an isolated legacy domain and files to the production migration code.
LEGACY = LEGACY.replace('[NSBundle mainBundle].bundleIdentifier', '@"ShowcaseMigrationTest"')
LEGACY = LEGACY.replace('@"/var/mobile/Library/Showcase/settings.plist"', 'legacyBackupPath')
LEGACY = LEGACY.replace('[[NSUserDefaults standardUserDefaults] persistentDomainForName:bundleID]',
                        'legacyCurrent')
LEGACY = LEGACY.replace('@[NSHomeDirectory(), @"/var/root", @"/var/mobile"]', '@[legacyHome]')

PREAMBLE = r"""
#import <Foundation/Foundation.h>
#include <assert.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>

static void ip_log(const char *message, ...) { (void)message; }
static NSString *legacyHome, *legacyBackupPath;
static NSDictionary *legacyCurrent;
"""

SCENARIOS = r"""
int main(int argc, char **argv) {
    assert(argc == 3);
    @autoreleasepool {
        NSString *directory = [NSString stringWithUTF8String:argv[1]];
        NSString *phase = [NSString stringWithUTF8String:argv[2]];
        legacyHome = [directory stringByAppendingString:@".legacy"];
        legacyBackupPath = [legacyHome stringByAppendingPathComponent:@"settings.plist"];
        assert([[NSFileManager defaultManager] createDirectoryAtPath:legacyHome
            withIntermediateDirectories:YES attributes:nil error:NULL]);
        assert(([@{
            @"apSSID": @"Old hotspot", @"apPassword": @"old-password",
            @"prioritizeVideoQuality": @(YES), @"videoWidth": @1024, @"videoHeight": @576
        } writeToFile:legacyBackupPath atomically:YES]));
        /* A partial system domain must retain the backup's hotspot details. */
        legacyCurrent = @{@"prioritizeVideoQuality": @(NO), @"qualityDefaultApplied": @(YES)};
        ShowcasePreferences *preferences = [[ShowcasePreferences alloc] initWithDirectory:directory];
        [preferences registerDefaults:@{@"startCarPlayOnLaunch": @(YES)}];
        assert([preferences boolForKey:@"startCarPlayOnLaunch"]);

        if ([phase isEqualToString:@"write"]) {
            assert([[preferences stringForKey:@"apSSID"] isEqualToString:@"Old hotspot"]);
            assert(![preferences boolForKey:@"prioritizeVideoQuality"]);
            assert(([preferences applyChanges:@{
                @"apSSID": @"New hotspot", @"apPassword": @"new-password",
                @"receiverAudioEnabled": @(YES), @"flipLandscape": @(YES)
            }]));
        } else if ([phase isEqualToString:@"reload"]) {
            assert([[preferences stringForKey:@"apSSID"] isEqualToString:@"New hotspot"]);
            assert([[preferences stringForKey:@"apPassword"] isEqualToString:@"new-password"]);
            assert([preferences boolForKey:@"receiverAudioEnabled"]);
            assert([preferences boolForKey:@"flipLandscape"]);
            assert(![preferences boolForKey:@"prioritizeVideoQuality"]);
            assert([preferences integerForKey:@"videoWidth"] == 1024);
            assert(([preferences applyChanges:@{
                @"videoWidth": [NSNull null], @"videoHeight": [NSNull null],
                @"flipLandscape": @(NO)
            }]));
        } else if ([phase isEqualToString:@"reset"]) {
            assert(![preferences objectForKey:@"videoWidth"]);
            assert(![preferences objectForKey:@"videoHeight"]);
            assert(![preferences boolForKey:@"flipLandscape"]);
        } else if ([phase isEqualToString:@"failed-write"]) {
            assert([preferences boolForKey:@"receiverAudioEnabled"]);
            NSString *backup = [directory stringByAppendingString:@".backup"];
            assert(rename(directory.fileSystemRepresentation, backup.fileSystemRepresentation) == 0);
            assert([@"file" writeToFile:directory atomically:YES encoding:NSUTF8StringEncoding error:NULL]);
            assert((![preferences applyChanges:@{@"receiverAudioEnabled": @(NO), @"flipLandscape": @(YES)}]));
            assert([preferences boolForKey:@"receiverAudioEnabled"]);
            assert(![preferences boolForKey:@"flipLandscape"]);
            assert(unlink(directory.fileSystemRepresentation) == 0);
            assert(rename(backup.fileSystemRepresentation, directory.fileSystemRepresentation) == 0);
        } else if ([phase isEqualToString:@"corrupt"]) {
            assert(![preferences stringForKey:@"apSSID"]);
            assert(![preferences setBool:YES forKey:@"flipLandscape"]);
        } else {
            assert(0);
        }
    }
}
"""

if sys.platform == "darwin":
    compile_flags, link_flags = ["-fobjc-arc"], ["-framework", "Foundation"]
else:
    compile_flags = shlex.split(os.environ["OBJCFLAGS"])
    link_flags = shlex.split(os.environ["OBJCLIBS"])

with tempfile.TemporaryDirectory() as temp:
    workspace = Path(temp)
    check = workspace / "check"
    code = check.with_suffix(".m")
    code.write_text(PREAMBLE + SOURCE[READER_START:READER_END] + LEGACY + SOURCE[START:END] + SCENARIOS)
    subprocess.run(["clang", *compile_flags, str(code), "-o", str(check), *link_flags], check=True)
    settings = workspace / "settings"
    for phase in ("write", "reload", "reset", "failed-write"):
        subprocess.run([str(check), str(settings), phase], check=True)

    data = settings / "Preferences.plist"
    assert settings.stat().st_mode & 0o777 == 0o700
    stored = plistlib.loads(data.read_bytes())
    assert stored["apPassword"] == "new-password" and stored["receiverAudioEnabled"]
    assert "startCarPlayOnLaunch" not in stored
    data.write_bytes(b"corrupt")
    subprocess.run([str(check), str(settings), "corrupt"], check=True)
    assert data.read_bytes() == b"corrupt"

print("PASS: migration, restart, grouped settings, defaults and write failure")
