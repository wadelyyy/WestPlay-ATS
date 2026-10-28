# ATS WestPlay

这是 [WestPlay](https://github.com/enes-less/WestPlay) 2.1.2 的独立 ATS 分支，基于上游提交 `0edc10bf44ffe57350cdf60c9d42bdc603f06eb3`。保留原版 React 车载界面、WebView2 媒体应用、原生 D3D11 纹理传输、地图生成、输入与账号授权流程。

目标车辆是官方 Road Trip: Ford DLC 的 **2023 Ford F-150**。WestPlay 通过插件把原版界面绘制到车辆 GPS 页的原车屏幕材质中，透视和遮挡由游戏渲染；仪表盘和停车摄像头页保持原有定义。游戏核心归档无需修改。

本机实际测试版本为 **ATS 1.61.3.18s / DX11 / Windows x64**。只把这一精确版本列入已测试版本，不推断其他 ATS 版本、所有地图 MOD 或所有车辆均兼容。

- [中文安装与使用说明](docs/ATS-使用说明.md)
- [功能对照表](docs/ATS-功能对照表.md)
- [真实游戏测试记录](docs/ATS-实测记录.md)
- [时区实现与验证边界](docs/ATS-时区验证.md)
- [安装与快捷方式验收](docs/ATS-安装与快捷方式验收.md)
- [源代码交付规则](docs/ATS-源码交付检查.md)
- [上游功能和原车集成研究](docs/ats-source-audit.md)

运行安装程序后，按首次设置完成插件部署和地图准备。日常使用桌面「ATS WestPlay」快捷方式，只打开伴侣程序，不自动启动 ATS；请自行通过 Steam 启动美卡。两个程序都运行后会自动连接，先后顺序均可。需要由 WestPlay 启动游戏时，可主动点击界面的「启动 ATS 游戏」。进入存档与驾驶室仍使用正常游戏菜单。

Spotify、Apple Music 等保留服务官方登录方式，账户和订阅由用户正常授权。实际已验证与尚未完成端到端验证的项目以功能对照表和实测记录为准。

## 构建

需要 Windows x64、Rust MSVC 工具链、Visual Studio C++ Build Tools 与 Windows SDK、Node.js/npm。安装项目依赖后执行：

```powershell
npm ci
npm --prefix ui ci
npm --prefix ui test
powershell -NoProfile -ExecutionPolicy Bypass -File tools/package-ats.ps1
```

`package-ats.ps1` 编译原生插件、生产界面、Tauri 程序和 NSIS 安装程序；输出在 `target/release/bundle/nsis`。本机 MSIX 环境的临时文件及跨命名空间重命名问题已在构建脚本与原子文件发布逻辑中处理。

使用 [GPL-3.0-or-later](LICENSE)。第三方声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。安装器不附带 ATS、Ford DLC、用户存档或第三方媒体凭据；屏幕资源与地图从本机已安装游戏中生成。
