# ATS WestPlay 本机实测记录

测试日期：2026-10-27。本文区分真实游戏测试、工程检查和未验证范围；文件名包含 drive 不代表文件中每一秒都在行驶。

本文为公开测试摘要。原始存档、私人备份、完整本机日志及进程报告保留在测试机器，未随公开仓库或 Release 上传；文中的证据文件名用于对应本机归档。公开安装包不包含这些私人数据。

## 环境与存档

- 游戏：Steam American Truck Simulator **1.61.3.18s**，AppID **270880**，DX11，Windows x64。
- 安装目录：通过 Steam 识别的 `steamapps/common/American Truck Simulator`（公开记录省略本机库盘符）。
- 车辆：官方 Road Trip: Ford DLC，SDK ID `vehicle.ford.f150_23`，2023 Ford F-150 原厂驾驶室。
- 显示：2560×1440；RTX 5060 Ti 16GB；32GB 内存。保留用户原有图形注入与视觉 MOD 组合。
- 按用户明确指示使用其 Steam 存档。测试前备份了 94 个相关配置/存档文件，逐文件 SHA256 相同，无备份错误。私人备份留在本机 `test-lab/backups`，不进入源码或交付 ZIP。
- 使用独立 `ats-f150` 分支，基于上游 WestPlay 2.1.2 / `0edc10bf44ffe57350cdf60c9d42bdc603f06eb3`。

## 第一轮真实游戏结果

| 项目 | 实际执行与结果 | 原始证据文件 |
|---|---|---|
| 原车屏幕集成 | 原厂 Ford GPS 屏内显示 WestPlay；游戏渲染车辆屏幕的透视、遮挡与位置，独立仪表正常 | `westplay-ford-home-04.png`、`westplay-in-cab-public-road-moving-69.png` |
| 主页与应用列表 | 按住左 Alt，实际点击 Home、Maps、Apple Music、YouTube、返回按钮 | `westplay-home-grid-open-08.png`、`westplay-maps-open-09.png` |
| 点击与滚动 | DirectInput buffered 事件实际送达；地图滚轮缩放可见变化 | `westplay-map-wheel-10.png`、plugin 日志 |
| 本地 ATS 地图 | 从本机 usa 地图、实际挂载 DLC 和配置生成地图；不是欧洲底图 | map 生成日志、导航截图 |
| 搜索与路线同步 | 搜索附近 Fuel，点击 Go；游戏 navigator 返回 `Done`，SDK 导航距离变为 6783.77m | `westplay-fuel-directions-24.png`、`westplay-route-active-26.png`、plugin 日志 |
| 转弯、停车、重新起步 | 维修场内实际低速转向、倒车修正、停止和再起步，之后通过出口进入公共道路 | `westplay-restart-left-stop-40.png`、`westplay-public-road-entered-59.png` |
| 车内公共道路行驶 | 在公共道路右侧车道前进约 11.6 个游戏世界米，仪表截图 20km/h；1秒采样最高 21.64694km/h；停车于 STOP 路口前 | `westplay-in-cab-public-road-moving-69.png`、`westplay-in-cab-public-road-stopped-70.png`、`ford-cabin-road-gps-05.jsonl` |
| 移动 GPS | 实际车内路线随行驶更新，SDK 导航距离 6402.07→6124.64m；位置、方向和速度变化可读 | 同上、`ford-driving-gps-25s.mp4` |
| 驾驶室视角 | 切换追尾/俯视视角观察道路，再通过临时键盘绑定返回驾驶室；中控恢复显示 | `westplay-interior-binding-verified-68.png` |
| OEM 返回 | 点击 WestPlay 侧栏车辆按钮恢复原车 GPS，再返回 WestPlay；独立仪表保持 | `westplay-clock-WestPlay-76.png`、OEM 时钟对照截图 |
| 日夜外观 | 测试从雨天/傍晚持续到天黑，地图自然由浅色变为深色 | `westplay-route-active-26.png` 对比 `westplay-in-cab-public-road-moving-69.png` |
| YouTube | 未登录，实际加载视频；进度推进，Alt+2 暂停，返回列表、再次播放均成功 | `westplay-youtube-pause-controls-19.png`、`westplay-youtube-back-20.png`、`westplay-audio-diagnostic-playing-72.png` |
| 实际媒体声音 | 直接录取 WebView2 AudioService PID16936 的 15.45秒 PCM：peak0.6032、RMS0.11135；Windows 同时检测到媒体与 ATS 音频会话向同一扬声器输出非零信号 | `audio-playing-sessions-02.json`、`ford-youtube-audio-confirmed-03.audio.verification.json`、`ford-youtube-audio-confirmed-03.mp4` |
| Apple Music | 在原厂中控内打开实际未登录首页和目录；未登录、未验证订阅播放 | `westplay-music-loaded-12.png` |

