# ATS WestPlay 安装与快捷方式验收

本文记录当前安装器的验收要求。2026-10-28 按用户要求，将桌面和开始菜单入口改为只打开 WestPlay，由用户手动启动 ATS。此前 2.1.2 的实际安装、桌面启动游戏及连接已有游戏的历史证据仍保留在《ATS-实测记录》中；它们不代表本次手动启动默认值已完成新一轮游戏测试。

本次新版安装器已完成覆盖安装，安装器 SHA256 为 `0753314A417C72D241AEE6F5D3F1FD38EF067E7C689E2C91C8BC7E113EEB7691`。只读报告 `test-lab/evidence/manual-launch-installed-20261028.json` 核对 61 个安装文件全部通过，失败检查为 0，卸载器存在，桌面和开始菜单快捷方式参数均为空。该报告只证明安装产物与快捷方式字段正确；实际点击及新一轮游戏连接以另行采集的运行证据为准。

随后通过 Windows ShellExecute 实际打开桌面快捷方式，安装版 WestPlay PID25668 正常运行，日志记录界面、车屏浏览器和地图准备完成。连续25秒进程采样未出现 ATS，再进行10次独立进程数量检查，均为 WestPlay 1个、ATS 0个。结果见 `manual-launch-runtime-20261028.json`。检查脚本最初将空进程列表的 null 误计为一个进程，已修正并保留原始检查报告；没有为此改动应用。此次没有启动游戏或重复先前车内测试，exe 与 DLL 哈希均与上一轮真实游戏验证版本相同。

## 代码审查结论

当前安装器采用 `currentUser`。静默首次安装传 `/S`、不传 `/NS` 或 `/UPDATE` 时，Tauri 在安装节内先创建开始菜单快捷方式，并因静默模式创建桌面快捷方式，再调用 `NSIS_HOOK_POSTINSTALL`。ATS hook 对目标确实属于此次安装的快捷方式清空启动参数，包括旧版的 `--launch-ats`，使入口只打开 WestPlay。开始菜单变量为空时，MUI 的写入宏使用配置的默认文件夹 `ATS WestPlay`。

交互式安装的桌面快捷方式在完成页创建，晚于 `POSTINSTALL`；因此 hook 还在 `.onGUIEnd` 再清空参数。只更新匹配本安装 exe 的已有快捷方式，不创建用户通过选项跳过的快捷方式，不修改其他目标。工作区内的隔离快捷方式夹具可核对旧自动启动参数清除和目标保护；它不能代替完整安装测试。

## 真机安装前

1. 根代理确认本轮驾驶和日志采集结束，选择不会影响正在运行测试的时间；不自动关闭游戏或启动器。
2. 记录最终安装器路径、长度及 SHA256，并与本次构建清单核对。源码变化后需重新打包并重新记录哈希。
3. 记录已有 `ATS WestPlay` 安装和快捷方式状态。如果已经安装，先记录它们的目标和参数；不能把覆盖安装称作“首次安装”。真正首次安装可在新的 Windows 测试用户中执行，或在用户同意的干净环境中执行。
4. 不删除或重命名个人 ATS 存档、MOD、Steam 数据或媒体账户目录。测试安装目录优先放在明确的独立路径，避免覆盖开发版。

## 场景一：静默首次安装

下列命令仅供实际验收时执行。本轮没有运行。

```powershell
$installer = '安装包的绝对路径'
$installDir = 'D:\Apps\ATS WestPlay'
$process = Start-Process -FilePath $installer -ArgumentList "/S /D=$installDir" -WindowStyle Hidden -Wait -PassThru
$process.ExitCode
```

`/D=` 是最后一项；不加 `/R`，避免静默安装结束后立即启动应用，不加 `/NS`，不加 `/UPDATE`。预期退出码为 `0`。

随后以只读方式检查：

