import { useEffect, useState } from 'react'
import { atsDiagnostics, atsLaunchGame, atsOpenLogs, atsRepair, type AtsDiagnostics } from '../ats'
import { IN_APP } from '../bridge'
import { Button, Group, Note, Panel, Row, Status } from '../room/parts'
import { GLOW, useScreenAt } from '../room/screen'
import type { HostStatus } from '../useHostStatus'

type Action = 'launch' | 'diagnostics' | 'repair' | 'logs'

/** The ATS controls use native commands only. Browser previews never claim a real game connection. */
export function AtsPage({
  status,
  openSettings,
  openAccounts,
  uninstall,
}: {
  status: HostStatus | null
  openSettings(): void
  openAccounts(): void
  uninstall(): void
}) {
  const [diagnostics, setDiagnostics] = useState<AtsDiagnostics | null>(null)
  const [busy, setBusy] = useState<Action | null>(IN_APP ? 'diagnostics' : null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  useScreenAt('home', GLOW.home, null)

  useEffect(() => {
    if (!IN_APP) return
    let active = true
    atsDiagnostics()
      .then((result) => {
        if (active) setDiagnostics(result)
      })
      .catch((reason: unknown) => {
        if (active) setError(String(reason))
      })
      .finally(() => {
        if (active) setBusy(null)
      })
    return () => {
      active = false
    }
  }, [])

  const run = async (action: Action) => {
    if (!IN_APP || busy) return
    setBusy(action)
    setError(null)
    setMessage('')
    try {
      if (action === 'logs') {
        await atsOpenLogs()
        setMessage('已打开日志文件夹。')
      } else if (action === 'launch') {
        const result = await atsLaunchGame()
        setMessage(result.message)
        setDiagnostics(await atsDiagnostics())
      } else if (action === 'repair') {
        const result = await atsRepair()
        setMessage(result.message)
        if (!result.done) setError(result.message)
        setDiagnostics(await atsDiagnostics())
      } else {
        setDiagnostics(await atsDiagnostics())
        setMessage('检查结果已刷新。')
      }
    } catch (reason) {
      setError(String(reason))
    } finally {
      setBusy(null)
    }
  }

  const disabled = !IN_APP || busy !== null
  const connected = IN_APP && status?.gameConnected === true
  const drawing = connected && status?.screenDrawing === true
  const running = connected || diagnostics?.gameRunning === true
  return (
    <Panel place="page" title="ATS 启动台" sub="American Truck Simulator · Ford F-150">
      <div className="ats-launch-actions" lang="zh-CN">
        <Button busy={busy === 'launch'} disabled={disabled} onClick={() => void run('launch')}>
          {running ? '连接正在运行的游戏' : '启动 ATS 游戏'}
        </Button>
        <p className="ats-launch-note">后台服务随启动器运行，游戏已启动时会优先连接。</p>
      </div>
      <Group title="实时连接" place={4}>
        <Row
          title="WestPlay 服务"
          value={!IN_APP ? '界面预览' : status?.error ? '需要检查' : status ? '运行中' : '连接中'}
          accessory={<Status tone={!IN_APP ? 'idle' : status?.error ? 'bad' : status ? 'good' : 'busy'} />}
        />
        <Row
          title="游戏遥测"
          value={connected ? '已连接' : '等待游戏'}
          accessory={<Status tone={connected ? 'good' : 'idle'} />}
        />
        <Row
          title="车内中控屏"
          value={
            drawing
              ? `${status?.framesPerSecond ?? 0} 帧/秒`
              : status?.truckSupported === false
                ? '当前车辆未适配'
                : '等待驾驶室画面'
          }
          accessory={<Status tone={drawing ? 'good' : 'idle'} />}
        />
      </Group>
      <div className="ats-tools" aria-label="ATS 工具" lang="zh-CN">
        <Button small glass busy={busy === 'diagnostics'} disabled={disabled} onClick={() => void run('diagnostics')}>
          检查连接
        </Button>
        <Button
          small
          glass
          busy={busy === 'repair'}
          disabled={disabled || connected}
          onClick={() => void run('repair')}
        >
          诊断与修复
        </Button>
        <Button small glass busy={busy === 'logs'} disabled={disabled} onClick={() => void run('logs')}>
          查看日志
        </Button>
      </div>
      <div className="ats-feedback" role="status" aria-live="polite" aria-atomic="true">
        {message && !error ? <Note tone="calm">{message}</Note> : null}
        {error ? <Note tone="bad">{error}</Note> : null}
      </div>
      {!IN_APP ? <Note>这是界面预览，尚未连接本机 ATS。启动、诊断和修复仅在桌面程序中可用。</Note> : null}
      {diagnostics ? (
        <details className="ats-diagnostics">
          <summary>安装检查详情</summary>
          <dl>
            <dt>游戏版本</dt>
            <dd>{diagnostics.gameVersion ?? '未识别'}</dd>
            <dt>游戏路径</dt>
            <dd>{diagnostics.gameDir ?? '未找到'}</dd>
            <dt>游戏进程</dt>
            <dd>{diagnostics.gameRunning ? '运行中（上次检查）' : '未运行（上次检查）'}</dd>
            <dt>游戏插件</dt>
            <dd>{diagnostics.pluginCurrent ? '当前版本' : '需要检查'}</dd>
            <dt>屏幕 MOD</dt>
            <dd>{diagnostics.modInstalled ? '已部署' : '未检测到'}</dd>
            <dt>Ford DLC 文件</dt>
            <dd>{diagnostics.fordDlcInstalled ? '已检测到' : '未检测到'}</dd>
          </dl>
          <p>{diagnostics.message}</p>
          <p>DLC 文件检查不代表已激活，也不代表车内功能已通过实测。</p>
        </details>
      ) : null}
      <Group title="设置与账户" place={5}>
        <Row title="设置" detail="游戏安装与插件管理" link onClick={openSettings} />
        <Row title="音乐与视频账户" detail="登录 Spotify、Apple Music 或 YouTube" link onClick={openAccounts} />
        <Row title="安全卸载" detail="从游戏移除 WestPlay 并选择是否保留设置" danger link onClick={uninstall} />
      </Group>
    </Panel>
  )
}
