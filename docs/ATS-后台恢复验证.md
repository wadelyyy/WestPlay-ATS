# 后台宿主恢复验证

`app/src/main.rs` 的既有 supervisor 现在对 WebView2 浏览器退出、宿主返回错误、宿主线程 panic 和线程创建失败统一重试。每次在原 supervisor 中等待 1 秒，再创建新的宿主线程；所有失败共用 60 秒滚动窗口内最多 5 次重启的限额。第 6 次失败停止恢复，记录原因和限额，并向 companion 发出最终 `host-status`。

正常停止与 GPU 迁移不消耗失败限额。循环开头检查停止标志，避免用户退出发生在重试延迟或 GPU 迁移等待期间时又启动宿主。原有 GPU 迁移等待浏览器退出的流程保留。

策略在 `app/src/host_restart.rs`，仅依赖 Rust 标准库，不新增运行时或常驻进程。它恢复的是仍在运行的 companion 进程内部的宿主线程/浏览器；不提供整个 companion 进程被结束后的进程外重拉机制。

2026-10-27 已完成工程验证：

| 验证 | 结果 |
| --- | --- |
| 浏览器错误、宿主错误、panic 原因共用限额 | 通过 |
| 滚动窗口与第 60 秒的过期边界 | 通过 |
| 用户停止优先于错误和 GPU 迁移，且不消耗限额 | 通过 |
| GPU 迁移和正常停止不消耗限额 | 通过 |
| 实际应用整合 `cargo check --offline --locked --target-dir target/qa -p westplay-app` | 退出码 0 |
| 变更 Rust 格式与 Git 空白检查 | 通过 |

4 项策略单测使用 production 模块编译执行，日志为 `docs/qa-host-restart-policy.log`；应用检查日志为 `docs/qa-host-supervisor-check.log`。这一步仅证明工程策略。随后执行的真实浏览器故障注入及修复后结果分别记录如下。

## 共享纹理代号的恢复缺陷

随后真实故障注入只结束 WestPlay 所属的 cabin WebView2 浏览器，保持 companion / host 进程和 ATS 进程不变。supervisor 确实执行了第 1 次重启，新页面与纹理发布计数继续增长，但车屏仍显示原厂界面，首次注入不能记为屏幕恢复通过。

根因是每次 `host::run` 都将局部 `generation_counter` 清零，以 PID 加低 8 位计数组成的共享纹理代号在同进程重启后重复。插件只在代号变化时打开新纹理，因此仍持有旧纹理。低 8 位计数还会在 256 次重建后再次重复。

已改为 `crates/host/src/frame_generation.rs` 中的进程级静态原子分配器。各次 host run 和管线重建共用同一序列，完整的非零 u32 代号空间每个值仅分配一次，0 保留为无纹理，耗尽时报错而不复用。PID 仍用于不同进程的起始偏移。桥接协议 v24、字段布局、u32 类型和 v8 纹理名称格式保持一致，修复只需重构建并安装 app，无需替换插件。

5 项新增回归已通过：跨 host run 分配、连续 1025 次重建、跨数值尾部跳过 0、代号耗尽拒绝复用，以及 4 个线程并发唯一性。日志为 `docs/qa-frame-generation-tests.log`。应用整合检查 `cargo check --offline --locked --target-dir target/qa -p westplay-app` 退出码为 0，日志为 `docs/qa-frame-generation-app-check.log`。

## 修复后的安装版真实复测

最终安装版 app SHA256 为 `762F42FB169728F113FEF1A1B8DD3812042AF92F75C843B0B5E1794D65FB15E5`，安装器 SHA256 为 `F54210893C170EDD2AE2202DE66F69AE14B6F8FBA863A32410F6B893260548BC`。`installed-generation-fixed-artifacts.json` 核对 61 个文件，结果 `passed`、0 失败。

先验证安装升级后重新连接：正常停止旧 host10408，保留 ATS PID9720；升级后通过桌面快捷方式启动新 host29316。`installed-service-reconnect-104.png` 显示原厂中控内真实 WestPlay 页面，`installed-generation-before-105.jsonl` 记录同一游戏 PID9720 和 generation7504897。该场景没有重复启动游戏，属于 companion 重新启动后的重连，不是进程内部的自动故障恢复。

随后对新安装版执行真实浏览器退出测试，未结束 companion / host 或 ATS：

| 证据点 | 实际观测 |
|---|---|
| 注入目标 | host29316 所属 cabin WebView2 浏览器 PID16444，14:11:19 受控停止 |
| supervisor | 14:11:19.417 记录 cabin browser stopped、`restarting 1/5 within 60s after 1s` |
| 新纹理发布 | 14:11:20.952 记录 generation7504898；之前为7504897 |
| 插件重新打开 | plugin.log 明确记录 `opened shared texture generation 7504898` |
| 真实车屏 | 约10秒后的 `installed-recovery-fixed-after-106.png` 显示 WestPlay 页面，区别于首次失败时的 OEM 画面 |
| 后续桥采样 | `frame_seq=693`、`screen_enabled=true`、host29316 与 game9720 保持；见 `installed-recovery-fixed-02.jsonl` |

上述证据确认同一宿主进程内部浏览器退出后，自动恢复的新共享纹理实际到达原车屏幕。之后主任务在恢复后的真实车屏按住Alt并点击Maps，`installed-recovered-maps-click-110.png` 显示地图、路线与300m右转提示；game9720 / host29316保持，无需重启。因此恢复后的Maps切换已实测通过；其他按钮与全部应用交互没有据此一并标为通过。107–109仅是校准或悬停过程，不作为完成交互的证据。

本轮只完成一次修复后的真实浏览器退出注入。宿主返回错误、线程 panic、GPU 迁移、60秒内连续失败耗尽限额及长期反复恢复仍只有对应工程覆盖或尚待专门实测。整个 companion 进程被结束后不由外部守护进程自动重拉；桌面入口重新启动并连接现有游戏已有独立实测。
