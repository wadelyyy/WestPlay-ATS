[简体中文](README.md) | **English**

# ATS WestPlay · Ford F-150 Community Port

Display maps, navigation and media on the **original dashboard screen of the official 2023 Ford F-150** in American Truck Simulator (ATS).

This project is **adapted from [enes-less/WestPlay](https://github.com/enes-less/WestPlay)**, which was originally built for Euro Truck Simulator 2. This fork is based on upstream **2.1.2**, commit [`0edc10bf44ffe57350cdf60c9d42bdc603f06eb3`](https://github.com/enes-less/WestPlay/commit/0edc10bf44ffe57350cdf60c9d42bdc603f06eb3). It retains the original author, contributor and third-party copyright and licence notices, and continues under **GPL-3.0-or-later**. The original upstream introduction is preserved in [README.upstream.md](README.upstream.md).

**[Download the installer](https://github.com/wadelyyy/WestPlay-ATS/releases/latest) · [Detailed installation and usage guide (Chinese)](docs/ATS-下载安装与使用.md) · [Features and test coverage (Chinese)](docs/ATS-功能对照表.md)**

This is an independent community adaptation, with no affiliation with or endorsement from SCS Software, Ford, Apple, Spotify or Google.

## Requirements

- Windows 10 / 11, 64-bit, and Microsoft Edge WebView2 Runtime.
- A working Steam installation of ATS, with the official **Road Trip: Ford DLC** owned and enabled.
- The DLC's **2023 Ford F-150**, with the game running in **DirectX 11** mode.
- The configuration tested in the actual game is **ATS 1.61.3.18s / DX11 / Windows x64 / 2023 Ford F-150**. Other game versions, vehicles and map mods require separate verification.

The installer does not include ATS, the Ford DLC, user saves or game map archives. Screen resources and map data are generated from your own installed game during initial setup.

## First installation

1. Open this repository's [Releases page](https://github.com/wadelyyy/WestPlay-ATS/releases/latest), expand **Assets**, and download the Windows installer whose name ends in **`_x64-setup.exe`**, such as `ATS-WestPlay_2.1.2_x64-setup.exe`. GitHub's `Source code (zip)` / `Source code (tar.gz)` downloads are source archives, not installers.
2. **Exit ATS normally**, run the installer, and choose the installation location and shortcuts you want.
3. Open **ATS WestPlay**. Follow the setup wizard to confirm the ATS game directory and deploy the plugin and screen resources. Wait for map preparation to finish, then complete the controls tutorial. If copying the plugin requires Windows permission, follow the prompt to grant it.
4. Keep WestPlay running. **Start ATS manually from Steam and select DirectX 11**, load your own save, and enter the official 2023 Ford F-150's cockpit.
5. Turn on the vehicle's electrical power, switch the original screen to its **GPS / navigation page**, and wait for WestPlay to appear.

**The desktop and Start menu shortcuts open only WestPlay; they do not automatically start ATS.** The two programs connect automatically once both are running, in either launch order. If needed, you can explicitly click **Launch ATS game** (`启动 ATS 游戏`) in WestPlay.

For detailed steps, controls, media sign-in and troubleshooting, see the [installation and usage guide (Chinese)](docs/ATS-下载安装与使用.md).

## Everyday use

Check the interaction key and mode on the companion app's **Controls** page. The default key is **Left Alt**: in hold mode, hold it while using the screen and release it to return to driving controls. With the press-once mode enabled, press once to enter screen interaction and again to leave. While interacting, use the mouse to click and the wheel to zoom the map.

The default media shortcuts use the main keyboard's number keys: **1 lowers volume, 2 plays/pauses, and 3 raises volume**. In hold mode, keep the interaction key held while pressing them; in press-once mode, enter screen interaction first. Your current bindings on the Controls page take precedence.

Use the map to search for destinations, find nearby facilities and send routes to the game's navigation. Signed-out public YouTube video playback, pause, return navigation and nonzero audio output have been verified. Apple Music, Spotify, YouTube Music and other services retain their official sign-in flows; accounts and subscriptions are authorized according to each service's requirements.

## Main changes from upstream

| Area | Changes in this fork |
| --- | --- |
| Game and vehicle | ATS discovery, Steam AppID, save and map paths; integration with the official 2023 Ford F-150's original GPS screen material |
| Maps and navigation | Generate data from the local ATS `usa` map and mounted DLC; connect ATS telemetry and game navigation |
| Time | Fix ATS cloud-save reading, load the base time zone from game definitions, and apply the current location's primary time zone |
| Companion app | Chinese ATS launch page, connection status, installation checks, logs, diagnostics, repair and safe uninstall |
| Startup | Open only the companion by default, with ATS started manually through Steam; retain an explicit game-launch button |
| Background recovery | Retry internal host/browser failures a bounded number of times and use unique texture generations across restarts to restore the dashboard connection |
| Project identity | Separate ATS application identity, data directory and IPC names to avoid mixing data with the original ETS2 branch |
| Updates and interface | Disable the upstream ETS2 updater; remove the “Support me” page and its launch command while retaining copyright and licence notices |

The original React cabin interface, WebView2 media implementation, D3D11 shared textures, input handling and account authorization flows remain in use.

## Actual game testing and limitations

The ATS version listed above has been tested in the actual game for the Ford's original dashboard screen, maps and mouse interaction, destination and navigation synchronization, short public-road driving, YouTube playback and audio output, day/night themes, connection to an already-running game, and automatic recovery after a controlled browser failure. Installed files and the desktop and Start menu shortcuts have also been checked.

Current coverage has these limits:

- Full long-distance trips, all map DLC, all map mods, all resolutions and extended stress testing have not been completed.
- Spotify and Apple Music subscription playback, YouTube Music, lyrics and complete account flows have not been verified end to end.
- `secondary timezone` subregion rectangles are not implemented; affected areas may show a one-hour time difference.
- Internal host/browser failures have bounded automatic recovery. If the entire WestPlay process exits, open the app again.
- Detecting Ford DLC files or a telemetry connection alone does not establish that the DLC is authorized or the dashboard display is working.

Detailed results and scope are documented in the [feature comparison (Chinese)](docs/ATS-功能对照表.md), [test record (Chinese)](docs/ATS-实测记录.md), [time-zone verification (Chinese)](docs/ATS-时区验证.md) and [background recovery verification (Chinese)](docs/ATS-后台恢复验证.md).

## Build from source

You need Windows x64, a Rust MSVC toolchain, Visual Studio C++ Build Tools and the Windows SDK, plus Node.js 24 / npm.

```powershell
npm ci
npm --prefix ui ci
npm --prefix ui test
powershell -NoProfile -ExecutionPolicy Bypass -File tools/package-ats.ps1
```

The script builds the native plugin, interface, Tauri app and NSIS installer. Installer output is in `target/release/bundle/nsis`. A successful build does not replace actual in-game verification.

## Credits and licence

Thank you to [enes-less](https://github.com/enes-less) and the [upstream WestPlay project](https://github.com/enes-less/WestPlay) for the original implementation. This repository is an ATS adaptation; the original author and third parties retain their respective rights.

The project uses the [GNU GPL, version 3 or later](LICENSE). Third-party sources and licences are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Game, vehicle and media-service names and logos belong to their respective owners.
