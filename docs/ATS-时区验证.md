# ATS 时区与帧计数验证

核查日期：2026-10-27。实际安装版本：ATS 1.61.3.18s。源码审查、定义读取和公开桥接采样均为只读；主任务另外执行了游戏设置及安装版同画面对照，结果单独记录如下。

## 时间编码与修复依据

本仓库附带的 SCS SDK 1.15 头文件 `tools/scs_sdk_1_15/include/common/scssdk_telemetry_common_channels.h` 将 `game.time` 定义为从第 0 天 00:00 起累计的游戏分钟，将 `multiplayer.time.offset` 定义为本地经济时间与 Convoy 服务器时间的差。它们不是 Unix 时间戳，也不对应电脑的现实日期。插件直接传递游戏分钟；UI 的 `cabClock` 分别加入 Convoy 偏移和地理时区偏移。

[SCS 官方 ATS 1.29 时区文档](https://modding.scssoft.com/wiki/Games/ATS/Modding_guides/1.29#Time_zones_data) 明确说明：`economy_data.default_time_zone` 是基础游戏时间使用的时区。不能将 ETS2 的 120 分钟直接用于 ATS，也不应将当前版本的 ATS 数值永久硬编码。

只读探针从 Steam 库中 `steamapps/common/American Truck Simulator` 实际挂载的定义读取到：

| 游戏定义 | 实际值 |
| --- | --- |
| `def.scs` 内 `def/economy_data.sii` | `default_time_zone: -360`，名称 `MDT` |
| `def/country/nebraska.sui` | country 18，`time_zone: -300`，CDT |
| `def/country/california.sui` | country 1，`time_zone: -420`，PDT |
| `def/car_economy_data.sii` | 无独立时区覆盖 |

新实现将已挂载 `economy_data.sii` 及其 include 中的基准导出为 `countries.json.baseZone`。开启游戏时区时，UI 使用 `countryZone - baseZone`：当前定义下 Nebraska 为 +60 分钟、California 为 -60 分钟、MDT 州为 0。缺少基准时不猜测时区，使用 0 地理偏移。地图 builder 与旧缓存兼容下限均升为 16，确保旧 14/15 缓存重建，不受旧的“无遗漏 MOD 可沿用缓存”例外影响。

新编译的 Rust 定义探针真实返回 `PARSED_BASE_ZONE=Some(-360)` 和 `EXPORTED_BASE_ZONE=-360`。工作区证据为 `research/ats-time-definition-probe.log`。

## Steam 云档选项路径

进一步核查发现，`mapdata::save::latest_of` 仍从 ETS2 AppID 227300 搜索云存档，导致 host 没有选到 ATS 的云存档，也无法从该存档的 profile 读取 `config.cfg`。Documents 下 Steam profile 只有本机控制/摄像机设置 `config_local.cfg` 和 controls，不能据此判断游戏时区选项。

现已改为共享常量 `westplay_shared::GAME_STEAM_APP = "270880"`，供 setup 的安装、Workshop、云档识别及 mapdata 的云存档搜索共用。新增回归使用独立 fixture 同时放置 ATS 云档和同名、更新时间更晚的 ETS2 云档，确认选择 ATS，并正确找到 ATS profile 的 `config.cfg`，不会串读另一款游戏。

独立 Rust 探针调用 production `places` / `profiles` / `save::latest_of`，确认当前选中用户实际使用的 ATS 档案，最新存档为该档案的 `save/autosave_drive/game.sii`，选项来自 `Steam/userdata/<user>/270880/remote/profiles/<profile>/config.cfg`。初次核查时读值为 `uset g_time_zones "0"`；这是当时的配置快照，不代表后续开启时区测试的状态。

新宿主必须在统一重编并重启后才使用修复。进行开启/关闭对照时，应在游戏 Options 中应用并退出设置，使 profile `config.cfg` 真正写盘；只在 Console 改值可能只影响游戏内存。host 同时观察存档和选项文件修改时间，轮询间隔最多约 10 秒，写盘后才向 UI 更新 `timeZones`。

含真实 userdata 绝对路径的原始探针日志仅保留在仓库外的工作区 `research/ats-profile-clock-options.log`，不进入源码 ZIP。本文只保留脱敏后的路径结构。

## North Platte 验证预期与边界

审查时的公开桥接快照位置为 `x=-19361.215126, z=-11433.91423`，网格 country 18，`gameTime=18438`，Convoy 偏移为 0。基础经济时间为第 12 天 19:18；开启游戏时区后，应显示 20:18。关闭游戏时区时，应仍显示 19:18。此点不在 Nebraska 已定义的 secondary 区域内。

上述是定义与算法确定的预期；仅有配置读值不能证明实际显示。主任务随后已完成修复安装版与原厂 HUD 的同画面对照，见下一节。

当前网格尚未支持 **country secondary time-zone rectangles**。Nebraska 西部及其他子时区区域开启时区后仍可能相差一小时；现有 1 km country 网格也会近似州界位置。[SCS 官方 1.35 子时区文档](https://modding.scssoft.com/wiki/Games/ETS2/Modding_guides/1.35#Timezone_sub-areas) 规定：country 的同步数组按顺序匹配地理矩形，首个命中区域决定子时区；city 的时区覆盖另用于经济系统的静态城市时间。本文修复基础时区，不假设尚未对照原厂验证的矩形分量顺序或边界包含规则。

## 修复安装版的同画面实测

证据为 `installed-timezone-hud-100.png` 与 `installed-timezone-hud-100.jsonl`，2026-10-27 13:48:46 左右，North Platte 附近，坐标约 `x=-19396.916, z=-11396.574`，该点不在已定义 secondary 矩形内。实际游戏 PID9720、安装版 host PID10408。截图同时可见 WestPlay 时钟和原厂 HUD；没有拼接不同时刻的画面。

| 同期来源 | 实际值 |
|---|---|
| SDK `game_time_minutes` | 18549，即第12天21:09 |
| WestPlay 原车中控时钟 | 22:09 |
| ATS 原厂 HUD | 10:09PM，即22:09 |
| 结果 | WestPlay 与 HUD 一致，正确应用 Nebraska 相对 MDT 基准的 +60分钟 |

这确认了该安装版在实际开启游戏时区的测试点显示修复通过。随后安装的 generation 修复版只改变共享纹理代号分配，未改动时区算法；其重新连接与浏览器恢复另见 [后台恢复验证](ATS-后台恢复验证.md)。

## 手动时间与关闭时区复测

随后在同一游戏中真实执行 `g_set_time 6` 和 `g_set_time 12`。game.log分别回显命令，截图`installed-manual-time-console-111.png`、`installed-morning-time-112.png`和`installed-noon-theme-113.png`记录早晨/正午，正午地图切为浅色；112的公开桥采样仍为game9720 / host29316。该项验证运行中手动改时间后界面继续工作，不代表测试了所有时刻和跨日边界。

关闭游戏时区的测试还核对了写盘链路：先将RAM选项设为0，再通过游戏Options退出使配置真正写入ATS AppID270880的云profile `config.cfg`，读回`uset g_time_zones "0"`。`settings-restored-driver-127.png`的WestPlay为11:12，与原关闭模式一致。截图127用于关闭模式及写盘状态验收；同时显示原厂HUD的对照证据为前述截图100。

已完成本机开关状态、6点与12点两次手动改时间及对应界面观察；所有州界、secondary子区域、Convoy真实服务器偏移、多次跨时区驾驶和完整跨日边界仍未广泛验证。

## 已执行的源码验证

- `docs/qa-timezone-rust.log`：mapdata 167 项、setup 70 项通过，8 项既有依赖真实游戏的 setup 测试主动忽略。
- `docs/qa-timezone-after-fix.log`：相关 UI 测试 25 项通过，覆盖 ATS 州时差、North Platte 实际分钟、ETS2 回归、自定义经济基准、未知基准。
- 新编译 Rust 函数在实际安装定义上返回并导出 -360。
- TypeScript 项目构建、变更 UI 的 Prettier、变更 Rust 的 rustfmt 和 Git 空白检查通过。

最终全量回归已完成：

- `docs/qa-final-core-tests.log`：Rust 核心 300 项通过、0 失败、9 忽略，进程退出码 0；分项为 mapdata 168、plugin 36、setup 70、shared 26，包含精确的已测试游戏版本判定、时区缓存更新和 ATS / ETS2 云档隔离用例。
- `docs/qa-final-ui-tests.log`：62 个 UI 测试文件、442 项测试全部通过，进程退出码 0。
- Rust 使用独立 `target/qa`、offline/locked、4 个构建任务；测试进程的 `TEMP` / `TMP` 指向工作区 `test-lab/qa-temp`，不重链正在运行的 release 应用。
- UI 首轮在默认 MSIX 沙箱 C 盘 TEMP 出现 SSR 临时模块 `ENOENT`，原始失败日志保留为 `docs/qa-final-ui-tests-initial-environment.log`。仅将当前测试进程的 `TEMP` / `TMP` 改到同一工作区 fixture 后完整通过，未为此修改产品源码。

## 探针帧率字段的含义

`tools/ats_probe.py` 用计数差除以单调时钟间隔计算速率。首个快照没有速率，累计计数本身不是 FPS。

| 字段 | 实际含义 | 不能据此推断 |
| --- | --- | --- |
| `plugin.heartbeat` | DXGI `Present` / `Present1` hook 进入计数 | 未过滤 flags、返回结果或 swap chain，且在原始调用之前计数 |
| `plugin.present_rate_fps` | 上述计数每秒增量，应标为 Present 调用率（Hz） | 显示器实际显示帧率、DLSS 插帧后的显示帧率 |
| `host.frame_seq` | 成功发布的座舱共享纹理计数 | 游戏渲染帧数、源视频帧数 |
| `host.published_rate_fps` | 座舱纹理发布率（Hz） | 游戏实际 FPS |
| `host.frame_generation` | 共享纹理的代号，纹理重建时改变 | **不是** DLSS / FSR 帧生成开关或插帧数 |
| `host.heartbeat` | host 消息循环进度 | 渲染帧率 |
| `screen_frame` / `cab_frame` | 最后发现屏幕时对应的插件帧戳 | 独立累计帧数 |

依据源码：`crates/plugin/src/d3d.rs` 的 `present_hook`、`present1_hook` 与 `on_present`；`crates/host/src/capture.rs` 的纹理发布计数；`crates/host/src/lib.rs` 的消息循环；`crates/shared/src/lib.rs` 的 `frame_texture_name`。真实 FPS 结论需另用原厂/Steam/vendor 显示或独立显示帧测量，并标明测量方法，不能混用探针速率。

## 已完成停车采样：ford-route-drive-01

原始证据：工作区 `test-lab/evidence/ford-route-drive-01.jsonl`，2026-10-27 03:55:04.681 至 03:59:03.689 UTC，240 个样本、跨度 239 秒。

| 指标 | 只读统计结果 |
| --- | --- |
| 公开桥接 / Ford 专用布局支持 / 屏幕启用 | 各 240 / 240 样本 |
| 车辆 / 布局 | `vehicle.ford.f150_23` / `ford-f150-2023` |
| 游戏 / host PID | 5868 / 3992，全程一致 |
| 屏幕检测年龄 | 0–1 个 Present 调用 |
| Present 调用率 | 18–22 Hz，均值 19.85 Hz（239 个区间） |
| 座舱纹理发布率 | 0–44 Hz，均值 13.66 Hz（239 个区间） |
| 纹理 | 1280×720，代号 1021953 |
| 计数增量 | Present 4745，纹理发布 3264 |
| 游戏 / host 工作集范围 | 4301.39–4510.25 MiB / 269.71–281.11 MiB |
| 路线命令状态 | action 4、request 1、answered 1、`done`，整段未变 |
| 导航剩余距离 | 全程 6783.77246 m |
| 最大速度 / 与起点最大位移 | 0.00317 km/h / 0.00070 m |

这段证明 Ford 停车状态下桥接和纹理发布持续运行，不能因文件名含 `drive` 就宣称完成驾驶。发布率为 0 的单秒区间也不能单独证明黑屏或故障，静止 UI 可能没有新画面。路线命令应答证明该命令已应答，不能替代路线几何或实车导航验证。本文不据这段停车采样宣称声音播放、道路行驶、真实显示 FPS 或插帧通过；后续短途驾驶与实际媒体声音有各自独立证据，见 [本机实测记录](ATS-实测记录.md)。

个人存档备份和工作区 research 原始数据只留本地，不纳入发布的源码 ZIP。
