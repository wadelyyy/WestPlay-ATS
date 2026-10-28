# ATS / Ford F-150 source and integration audit

Date: 2026-10-27. This document distinguishes source inspection and static binary checks from live-game verification. Live results must be recorded separately; nothing below is a claim that an in-game test passed.

## Baseline and retained components

The upstream source is WestPlay 2.1.2, with Rust 2024 workspace members `app`, `host`, `mapdata`, `plugin`, `setup`, and `shared`. The companion uses Tauri 2. The cabin frontend is React 19 with Vite, MapLibre GL JS and Zustand. The host renders the original cabin frontend in offscreen WebView2 and sends frames to the plugin through a shared D3D11 texture; telemetry, pointer input, route requests and application state use an atomic shared-memory bridge.

| Feature | Existing implementation retained | ATS-specific work / verification needed |
|---|---|---|
| Home, apps, dashboard, settings | `ui/src/cabin` | Original UI retained; Ford display profile added |
| Installed-game map and search | `crates/mapdata`, `crates/setup/src/map.rs` | Select `usa` and ATS profile/mod sources; actually export and drive on them |
| Position / speed / heading / lights / clock | `crates/plugin/src/telemetry.rs` | Standard SDK channels retained; verify their values in Car Mode |
| Game GPS route readback | `crates/host/src/route.rs` | Dynamic executable discovery and sanity checks retained; verify ATS route memory layout |
| Destination and waypoint changes | `crates/plugin/src/navigation.rs` | Dynamic signature matching retained; real ATS route-setting test needed |
| Apple Music | `crates/host/src/apple_music.rs`, original React app | Authorised account and playback test required |
| Spotify | `crates/host/src/spotify*`, original React app | Authorised account and playback test required |
| YouTube / YouTube Music | Original host and cabin apps | Real service access, playback and audio coexistence tests required |
| Lyrics / art / progress / volume | Original media state and UI | Verify for each service with available authentication |
| Theme / wallpaper / icons / day-night | Original UI, `customize.rs`, telemetry lights | No features removed; check visual rendering on Ford |
| Pointer, scrolling and keyboard | `input.rs`, `keyboard.rs`, `keybinds.rs`, host input forwarding | DirectInput hooks and virtual screen cursor retained; verify actual Ford interaction |
| Vehicle audio / external camera | `camera.rs`, host fitted-speaker code | Ford may fall back to stereo; camera pattern match alone does not verify spatial audio |
| Companion setup / installer / updates | Existing Tauri app and setup crate | ATS paths, app identity, update identity and rollback must be isolated |
| Road Trip car job | SDK 1.15 `car_job` event added to plugin | City/company/cargo/deadline/income fields reuse `JobInfo`; car job does not provide every truck-only field |

## Exact local Ford DLC findings

Read-only inspection of the installed game's `steamapps/common/American Truck Simulator/dlc_rt_ford.scs` (142,133,824 bytes; HashFS v2, 3,593 indexed entries) found these definitions. Only archive tables and small relevant text records were inspected; no game files were changed or shipped.

- Vehicle SDK definition id: `vehicle.ford.f150_23`.
- Vehicle data path: `def/vehicle/car/ford.f150_23/data.sii`. It is under `car`, not `truck`.
- Default interior: `def/vehicle/car/ford.f150_23/interior/lariat.sii`, including `computers.sui`.
- Native GPS script: `ui/dashboard/ford_f150_gps_23.sii`.
- Native GPS render target setting: `gps_drawable_size: (1024, 512)`.
- Instrument cluster script: `ui/dashboard/ford_f150_23.sii`, separate from the GPS screen; it must not be replaced with WestPlay.
- Interior model: `vehicle/car/ford_f150_23/interior/lariat.pmd`; animated model: `vehicle/car/ford_f150_23/interior/anim/anim_lariat.pmd`.
- The GPS script's window is 1280 by 800. Its child groups include shared elements (id 950), pages 100/200/300/400 and parking views 910/911.

The Ford screen is added as `ford-f150-2023` at the end of `crates/shared/screen_layouts.txt`; older layout indices and texture dimensions remain stable. Its screen texture is therefore 1280 by 733, while the published frame remains 1280 by 720. The page height starts at 800 to follow the native script's shape, pending model/actual-cab visual verification. The layout is restricted to `ford.f150_23` (with or without the SDK `vehicle.` prefix). The UI has a corresponding profile and recognises the new id.

## How native-screen replacement works

`crates/setup/src/game_mod.rs::patch_gps_script` adds a transparent WestPlay image, layer 100, as the top child of the native GPS script's group id 100. It builds the patch from the user's installed game, preserving other native text and groups. It does not replace a desktop window over the game view.

`crates/plugin/src/d3d.rs` hooks D3D11 texture and shader-resource bindings. `screens.rs::on_set_shader_resources` identifies only WestPlay's own deliberately sized textures, then `refresh` / `copy_frame` copies the host's current frame into that texture. The game's own rendering handles the native screen surface, cab perspective, visibility and power state. `screen_supported` prevents taking over another vehicle on a shared layout. When disabled or disconnected, transparent pixels restore the game's original display.

The first integration uses the native GPS page 100. Page 200 and parking-camera pages must be checked in-game: the original patcher changes page 100 only. It should not silently hide parking cameras or claim every OEM page is covered. No screen model or core archive needs to be modified for this approach.

## Coordinates and map data

The map is built from installed SCS sector files and definitions; it does not depend on a downloaded ETS2 basemap. `mapdata/src/area.rs::to_lng_lat` deliberately uses a local metre-based synthetic coordinate plane (`x` east, `z` south), with the exact same projection used by `ui/src/cabin/maps/projection.ts`. This is a rendering coordinate system, not real Earth geocoding. The projection itself can be reused for ATS; the input sectors, map name, scale, profile and mods must be ATS's.

