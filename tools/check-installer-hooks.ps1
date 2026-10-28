param(
    [Parameter(Mandatory = $true)][string]$MakeNsisPath,
    [Parameter(Mandatory = $true)][string]$TauriUtilsPath,
    [Parameter(Mandatory = $true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$workspacePath = Split-Path -Parent $repoPath
$checkedOutput = [IO.Path]::GetFullPath($OutputDirectory)
if (-not $checkedOutput.StartsWith($workspacePath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The smoke-check output must remain inside this workspace.'
}
New-Item -ItemType Directory -Path $checkedOutput -Force | Out-Null
$executablePath = Join-Path $checkedOutput 'hooks-smoke.exe'
$fixturePath = Join-Path $PSScriptRoot 'nsis-hooks-smoke.nsi'
& $MakeNsisPath '/V2' ('/DATS_NSIS_UTILS=' + [IO.Path]::GetFullPath($TauriUtilsPath)) ('/DATS_TEST_OUTPUT=' + $executablePath) $fixturePath
if ($LASTEXITCODE -ne 0) { throw 'NSIS hook compilation failed.' }

$smokeProcess = Start-Process -FilePath $executablePath -WorkingDirectory $checkedOutput -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
if ($smokeProcess.ExitCode -ne 0) { throw 'NSIS shortcut smoke-check fixture failed.' }

$shell = New-Object -ComObject WScript.Shell
$results = foreach ($name in @('start-menu.lnk', 'desktop.lnk', 'foreign.lnk')) {
    $shortcut = $shell.CreateShortcut((Join-Path $checkedOutput $name))
    $expected = if ($name -eq 'foreign.lnk') { '--keep' } else { '' }
    if ($shortcut.Arguments -ne $expected) { throw ('Unexpected shortcut arguments: ' + $name + ' = ' + $shortcut.Arguments) }
    [pscustomobject]@{ shortcut = $name; arguments = $shortcut.Arguments; target = $shortcut.TargetPath }
}
$json = $results | ConvertTo-Json -Depth 3
[IO.File]::WriteAllText((Join-Path $checkedOutput 'shortcut-check.json'), $json, [Text.UTF8Encoding]::new($false))
Write-Output $json
