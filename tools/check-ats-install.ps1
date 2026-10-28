param(
    [string]$InstallDirectory,
    [string]$ManifestPath,
    [string]$OutputPath,
    [switch]$SkipShortcuts
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
if (-not $InstallDirectory) {
    $InstallDirectory = Join-Path (Split-Path -Parent $repoPath) 'Installed\ATS WestPlay'
}
if (-not $ManifestPath) { $ManifestPath = Join-Path $repoPath 'docs\package-manifest.json' }
$installRoot = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\', '/')
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if (-not $manifest.installedFiles -or @($manifest.installedFiles).Count -lt 6) {
    throw 'The package manifest has no full installed-file list. Bundle the current production binary first.'
}
$checks = @()
foreach ($file in $manifest.installedFiles) {
    if ([IO.Path]::IsPathRooted($file.path)) { throw 'Manifest contains an absolute resource path.' }
    $destination = [IO.Path]::GetFullPath((Join-Path $installRoot $file.path))
    if (-not $destination.StartsWith($installRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Manifest resource escapes the installation directory.'
    }
    $exists = Test-Path -LiteralPath $destination -PathType Leaf
    $actualHash = if ($exists) { (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash } else { $null }
    $checks += [pscustomobject]@{
        path = $file.path
        exists = $exists
        expectedSha256 = $file.sha256
        actualSha256 = $actualHash
        passed = $exists -and $actualHash -eq $file.sha256
    }
}
$shortcuts = @()
if (-not $SkipShortcuts) {
    $expectedTarget = Join-Path $installRoot 'westplay.exe'
    $shell = New-Object -ComObject WScript.Shell
    try {
        $links = @(
            [pscustomobject]@{ location = 'desktop'; path = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'ATS WestPlay.lnk') },
            [pscustomobject]@{ location = 'startMenu'; path = (Join-Path ([Environment]::GetFolderPath('Programs')) 'ATS WestPlay\ATS WestPlay.lnk') }
        )
        foreach ($item in $links) {
            $exists = Test-Path -LiteralPath $item.path -PathType Leaf
            $target = $null
            $arguments = $null
            $workingDirectory = $null
            if ($exists) {
                # CreateShortcut only loads an existing link here. Save() is never called.
                $link = $shell.CreateShortcut($item.path)
                $target = $link.TargetPath
                $arguments = $link.Arguments
                $workingDirectory = $link.WorkingDirectory
                [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($link)
            }
            $shortcuts += [pscustomobject]@{
                location = $item.location
                exists = $exists
                target = $target
                arguments = $arguments
                workingDirectory = $workingDirectory
                passed = $exists -and [string]::Equals($target, $expectedTarget, [StringComparison]::OrdinalIgnoreCase) -and [string]::IsNullOrWhiteSpace($arguments)
            }
        }
    }
    finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell) }
}
$uninstaller = Test-Path -LiteralPath (Join-Path $installRoot 'uninstall.exe') -PathType Leaf
$failures = @($checks | Where-Object { -not $_.passed }).Count + @($shortcuts | Where-Object { -not $_.passed }).Count
$report = [pscustomobject]@{
    utc = [DateTime]::UtcNow.ToString('o')
    installDirectory = $installRoot
    installerSha256 = $manifest.sha256
    manifestPath = [IO.Path]::GetFullPath($ManifestPath)
    status = if ($failures -eq 0 -and $uninstaller) { 'passed' } else { 'failed' }
    fileCount = $checks.Count
    failedChecks = $failures
    uninstallerPresent = $uninstaller
    shortcutsChecked = -not [bool]$SkipShortcuts
    files = $checks
    shortcuts = $shortcuts
    scope = 'Read-only installed artifacts and shortcut fields; no app, game, GUI, account or gameplay test.'
}
$json = $report | ConvertTo-Json -Depth 7
if ($OutputPath) {
    $outputFullPath = [IO.Path]::GetFullPath($OutputPath)
    $outputParent = Split-Path -Parent $outputFullPath
    if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) { throw 'Output directory must already exist.' }
    $json | Set-Content -LiteralPath $outputFullPath -Encoding utf8
}
$json
if ($report.status -ne 'passed') { exit 1 }