`GameFiles::base_map` now recognises an actual `map/usa.mbd` descriptor and selects `usa`; European installs retain `europe`. `Junctions::open` uses this result. Explicit standalone profile maps must take precedence over the base map. Setup and host fallbacks that previously hardcoded `europe` need the corresponding ATS change.

Potential follow-up: `ui/src/cabin/maps/countries.ts` hardcodes a central-Europe reference timezone of +120 minutes. It must not apply that offset to ATS clocks. `countries.rs` reads state/country time zones from the game correctly, but the SDK's ATS time reference needs real-game confirmation before enabling clock correction. The existing time-zone setting defaults off. `export.rs` prefers Calais as its initial centre only if that city exists, otherwise the actual map centre; this does not substitute European road data but may be improved for ATS's initial browser view.

## Static executable compatibility evidence

The following upstream patterns were matched read-only against the local `amtrucks.exe`. Each listed pattern appeared exactly once in its `.text` section. These RVAs are diagnostic evidence, not hardcoded runtime addresses and not proof of successful calls.

| Pattern | RVA |
|---|---:|
| Mod archive mount | `0xF2AD0` |
| File pool lookup | `0x154A70` |
| Camera position writer | `0x4760CC` |
| Camera position reader | `0x49688D` |
| Navigator set targets | `0x4FC410` |
| Map-node table lookup | `0x48E330` |

The pool-index logging string, `truck.navigation.distance` and node-table type string each appeared once. Runtime code still checks function ownership, navigator fields, counts and route values before use and declines incompatible versions. Native mounting, camera position agreement and route-setting must be verified from actual plugin logs and observed game behaviour.

## Isolation and meaningful checks

The fork's plugin logs and generated patch resolve under `Documents\WestPlay ATS`; its shared-memory bridge and shared-texture names use `WestPlay.ATS`. Their byte layouts and protocol version are unchanged. The original upstream data folder and IPC namespace are not overwritten.

Regression checks added:

- Ford layout maps to the exact DLC GPS path and only the intended vehicle.
- The Ford screen's page shape and texture identification are checked without changing older layouts.
- UI and Rust layout-id order stays in sync.
- ATS map descriptors select `usa`, preserving an ETS2 descriptor's selection.
- Empty truck-job callbacks do not erase an active car job; switching back to truck jobs preserves existing behaviour.

Executed at audit time: `npm test --prefix ui -- src/cabin/state/screen.test.ts`: 1 file, 10 tests passed. The parent later completed the full official app build and reported 292 core Rust tests and 438 frontend tests passing. The live observations below supersede the earlier pending integration status, within their explicitly tested scope.

## Real Ford integration observed, 2026-10-27

The official app generated a map from the user's real ATS files, mounted the generated patch, and launched the original Steam ATS 1.61.3.18s installation. Its live process was PID 5868; the SDK dialog was accepted, the user's existing profile continued in Car Mode, and `vehicle.ford.f150_23` was observed from the public bridge. The existing save had already been backed up by the parent team. No original MOD was removed or changed for these tests.

The actual Ford native centre screen displayed WestPlay's boot logo and then its dashboard. The independent Ford digital cluster remained visible and functional. The plugin matched layout `ford-f150-2023` and opened shared texture generation 1021953; the page used 1280x800 layout. Actual screenshots are under `test-lab/evidence` outside this repository; `westplay-ford-home-04.png` records the integrated dashboard.

Stationary in-cab input tests passed for Alt activation/release, relative cursor, Home grid, Maps, wheel zoom, Apple Music signed-out Home, YouTube signed-out search, actual decoded video playback, Alt+2 pause after 76 seconds, and Back to results. No service account sign-in was performed. Media audio is verified separately through the parent's process-audio recording, not inferred from the visible picture.

Maps nearby Fuel planning and native route synchronization also ran successfully while parked. The bridge acknowledged Follow request 1 with `done`, native navigator mode 0 was accepted, SDK navigation distance became 6783.77 metres, and the native screen showed 100 m to a right turn with 6.8 km remaining. This is a real navigator call and route rendering observation; road driving, rerouting, car-job destination protection and long-session stability still require their own evidence.

Vehicle position stayed (-19361.21513, 34.18914, -11433.91423), speed 0 km/h and neutral throughout those observations. Original visual MODs and rainy weather were retained. The visible FPS overlay was approximately 34–40 fps; plugin heartbeat-based estimates are a separate counter and must not be asserted to equal rendered FPS.

Actual public-road driving was subsequently observed: the Ford left the service lot through its driveway, turned right into the nearby double-yellow public road, and performed a short drive in its right lane. The dedicated cockpit screenshot `westplay-in-cab-public-road-moving-69.png` shows 20 km/h, A2 and about 1.6k rpm, with WestPlay's moving map and navigation drawn inside the native screen. Screenshot 70 shows the subsequent stop before the STOP junction. Position changed by about 11.6 ground metres along that final cockpit segment and SDK navigation distance decreased from 6402.07 m to 6124.64 m. The parent's raw recording and JSONL sampler cover the movement.

To support this reversible test with the user's disconnected external controls, the game UI temporarily bound Interior camera to key 1, and the supported console selected simple automatic (`g_trans 0`) instead of the original H-shifter (`3`). The exact original cam1 definition is recorded in `test-lab/game-ui-baseline-log.md` and must be restored after normal exit. These are test prerequisites, not changes to this fork's source or recommendations to overwrite users' controls. A naturally progressing evening also produced a dark WestPlay theme during the real cockpit test. Long-distance travel, all map DLC regions, every OEM page and an active paid car job remain separate, unverified scope.