道路测试为短途低速测试，没有通过前方 STOP 路口、完成全部 6.8km 导航行程或验证所有 DLC 地区。视频中带 Spotify 图标的是 YouTube 视频自身的封面，不能据此认定已验证 Spotify 服务。

第一段以 host 父 PID 捕获的媒体音轨全零，保留在 `audio-verification.json`；原因没有确定。之后加隐藏后台采集进程、保持 ATS 前台并直录实际音频服务，取得了非零音轨。60秒 WASAPI 采样中 600 个前台样本全为 ATS，两会话均未静音。未做人耳音质评价。GPS 短片使用游戏音轨，YouTube 短片使用媒体音轨，两者没有后期混音。

## 实测发现与修复

1. 初次 Tauri 启动因禁用更新后仍注册 updater 插件而崩溃：移除注册，重新启动成功。
2. Codex MSIX 的 AppData 命名空间导致文件原子重命名报 Win32 17：保留原子语义，针对该错误使用物理规范路径重试；实际地图随后在约40秒内完成。
3. ATS 时区基准沿用 ETS2 +120：改为从实际挂载 `economy_data.default_time_zone` 导出，当前实读 -360/MDT，地图缓存升级至 builder16。
4. 上游云存档查找仍写死 ETS2 AppID227300：统一使用 ATS AppID270880，回归确保不会读到同名 ETS2 云档。实际只读探针已命中用户 ATS 云存档及选项。
5. 原宿主仅在浏览器退出时重试：宿主错误与线程 panic 也统一进入有限恢复策略，60秒最多5次重启，每次等待1秒，正常停止和 GPU 迁移不计入。
6. 新启动游戏前增加固定部署文件预检：插件字节匹配、自有资源版本、Ford GPS 材质/纹理齐全；失败给中文修复提示，已运行游戏只连接现有进程。
7. 首次真实浏览器故障注入发现：supervisor 已重启宿主线程，但共享纹理 generation 在同一进程内重复，插件仍使用旧句柄，车屏显示 OEM。改用进程级非零代号分配器后，第二次真实注入已验证代号改变、插件打开新纹理和 WestPlay 车屏恢复；协议及 DLL 不变。

时区旧版真实对照：North Platte 开启 `g_time_zones=1` 后，SDK20:50、原车/HUD9:50PM（21:50），证实本地时间应为 SDK+60分钟；旧 host 因云档路径遗漏没有读到该选项，屏内仍显示 SDK 时间。修复后的安装版已完成同画面对照：WestPlay **22:09**、原厂 HUD **10:09PM**，同期 SDK `18549` 分钟为 **21:09**，实际正确加上 60 分钟。证据为 `installed-timezone-hud-100.png` 及同名 `.jsonl`，详见 [时区验证](ATS-时区验证.md)。

## 性能记录的口径

第一轮只读探针共 1380 个1秒样本，分5个阶段；大部分为停车与菜单操作，包含约26个速度绝对值大于1km/h的采样点。示例公共道路驾驶阶段：

| 指标 | 该阶段观测 |
|---|---|
| westplay.exe 工作集 | 约259MB |
| westplay.exe 系统 CPU 占用中位值 | 0.08%（不包含 WebView2 子进程） |
| amtrucks.exe 工作集中位值 | 约2979MB |
| 游戏画面原有 FPS 角标 | 截图约34–42fps，原图形 MOD、雨天/傍晚场景 |
| 插件 Present 调用率 | 约18–22次/秒；不是显示/生成帧 FPS |
| UI 纹理发布率 | 静态页面可能低至0，视频/地图交互时升高；不是游戏 FPS |

完整统计见 `phase1-performance-summary.json`。未进行独立受控的安装前后性能对比，不据此声称“零性能开销”。源码编译、录屏和菜单操作期间的数值也不能等同于长途驾驶压力测试。

## 工程检查

- 核心 Rust：300 通过、0失败、9项上游主动忽略。
- 前端：62文件、442测试通过。
- 宿主有限重启策略：4项纯 Rust 测试通过；Tauri app 检查通过。
- 共享纹理 generation：5项新增回归和应用检查通过；production 构建成功，日志为 `qa-generation-production-build.log`。
- 视频已实际探测并查看联系表：驾驶片25.00秒，YouTube片14.90秒，均2560×1440/30fps、H.264、AAC立体声。联系表用于 QA，交付原始单帧截图没有拼接或合成功能画面。

