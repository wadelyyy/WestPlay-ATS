//! Windows launch and diagnostics for the ATS fork. Never stops a running game.

use crate::setup::SetupStore;
use serde::Serialize;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{AppHandle, Manager, State};
use westplay_setup::{
    game::{self, FoundBy, Game},
    game_mod, places, plugin,
};

#[derive(Default)]
pub(crate) struct LaunchState {
    pending: AtomicBool,
    map_ready: AtomicBool,
    map_failed: AtomicBool,
}

pub(crate) fn queue_launch(app: &AppHandle) {
    app.state::<LaunchState>().pending.store(true, Ordering::Release);
}

pub(crate) fn host_status(app: &AppHandle, status: &westplay_host::Status) {
    let state = app.state::<LaunchState>();
    let ready = matches!(status.map, westplay_host::maps::MapStatus::Ready);
    state.map_ready.store(ready, Ordering::Release);
    state.map_failed.store(matches!(status.map, westplay_host::maps::MapStatus::Failed { .. }), Ordering::Release);
    if ready
        && state.pending.swap(false, Ordering::AcqRel)
        && let Some(store) = app.try_state::<SetupStore>()
    {
        match launch(&store) {
            Ok(message) => westplay_host::log!("ATS ready launch: {}", message.message),
            Err(error) => westplay_host::log!("ATS ready launch: {error}"),
        }
    }
}

fn request_or_launch(app: &AppHandle, store: &SetupStore) -> Result<Message, String> {
    if game::running() {
        return launch(store);
    }
    let state = app.state::<LaunchState>();
    if state.map_failed.load(Ordering::Acquire) {
        return Err("地图准备失败，请在地图页查看错误并重新准备后再启动。".into());
    }
    if !state.map_ready.load(Ordering::Acquire) {
        queue_launch(app);
        return Ok(Message { message: "地图首次准备中，完成后会自动启动 ATS。".into(), done: false });
    }
    launch(store)
}

