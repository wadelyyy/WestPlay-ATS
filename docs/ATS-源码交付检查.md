# ATS WestPlay 源码交付检查

源码 ZIP 从 `WestPlay-ATS` 仓库自身取文件，不能递归压缩整个 `ATS` 工作区。相邻 `.tools`、`test-lab`、历史项目、私人备份和真实游戏安装均不属于源包。

当前采用 `tools/source-package-policy.json` 的允许清单与排除清单。`tools/audit-source-package.py` 读取 Git 已跟踪及未忽略的新文件，并取当前工作区内容，因此保留尚未提交的移植修改；不能直接使用 `git archive HEAD` 导出旧版源码。脚本只产生审核清单，不创建 ZIP。

运行：

```powershell
python tools/audit-source-package.py
```

实际归档使用下面的脚本。输出目录必须是仓库外的独立新目录，已存在时拒绝执行。先完成文档与源码冻结，再创建归档；实际文件与校验结果以交付目录中的ZIP及哈希清单为准。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/package-source.ps1 -OutputDirectory '..\deliverables\ATS-WestPlay-2.1.2-20261027\source'
```

脚本重新运行审核，按 `docs/source-package-audit.json` 的 `files` 列表逐文件归档，随后从 ZIP 逐项读回并核对 SHA256，再生成 `source-files.json`、`source-files.sha256` 和 `SHA256SUMS.txt`。源码在审核后发生改变、出现清单外条目或缺文件时均报错，不生成成功清单。审核清单本身不进入源码 ZIP。

敏感标记检查只是补充，不代表已证明所有文件没有秘密；最终仍需审阅新加入的文件和 ZIP 的条目列表。

| 类别                                                                        | 源码 ZIP 处理                                      |
| --------------------------------------------------------------------------- | -------------------------------------------------- |
| Rust、React、配置、锁文件、图标、原版 UI 资源                               | 保留                                               |
| 中文通用说明、功能表、源码分析、上游文档图片                                | 保留                                               |
| GPL 许可、第三方声明、SCS SDK 源码头文件及许可                              | 保留                                               |
| `target`、`node_modules`、`dist`、生成 schemas、缓存和工具链                | 排除                                               |
| `.git`、`.codex`、`.agents`、环境文件、私钥、证书                           | 排除                                               |
| 存档、用户档案、备份、WebView2 浏览器数据、Cookie、账户数据库               | 排除                                               |
| `.scs`、从游戏导出的地图瓦片/模型/材质及其他游戏文件                        | 排除                                               |
| 安装包、DLL、EXE、PDB 和历史 ZIP                                            | 作为独立二进制交付，排除出源码 ZIP                 |
| `ats-deployment.json`、`cargo-metadata.json`、`package-manifest.json`、日志 | 本机部署/构建证据，排除出源码 ZIP                  |
| `docs/ui-preview`                                                           | 生成的界面预览证据，排除出源码 ZIP；不能算游戏截图 |

`assets/tablet/Kedi739.pmd`、`Kedi739.pmg`、`tablet.dds` 是上游原本提供且被构建流程使用的素材，旁边 `assets/tablet/README.md` 说明了来源和使用许可。它们是精确列出的例外，审核脚本只接受与 Git 原版一致的字节，并保留说明文件。不能按扩展名全部删除，否则会破坏完整源码构建。

实际截图、录屏和测试日志可作为单独证据包交付；应逐项选取、去除凭据和不必要的私人信息，不能打包整个游戏 home、测试档案或备份目录。源包生成后，再检查 ZIP 中不存在排除项，并至少确认有 `Cargo.toml`、各 crate 源码、`ui/src`、安装 hooks、资源和许可文件。

源码包排除整个本机`test-lab`与`research`，不包含测试截图、录屏或运行日志。公开证据另行挑选：早期114–125为控制台焦点/菜单误操作过程，并含私人本机音乐列表，不纳入公开交付；渲染缩放仅以最终成功批次130、132及对应命令日志为有效依据。合法构建必需的原版tablet素材不属于该类本机测试数据，按上述精确例外保留。
