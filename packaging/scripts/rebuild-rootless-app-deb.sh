#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 ]]; then
  echo "Usage: IOS_SDK=/path/to/iPhoneOS.sdk $0 upstream-rootless.deb output.deb" >&2
  exit 2
fi

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
UPSTREAM_DEB="$1"
OUTPUT_DEB="$2"
SDK="${IOS_SDK:?Set IOS_SDK to the iPhoneOS 16 SDK path}"
CLANG="${CLANG:-clang}"
LDID="${LDID:-ldid}"
. "$REPO/packaging/scripts/version.sh"

# Use the published Beta 5-2 rootless payload for the Bluetooth runtime.
EXPECTED_SHA=f91ab0bf7ddf94d9eb1eacc56db37e8943ea8f1dce60c4976f793d679707a1d6
ACTUAL_SHA="$(sha256sum < "$UPSTREAM_DEB" | cut -d ' ' -f 1)"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  echo "The input must be the official Showcase Beta 5-2 rootless package." >&2
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
ROOTFS="$WORK/rootfs"
APP="$ROOTFS/var/jb/Applications/Showcase.app"
SRC="$REPO/source"
BTSTACK="$ROOTFS/var/jb/usr/lib/libBTstack.dylib"
dpkg-deb --raw-extract "$UPSTREAM_DEB" "$ROOTFS"

FLAGS=(-target arm64-apple-ios12.0 -isysroot "$SDK" -fobjc-arc -Os -DSHOWCASE_ROOTLESS=1 -fuse-ld=lld)
"$CLANG" "${FLAGS[@]}" "-DAPP_VERSION=\"$DISPLAY_VERSION\"" "-DPACKAGE_VERSION=\"$PACKAGE_VERSION\"" \
  -o "$WORK/Showcase" "$SRC/Showcase.m" \
  -framework UIKit -framework AVFoundation -framework AudioToolbox \
  -framework CoreMedia -framework Foundation -framework Security \
  -framework CoreGraphics -framework QuartzCore
"$CLANG" "${FLAGS[@]}" -o "$WORK/CarDisplaySim" "$SRC/carplay_bt.m" "$BTSTACK" \
  -framework Foundation -framework Security
"$CLANG" "${FLAGS[@]}" -o "$WORK/CarPlay Simulator" \
  "$SRC/carplay_services.m" "$SRC/carplay_pair.c" \
  "$SRC/vendor/monocypher/monocypher.c" "$SRC/vendor/monocypher/monocypher-ed25519.c" \
  "$SRC/vendor/libtommath/tommath.c" -framework Foundation -framework Security -framework CoreFoundation

"$LDID" -S"$SRC/ent_app.xml" "$WORK/Showcase"
"$LDID" -S"$SRC/ent_bt.xml" "$WORK/CarDisplaySim"
"$LDID" -S"$SRC/ent_svc.xml" "$WORK/CarPlay Simulator"
install -m 4755 "$WORK/Showcase" "$APP/Showcase"
install -m 4755 "$WORK/CarDisplaySim" "$APP/CarDisplaySim"
install -m 4755 "$WORK/CarPlay Simulator" "$APP/CarPlay Simulator"
fill_version "$SRC/Info.plist" > "$APP/Info.plist"
for localization in "$SRC"/Localizations/*.lproj; do
  install -m 0644 "$localization/Localizable.strings" "$APP/${localization##*/}/Localizable.strings"
done
fill_version "$REPO/packaging/control-rootless/control" > "$ROOTFS/DEBIAN/control"

(
  cd "$ROOTFS"
  find var -type f -print0 | LC_ALL=C sort -z | xargs -0 md5sum > DEBIAN/md5sums
)
dpkg-deb --root-owner-group -Zgzip -z9 --build "$ROOTFS" "$OUTPUT_DEB"