#[derive(Serialize)]
pub struct Message {
    pub message: String,
    pub done: bool,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Diagnostics {
    game_running: bool,
    game_dir: Option<PathBuf>,
    game_version: Option<String>,
    plugin_current: bool,
    ford_dlc_installed: bool,
    mod_installed: bool,
    game_home: Option<PathBuf>,
    logs: Option<PathBuf>,
    message: String,
}

fn selected_game(store: &SetupStore) -> Option<Game> {
    store.game().get().as_deref().and_then(Game::recognise).or_else(|| game::find().into_iter().next())
}

/// A repeated desktop shortcut forwards its intent to the existing companion rather than starting a
/// second host or showing an "already running" box. Requests stay in this fork's own data directory.
pub(crate) fn request_launch() -> Result<(), String> {
    let dir = places::westplay_documents().ok_or("未找到应用数据目录。")?;
    std::fs::create_dir_all(&dir).map_err(|error| error.to_string())?;
    std::fs::write(dir.join(format!("launch-request-{}", std::process::id())), b"launch ATS\n")
        .map_err(|error| error.to_string())
}

pub(crate) fn watch_launch_requests(app: &AppHandle) {
    let app = app.clone();
    let _ = std::thread::Builder::new().name("ats-shortcut".into()).spawn(move || {
        loop {
            std::thread::sleep(std::time::Duration::from_secs(1));
            let Some(dir) = places::westplay_documents() else { continue };
            let Ok(entries) = std::fs::read_dir(&dir) else { continue };
            let requests: Vec<_> = entries
                .flatten()
                .filter(|entry| {
                    entry.file_type().is_ok_and(|kind| kind.is_file())
                        && entry.file_name().to_string_lossy().starts_with("launch-request-")
                })
                .map(|entry| entry.path())
                .collect();
            if requests.is_empty() {
                continue;
            }
            let Some(store) = app.try_state::<SetupStore>() else { continue };
            if store.ready_to_launch() {
                match request_or_launch(&app, &store) {
                    Ok(message) => westplay_host::log!("ATS shortcut: {}", message.message),
                    Err(error) => westplay_host::log!("ATS shortcut: {error}"),
                }
            }
            for request in requests {
                let _ = std::fs::remove_file(request);
            }
        }
    });
}

#[tauri::command]
pub async fn ats_diagnostics(app: AppHandle, store: State<'_, SetupStore>) -> Result<Diagnostics, String> {
    let store = store.inner().clone();
    tauri::async_runtime::spawn_blocking(move || diagnostics(&app, &store)).await.map_err(|error| error.to_string())
}

fn diagnostics(app: &AppHandle, store: &SetupStore) -> Diagnostics {
    let game = selected_game(store);
    let ours = crate::setup::plugin_file(app);
    let current = game
        .as_ref()
        .zip(ours.as_deref())
        .is_some_and(|(game, ours)| matches!(plugin::state(game, ours), Ok(plugin::State::Current)));
    let ford = game.as_ref().is_some_and(|game| game.dlcs.iter().any(|name| name == "dlc_rt_ford"));
    let screen_mod = places::westplay_documents().map(|dir| dir.join(westplay_setup::game_mod::FILE_NAME));
    Diagnostics {
        game_running: game::running(),
        game_dir: game.as_ref().map(|game| game.dir.clone()),
        game_version: game.as_ref().and_then(|game| game.version).map(|version| version.to_string()),
        plugin_current: current,
        ford_dlc_installed: ford,
        mod_installed: screen_mod.is_some_and(|path| path.is_file()),
        game_home: places::game_documents(),
        logs: places::westplay_documents().map(|dir| dir.join("logs")),
        message: if game.is_none() {
            "未找到 ATS，请先通过 Steam 安装或在设置中选择游戏目录。".into()
        } else if !current {
            "ATS 已找到。游戏关闭时可用“诊断和修复”安装插件。".into()
        } else {
            "安装文件已检查。实际连接状态请看游戏连接指示；Ford DLC 文件存在不代表授权或游戏内测试通过。".into()
        },
    }
}

#[tauri::command]
pub fn ats_launch_game(app: AppHandle, store: State<'_, SetupStore>) -> Result<Message, String> {
    request_or_launch(&app, &store)
}

pub(crate) fn launch(store: &SetupStore) -> Result<Message, String> {
    if game::running() {
        return Ok(Message { message: "ATS 已在运行，WestPlay 将连接当前游戏。".into(), done: true });
    }
    let game = selected_game(store).ok_or("未找到 ATS，请先在设置中选择游戏。")?;
    let checked = (|| {
        if !store.ready_to_launch() {
            return Err("安装设置尚未完成或所选游戏已不可用".to_owned());
        }
        let ours = store.bundled_plugin().ok_or("应用缺少随附的 WestPlay 插件")?;
        let screen_mod =
            places::westplay_documents().ok_or("未找到 WestPlay 自有屏幕资源目录")?.join(game_mod::FILE_NAME);
        check_launch_files(&game, ours, &screen_mod)
    })();
    checked.map_err(|reason| {
        let message = format!("启动预检未通过：{reason}。请先完成安装设置，或在“诊断和修复”中执行修复后再启动 ATS。");
        westplay_host::log!("ATS launch refused: {message}");
        message
    })?;
    let steam = places::steam().ok_or("未找到 Steam，请先安装并登录 Steam。")?;
    let mut command = if game.found_by == FoundBy::Steam {
        let mut command = std::process::Command::new(steam.join("steam.exe"));
        command.args(["-applaunch", game::STEAM_APP]);
        command
    } else {
        // An explicitly selected separate installation uses its own executable, with the real Steam
        // API still responsible for ownership and DLC authorization.
        let mut command = std::process::Command::new(game.dir.join(game::EXECUTABLE));
        command.current_dir(&game.dir).env("SteamAppId", game::STEAM_APP).env("SteamGameId", game::STEAM_APP);
        command
    };
    command.args(["-64bit", "-rdevice", "dx11", "-nointro"]);
    if let Some(home) = std::env::var_os("WESTPLAY_ATS_LAB_ROOT").map(PathBuf::from).or_else(|| store.lab_root()) {
        command.arg("-homedir").arg(home);
    }
    command.spawn().map_err(|error| format!("Steam 启动失败：{error}"))?;
    Ok(Message { message: "已请求 Steam 启动 ATS，正在等待真实游戏连接。".into(), done: true })
}

/// Only this app's fixed deployment files are read. Never rebuilds a mod, copies a plugin or scans profiles.
fn check_launch_files(game: &Game, ours: &Path, screen_mod: &Path) -> Result<(), String> {
    match plugin::state(game, ours).map_err(|error| format!("无法核对已部署插件：{error}"))? {
        plugin::State::Current => {}
        plugin::State::Missing => return Err("游戏中缺少 WestPlay 插件".into()),
        plugin::State::Different => return Err("游戏中的 WestPlay 插件与当前应用不一致".into()),
    }
    let archive = westplay_mapdata::archive::Archive::open(screen_mod)
        .map_err(|error| format!("WestPlay 自有屏幕资源缺失或无法读取：{error}"))?;
    let manifest = archive
        .read("manifest.sii")
        .map_err(|error| format!("无法读取屏幕资源清单：{error}"))?
        .ok_or("屏幕资源缺少版本清单")?;
    let units = westplay_mapdata::sii::parse(&String::from_utf8_lossy(&manifest));
    let current = units.iter().any(|unit| {
        unit.class == "mod_package"
            && unit.get("display_name") == Some("WestPlay")
            && unit.get("package_version") == Some(env!("CARGO_PKG_VERSION"))
    });
    if !current {
        return Err("WestPlay 自有屏幕资源与当前应用版本不一致".into());
    }
    if game.dlcs.iter().any(|name| name == "dlc_rt_ford") {
        let material = "material/ui/westplay/screen_ford_f150_2023";
        let script = archive
            .read("ui/dashboard/ford_f150_gps_23.sii")
            .map_err(|error| format!("无法读取 Ford 屏幕资源：{error}"))?
            .ok_or("自有屏幕资源缺少 Ford F-150 布局")?;
        let patched = String::from_utf8_lossy(&script).contains(&format!("/{material}.mat"));
        if !patched
            || ["mat", "tobj", "dds"].iter().any(|extension| !archive.contains(&format!("{material}.{extension}")))
        {
            return Err("Ford F-150 自有屏幕资源不完整或未适配".into());
        }
    }
    Ok(())
}

#[tauri::command]
pub fn ats_open_logs() -> Result<(), String> {
    let logs = places::westplay_documents().ok_or("未找到日志目录。")?.join("logs");
    std::fs::create_dir_all(&logs).map_err(|error| error.to_string())?;
    std::process::Command::new("explorer.exe").arg(&logs).spawn().map_err(|error| error.to_string())?;
    Ok(())
}

#[tauri::command]
pub async fn ats_repair(store: State<'_, SetupStore>) -> Result<Message, String> {
    if game::running() {
        return Err("ATS 正在运行，无法替换已加载插件。请保存并正常退出游戏后重试；程序不会替你关闭游戏。".into());
    }
    let game = selected_game(&store).ok_or("未找到 ATS，请先在设置中选择游戏目录。")?;
    let report = crate::setup::install_into_game(game.dir, false, store).await?;
    let done = report.done;
    Ok(Message {
        done,
        message: if done {
            "插件和原车屏幕资源已安装，原有存档与 MOD 未修改。".into()
        } else {
            format!("修复未完成，请查看安装设置和日志：{report:?}")
        },
    })
}