## 安装版复测与限制

去「支持我」版已实际安装并就地升级；支持页面、赞助入口及相应本机命令已按用户要求移除。最终 generation 修复版的 `installed-generation-fixed-artifacts.json` 为 `passed`，61 个文件、0 失败，桌面与开始菜单快捷方式目标及 `--launch-ats` 参数均匹配。

| 最终安装产物 | SHA256 |
|---|---|
| NSIS 安装器 | `F54210893C170EDD2AE2202DE66F69AE14B6F8FBA863A32410F6B893260548BC` |
| 安装版 `westplay.exe` | `762F42FB169728F113FEF1A1B8DD3812042AF92F75C843B0B5E1794D65FB15E5` |
| `westplay.dll` | `2506C1F6EE152CF22B583581892F44DD91FB7E9F91EBA06B39882B69CC861C68` |

桌面快捷方式第一次实际启动后，安装版 host PID10408 与 ATS PID9720 出现，13:29:21 日志记录 ATS ready 和 Steam 启动请求成功。此前旧 DLL 的启动预检曾明确拦截，安装版界面的 Repair 已成功部署匹配 DLL。之后保留 ATS PID9720 运行，正常停止旧 host10408 并升级，桌面入口重新启动 host29316，成功连接同一个游戏，原车 WestPlay 画面恢复，未重复启动 ATS。证据为 `installed-service-reconnect-104.png`、`installed-generation-before-105.jsonl`。

14:11:19 对 host29316 所属的真实 cabin WebView2 浏览器 PID16444 进行受控停止；host 与 ATS 进程均保持运行。应用日志记录 `restarting 1/5`，共享纹理 generation 从 **7504897→7504898**；plugin 日志明确记录 `opened shared texture generation 7504898`。约 10 秒后的 `installed-recovery-fixed-after-106.png` 是恢复的真实 WestPlay 页面；后续桥采样 `frame_seq=693`、`screen_enabled=true`、游戏 PID9720 不变。该轮证实浏览器故障后的真实车屏恢复，不能只用计数增长判断。完整采样为 `installed-recovery-fixed-02.jsonl`，机制及首次失败见 [后台恢复验证](ATS-后台恢复验证.md)。

恢复后继续在原车中按住 Alt，实际点击 Maps。`installed-recovered-maps-click-110.png` 显示已切换到地图与路线，并有300m右转提示，仍为同一game9720 / host29316，无需重启。这只验证了恢复后的 Maps 切换，不扩展为所有控件交互通过。

| 后续专项 | 实际操作与结果 | 证据 |
|---|---|---|
| 手动修改游戏时间 | 游戏控制台真实执行 `g_set_time 6`、`g_set_time 12`，game.log有回显；车内画面转为早晨/正午，正午地图为浅色 | `installed-manual-time-console-111.png`、`installed-morning-time-112.png`及`.jsonl`、`installed-noon-theme-113.png` |
| 关闭游戏时区 | RAM设置后通过Options退出写盘，实际ATS AppID270880云profile的`config.cfg`读回`g_time_zones "0"`；车屏11:12与原关闭模式一致 | `settings-restored-driver-127.png` |
| 渲染缩放100% | game.log时标`01:43:12.406 r_scale_x 1`、`01:43:14.890 r_scale_y 1`；随后真实车内WestPlay仍正常 | `installed-render-scale-100-130.png` |
| 恢复原300%缩放 | game.log时标`01:47:49.247 r_scale_x 1.5`、`01:47:51.742 r_scale_y 2`；随后WestPlay仍正常 | `installed-render-scale-restored-132.png` |

缩放结果仅采用上述最终成功批次。截图130的92FPS是该帧角标，不能作为稳定帧率、性能提升幅度或独立受控对比的结论。107–109为交互校准/悬停过程；114–125含控制台焦点或菜单误操作及私人本机音乐列表，不用作缩放通过证据，也不进入公开证据交付。源码包不包含任何本机测试截图或运行日志。

真实故障恢复仅完成上述一次修复后浏览器退出场景，未实际覆盖 panic、GPU 迁移、重试限额耗尽和长时间反复故障。开始菜单入口已验目标与参数，实际点击启动尚未单独验证。

未完成账号授权的 Spotify、Apple Music、歌词/封面/切歌等按服务分别标为未完成端到端验证。地图 MOD、其他游戏版本、所有分辨率和长途驾驶没有得到广泛验证。国家定义中的 secondary timezone 矩形尚未实现，相关子区域可能有1小时偏差；当前 North Platte 测试点不在这些矩形内。保留上游实现不等同于这些项目已通过真实测试。
