# Showcase for iOS 15

This fork focuses on using a jailbroken **iPhone 13 Pro on iOS 15.0.2 with
Dopamine** as a dedicated wireless CarPlay display for a newer iPhone. It is
based on Showcase 1.0 Beta 5-3 and started with the settings persistence
problem reported in [upstream issue #38](https://github.com/amineross/showcase/issues/38).

## What this fork adds

- **Settings that survive a relaunch.** Showcase saves vehicle profiles,
  hotspot credentials, sound routing, display choices and other preferences
  in a private settings store. It imports readable settings from older builds,
  including the upstream Beta 5-3 settings backup.
- **Reversed landscape and notch clearance.** Enable **Flip Landscape
  Orientation** under **Settings → Display** to rotate the receiver interface
  and CarPlay by 180°. Showcase reserves space on the notch side in either
  direction and fits the full CarPlay image into the available area.
- **Reliable touch at the edge.** Drags that start inside the CarPlay image
  can finish at its edge when you lift your finger in the black margin.
- **More reliable startup and reconnection.** CarPlay services start when the
  Bluetooth helper reports readiness. The receiver handles split and grouped
  iAP2 packets, can retry a confirmed stale Bluetooth bond for a known phone,
  and reports pairing progress when pairing actually starts. Relaunch
  recovery limits waits for system commands and local authentication.

## Changes in v1.1.0

- Handles CarPlay requests split across encrypted records, including the
  iOS 27 connection sequence. Parses requests within the received buffer.
- Saves the receiver's CarPlay authentication identity for offline starts
  after a reboot or helper restart. It requests a certificate valid for up
  to a year and renews it ahead of expiry. iOS may issue a shorter certificate.
  Connect the receiver to the internet before its first authentication or
  when its saved certificate needs renewal.
- Starts Bluetooth as soon as the controller and helper are ready, with
  fewer fixed waits.
- Waits for the hotspot before recording network traffic and includes
  Share state and the Wi-Fi log in diagnostic exports.
- Adds Turkish and the upstream quality-default correction for older HSIC iPads.

## Install

1. Download the rootless `.deb` from the [latest release](https://github.com/TheMaxynator/showcase/releases/latest).
2. Stop any active CarPlay session and close Showcase. Open the package in
   Sileo and install it. The release upgrades the earlier fork test builds
   in place and uses the original Showcase package identifier.
3. Open Showcase on the receiver and complete its hotspot setup. Connect from
   the sending iPhone. You can change the orientation under
   **Settings → Display**.

The receiver's hotspot carries the wireless CarPlay session. See the
[original setup guide](https://aminerostane.com/articles/showcase/) for
receiver requirements, initial authentication and setup with a SIM-free receiver.

## Build from source

On Linux, provide an iPhoneOS 16 SDK, Clang, LLD and ldid. Use the official
Beta 5-3 rootless package as input to the rebuild script. The script compiles
and signs the app and both helpers and reuses the upstream Bluetooth runtime.

```bash
IOS_SDK=/path/to/iPhoneOS.sdk bash packaging/scripts/rebuild-rootless-app-deb.sh \
  /path/to/upstream-rootless.deb Showcase-iOS15-1.1.0-rootless.deb
```

## Upstream and credits

Showcase was created by [Amine Rostane](https://github.com/amineross/showcase).
The [original README at Beta 5-2](https://github.com/amineross/showcase/blob/34980e930a0b3245ffb6b49f22187630dac525ab/README.md)
covers the original features, diagnostics, anonymous usage, and build
variants. This fork also incorporates selected connection, display, touch,
and recovery fixes from [Showcase+](https://github.com/mymolasses/showcase).
The [release notes](https://github.com/TheMaxynator/showcase/releases/latest)
list the changes in detail.

[GPL-3.0-or-later](LICENSE).
