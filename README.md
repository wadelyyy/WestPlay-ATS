# ATS WestPlay · Ford F-150 改版

将地图、导航和媒体界面显示在《美国卡车模拟》（American Truck Simulator，ATS）官方 **2023 Ford F-150 的原车中控屏**中。

本项目由 [enes-less/WestPlay](https://github.com/enes-less/WestPlay) **修改移植而来**，原项目面向《欧洲卡车模拟 2》。本分支基于上游 **2.1.2**、提交 [`0edc10bf44ffe57350cdf60c9d42bdc603f06eb3`](https://github.com/enes-less/WestPlay/commit/0edc10bf44ffe57350cdf60c9d42bdc603f06eb3)，保留原作者、贡献者及第三方的版权与许可声明，继续使用 **GPL-3.0-or-later**。上游介绍原文保存在 [README.upstream.md](README.upstream.md)。

**[下载安装包](https://github.com/wadelyyy/WestPlay-ATS/releases/latest) · [第一次下载、安装与使用](docs/ATS-下载安装与使用.md) · [功能与测试范围](docs/ATS-功能对照表.md)**

这是独立社区改版，与 SCS Software、Ford、Apple、Spotify 或 Google 没有关联或官方背书。

## 适用环境

- Windows 10 / 11，64 位；Microsoft Edge WebView2 Runtime。
- 已安装并可正常运行的 Steam 版 ATS，以及合法拥有并启用的官方 **Road Trip: Ford DLC**。
- 使用 DLC 中的 **2023 Ford F-150**，游戏以 **DirectX 11** 模式运行。
- 已实际测试的组合为 **ATS 1.61.3.18s / DX11 / Windows x64 / 2023 Ford F-150**；其他游戏版本、车辆和地图 MOD 尚需分别验证。

安装包不包含 ATS、Ford DLC、用户存档或游戏地图归档。中控资源和地图数据在首次设置时从用户本机游戏生成。

## 第一次安装

1. 在本仓库的 [Releases](https://github.com/wadelyyy/WestPlay-ATS/releases/latest) 页面展开 **Assets**，下载名字以 **`_x64-setup.exe`** 结尾的 Windows 安装程序，例如 `ATS-WestPlay_2.1.2_x64-setup.exe`。GitHub 的 `Source code (zip)` / `Source code (tar.gz)` 是源码，不是安装包。
2. **正常退出 ATS**，运行安装程序，选择安装位置和需要的快捷方式。
3. 打开 **ATS WestPlay**，按向导确认 ATS 游戏目录、部署插件和屏幕资源，等待地图准备完成，再完成操作教程。插件复制需要权限时按提示授权。
4. 保持 WestPlay 运行，从 **Steam 手动启动 ATS，选择 DirectX 11**，载入自己的存档并进入官方 2023 Ford F-150 的驾驶室。
5. 打开车辆电源，切到原车 **GPS / 导航页面**，等待 WestPlay 中控出现。

**桌面和开始菜单快捷方式只打开 WestPlay，不会自动启动美卡。** 两个程序都运行后自动连接，先开哪个均可；需要时仍可主动点击 WestPlay 内的「启动 ATS 游戏」。

完整步骤、按键、媒体登录和故障排查见 [下载安装与使用指南](docs/ATS-下载安装与使用.md)。

## 日常操作

在 WestPlay 电脑端的「控制」页确认交互键与模式。默认交互键是 **左 Alt**：长按模式下按住它操作中控、松开退出；开启「按一次，无需按住」后，按一下进入、再按一下退出。进入中控操作后可用鼠标点击和滚轮缩放地图。

默认媒体键为主键盘 **1 降低音量、2 播放/暂停、3 提高音量**。长按模式下需同时按住交互键；按一次模式下先进入中控操作。以「控制」页实际绑定为准。

地图中可搜索地点、查看附近设施并把路线交给游戏导航。已验证无需登录的 YouTube 公开视频播放、暂停、返回和非零音频输出。Apple Music、Spotify、YouTube Music 等沿用服务官方登录；账户和订阅按各服务要求授权。

## 相对原项目的主要修改

| 范围 | 本分支的改动 |
| --- | --- |
| 游戏与车辆 | ATS 游戏识别、Steam AppID、存档与地图路径；适配官方 2023 Ford F-150 原车 GPS 屏材质 |
| 地图与导航 | 从本机 ATS `usa` 地图及已挂载 DLC 生成数据，对接 ATS 遥测与游戏导航 |
| 时间 | 修复 ATS 云存档读取，从游戏定义读取基础时区，并处理当前地点的主时区 |
| 电脑端 | 中文 ATS 启动台、连接状态、安装检查、日志、诊断修复和安全卸载入口 |
| 启动方式 | 默认只打开伴侣程序，用户手动从 Steam 启动 ATS；保留显式启动按钮 |
| 后台恢复 | 对内部宿主 / 浏览器故障进行有限重试，使用跨重启唯一纹理代号恢复车屏连接 |
| 项目标识 | 独立 ATS 应用标识、数据目录与 IPC 名称，避免混用原 ETS2 分支 |
| 更新与界面 | 关闭原 ETS2 自动更新入口；移除「支持我」页面和跳转命令，保留版权和许可 |

原版 React 车载界面、WebView2 媒体实现、D3D11 共享纹理、输入与账户授权流程继续沿用。

## 真实游戏验证与限制

已在上述 ATS 版本中实际验证 Ford 原车屏幕、地图和鼠标操作、目的地与导航同步、公共道路短途驾驶、YouTube 播放和声音输出、日夜主题、已有游戏连接及受控浏览器故障后的自动恢复。安装版文件与桌面、开始菜单快捷方式也已核对。

当前验证范围包括以下限制：

- 未完成长途全程、全地图 DLC、全部地图 MOD、全部分辨率或长期压力测试。
- Spotify、Apple Music 订阅播放、YouTube Music、歌词和完整账户流程尚未完成端到端验证。
- `secondary timezone` 子区域矩形尚未实现；涉及这些边界的地区可能出现一小时时差。
- 内部宿主 / 浏览器有有限次数的自动恢复；整个 WestPlay 进程退出后需重新打开程序。
- 检测到 Ford DLC 文件或遥测连接，不能单独证明 DLC 已授权或中控显示正常。

逐项结果与边界见 [功能对照表](docs/ATS-功能对照表.md)、[实测记录](docs/ATS-实测记录.md)、[时区验证](docs/ATS-时区验证.md) 和 [后台恢复验证](docs/ATS-后台恢复验证.md)。

## 从源码构建

需要 Windows x64、Rust MSVC 工具链、Visual Studio C++ Build Tools 与 Windows SDK、Node.js 24 / npm。

```powershell
npm ci
npm --prefix ui ci
npm --prefix ui test
powershell -NoProfile -ExecutionPolicy Bypass -File tools/package-ats.ps1
```

脚本构建原生插件、界面、Tauri 程序和 NSIS 安装器；安装包输出到 `target/release/bundle/nsis`。构建成功不能代替真实游戏验证。

## 来源与许可

感谢 [enes-less](https://github.com/enes-less) 及 [WestPlay 上游项目](https://github.com/enes-less/WestPlay) 的原始实现。本仓库是其 ATS 适配改版，原作者与第三方保留各自权利。

项目使用 [GNU GPL v3 或更新版本](LICENSE)。第三方来源与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。游戏、车辆和媒体服务名称及标志属于其各自权利人。
