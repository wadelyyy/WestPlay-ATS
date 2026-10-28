import { call } from './bridge'

/** Read-only checks from the ATS companion backend. File presence does not prove DLC activation. */
export interface AtsDiagnostics {
  gameRunning: boolean
  gameDir: string | null
  gameVersion: string | null
  pluginCurrent: boolean
  fordDlcInstalled: boolean
  modInstalled: boolean
  gameHome: string | null
  logs: string | null
  message: string
}

export const atsDiagnostics = () => call<AtsDiagnostics>('ats_diagnostics')
export const atsLaunchGame = () => call<{ message: string }>('ats_launch_game')
export const atsRepair = () => call<{ message: string; done: boolean }>('ats_repair')
export const atsOpenLogs = () => call<void>('ats_open_logs')