```powershell
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
$links = @(
  (Join-Path $desktop 'ATS WestPlay.lnk'),
  (Join-Path $programs 'ATS WestPlay\ATS WestPlay.lnk')
)
foreach ($path in $links) {
  if (-not (Test-Path -LiteralPath $path)) { throw "缺少快捷方式：$path" }
  $link = $shell.CreateShortcut($path)
  [pscustomobject]@{Path=$path;Target=$link.TargetPath;Arguments=$link.Arguments;WorkingDirectory=$link.WorkingDirectory}
}
```

两个目标应为此次安装目录中的 `westplay.exe`，`Arguments` 均为空。同时检查 DLL、`ui/index.html`、`ui/cabin.html`、`LICENSE.txt` 和两份第三方声明存在，安装后的 exe/DLL 哈希与构建清单一致。此时仍不能标记游戏内功能通过。

本项目还提供只读验收脚本。`package-ats.ps1` 成功打包时会重新生成 `docs/package-manifest.json`，记录此次安装器和每个资源文件的 SHA256。安装结束后，根代理可执行：

```powershell
& .\tools\check-ats-install.ps1 `
  -InstallDirectory 'D:\Apps\ATS WestPlay' `
  -OutputPath '..\test-lab\evidence\installed-artifacts.json'
```

脚本核对完整安装文件清单、卸载器是否存在，以及当前用户桌面和开始菜单两处 `.lnk` 的目标与空参数。它只读文件和快捷方式，不启动应用、游戏或卸载器，不操作 GUI，也不读取账户内容。缺少文件、哈希不一致、缺少预期快捷方式或参数错误时退出码为 `1`；通过时为 `0`。输出目录必须事先存在。明确测试 `/NS` 或取消桌面快捷方式的场景，可另用 `-SkipShortcuts` 只检查文件，并单独记录该场景的快捷方式预期。

此脚本通过只证明安装产物和入口字段正确。实际首次设置、双击启动、连接游戏、媒体声音以及升级/卸载仍须按后续场景单独验证。

## 场景二：交互式安装与快捷方式

使用简体中文完成一次交互式安装。选择创建桌面快捷方式，关闭安装器完成页后再读回 `.lnk` 参数，确认完成页最后一次创建后参数仍为空。另外测试明确取消创建桌面快捷方式时，安装器尊重该选择；测试 `/NS` 时不新建快捷方式。

## 场景三：独立启动与自动连接

先确认首次设置已完成，再实际双击桌面快捷方式：记录启动器进程、游戏进程数量和连接状态。游戏未运行时应只打开 WestPlay，显示等待游戏，不应启动 ATS。随后从 Steam 手动启动 ATS、载入存档并进入 Ford 驾驶室，确认自动连接和车内屏幕。反过来，先手动打开 ATS 后再启动 WestPlay，也应连接已有游戏。已运行的 ATS 不应重复启动。

再检查启动器已运行而游戏已退出时，重复点击无参数快捷方式不应重新启动 ATS；当前程序会提示 WestPlay 已在运行。首次地图构建应独立进行，完成后也不应自行启动 ATS。若构建失败，应显示错误而不是报告连接成功。最后使用开始菜单入口重复一次。

启动台中的「启动 ATS 游戏」按钮仍保留：只有用户明确点击它，或明确使用兼容命令行参数 `--launch-ats`，才请求启动游戏；地图未准备好时，该请求会等待地图准备完成。手动启动不经过该按钮的启动预检，如插件缺失，应在游戏关闭时使用「诊断与修复」。

## 场景四：升级、卸载与证据

覆盖安装后读回两个快捷方式参数，并核对原版 ETS2 WestPlay 的目录和快捷方式未改变。卸载前由用户正常退出实际安装版；通过程序的安全卸载入口移除游戏端组件，再测试 Windows 卸载。保留设置与删除设置的行为应分别记录，个人 ATS 存档与原有 MOD 必须保持不变。

每项证据记录时间、安装器哈希、安装目录、Windows 用户环境是否首次安装、实际命令、退出码、快捷方式字段、程序/游戏进程数量、截图和日志位置。未实际执行的项目标为“未验证”。
