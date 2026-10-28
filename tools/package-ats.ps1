param(
    [string]$CargoCommand = 'cargo',
    [switch]$BundleOnly,
    [string]$LogPath
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$tauriPath = Join-Path $repoPath 'node_modules\.bin\tauri.cmd'
$temporaryPath = Join-Path $repoPath 'target\package-tmp'
$stagingPath = Join-Path $repoPath 'target\ats-bundle-staging'
$oldTemp = [Environment]::GetEnvironmentVariable('TEMP', 'Process')
$oldTmp = [Environment]::GetEnvironmentVariable('TMP', 'Process')
$oldCargoTarget = [Environment]::GetEnvironmentVariable('CARGO_TARGET_DIR', 'Process')
if (-not $LogPath) { $LogPath = Join-Path $repoPath 'docs\package-ats.log' }
$LogPath = [IO.Path]::GetFullPath($LogPath)

if (-not (Get-Command $CargoCommand -ErrorAction SilentlyContinue)) {
    throw '需要 Rust MSVC 工具链。请安装 Rust 或用 -CargoCommand 指定 cargo.exe。'
}
if (-not (Test-Path -LiteralPath $tauriPath)) {
    throw '缺少项目依赖。请先在项目根目录执行 npm install。'
}

Push-Location $repoPath
New-Item -ItemType Directory -Path $temporaryPath -Force | Out-Null
# Tauri 2.12 uses bundle.useLocalToolsDir (target/.tauri) for the tools cache.
# Keep temporary extraction files on that volume too, without changing user settings.
[Environment]::SetEnvironmentVariable('TEMP', $temporaryPath, 'Process')
[Environment]::SetEnvironmentVariable('TMP', $temporaryPath, 'Process')
function Write-PackageLog([string]$Message) {
    $Message | Tee-Object -FilePath $LogPath -Append
}
try {
    Write-PackageLog ('[' + (Get-Date -Format o) + '] Package ATS WestPlay. BundleOnly=' + [bool]$BundleOnly)
    Write-PackageLog ('Process temporary files: ' + $temporaryPath)
    # The native plugin must exist before Tauri validates/copies bundled resources.
    if (-not $BundleOnly) {
        & $CargoCommand build --locked --release -p westplay-plugin 2>&1 | Tee-Object -FilePath $LogPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'ATS 插件编译失败。' }
    }
    $pluginPath = Join-Path $repoPath 'target\release\westplay.dll'
    if (-not (Test-Path -LiteralPath $pluginPath)) { throw '编译后未找到 westplay.dll。' }

    if (-not $BundleOnly) {
        Push-Location (Join-Path $repoPath 'app')
        try {
            & $tauriPath build --no-bundle --ci 2>&1 | Tee-Object -FilePath $LogPath -Append
            if ($LASTEXITCODE -ne 0) { throw 'ATS WestPlay 程序构建失败。' }
        }
        finally { Pop-Location }
    }
    $appPath = Join-Path $repoPath 'target\release\westplay.exe'
    if (-not (Test-Path -LiteralPath $appPath)) { throw '未找到 release\westplay.exe。' }
    $appHash = (Get-FileHash -LiteralPath $appPath -Algorithm SHA256).Hash

    # CLI 2.12.1 restores the input with write+truncate even with --no-binary-patching.
    # Bundle a byte-identical copy so the running companion remains untouched.
    $stagingRelease = Join-Path $stagingPath 'release'
    New-Item -ItemType Directory -Path $stagingRelease -Force | Out-Null
    $stagedApp = Join-Path $stagingRelease 'westplay.exe'
    Copy-Item -LiteralPath $appPath -Destination $stagedApp -Force
    if ((Get-FileHash -LiteralPath $stagedApp -Algorithm SHA256).Hash -ne $appHash) {
        throw '程序副本校验失败，打包已停止。'
    }
    $toolsParent = Join-Path $stagingPath '.tauri'
    $existingNsis = Join-Path $repoPath 'target\.tauri\NSIS'
    $stagedNsis = Join-Path $toolsParent 'NSIS'
    if ((Test-Path -LiteralPath $existingNsis) -and -not (Test-Path -LiteralPath $stagedNsis)) {
        New-Item -ItemType Directory -Path $toolsParent -Force | Out-Null
        Copy-Item -LiteralPath $existingNsis -Destination $toolsParent -Recurse
    }
    Write-PackageLog ('Staged input binary: ' + $stagedApp)
    Write-PackageLog ('Bundler tools: ' + $toolsParent)
    [Environment]::SetEnvironmentVariable('CARGO_TARGET_DIR', $stagingPath, 'Process')
    Push-Location (Join-Path $repoPath 'app')
    try {
        & $tauriPath bundle --bundles nsis --no-binary-patching --ci 2>&1 | Tee-Object -FilePath $LogPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'ATS WestPlay 安装器构建失败。' }
    }
    finally { Pop-Location }

    if ((Get-FileHash -LiteralPath $appPath -Algorithm SHA256).Hash -ne $appHash) {
        throw '原程序在打包期间发生改变，请重新打包以确保版本一致。'
    }
    Write-PackageLog ('Original app binary unchanged: SHA256 ' + $appHash)
    $bundlePath = Join-Path $repoPath 'target\release\bundle\nsis'
    New-Item -ItemType Directory -Path $bundlePath -Force | Out-Null
    $installers = @(Get-ChildItem -LiteralPath (Join-Path $stagingRelease 'bundle\nsis') -Filter '*setup.exe' -File)
    if ($installers.Count -eq 0) { throw '构建结束，但未找到 NSIS 安装程序。' }
    $installers | ForEach-Object {
        $destination = Join-Path $bundlePath $_.Name
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
        $hash = Get-FileHash -LiteralPath $destination -Algorithm SHA256
        Write-PackageLog ($hash.Hash + '  ' + $hash.Path)
    }
    if ($installers.Count -ne 1) { throw '安装器数量不唯一，请检查打包输出。' }
    $config = Get-Content -LiteralPath (Join-Path $repoPath 'app\tauri.conf.json') -Raw | ConvertFrom-Json
    $installedFiles = @([pscustomobject]@{
        path = 'westplay.exe'
        size = (Get-Item -LiteralPath $appPath).Length
        sha256 = $appHash
    })
    foreach ($resource in $config.bundle.resources.PSObject.Properties) {
        $source = [IO.Path]::GetFullPath((Join-Path (Join-Path $repoPath 'app') $resource.Name))
        if (Test-Path -LiteralPath $source -PathType Container) {
            $sourcePrefix = $source.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
            foreach ($file in @(Get-ChildItem -LiteralPath $source -Recurse -File)) {
                $relative = $file.FullName.Substring($sourcePrefix.Length)
                $installedFiles += [pscustomobject]@{
                    path = ((Join-Path $resource.Value $relative) -replace '\\', '/')
                    size = $file.Length
                    sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
                }
            }
        }
        else {
            $installedFiles += [pscustomobject]@{
                path = ($resource.Value -replace '\\', '/')
                size = (Get-Item -LiteralPath $source).Length
                sha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
            }
        }
    }
    $installerPath = Join-Path $bundlePath $installers[0].Name
    $manifest = [pscustomobject]@{
        status = 'candidate; installed artifact and real installed-app checks pending'
        builtUtc = [DateTime]::UtcNow.ToString('o')
        installer = $installerPath
        size = (Get-Item -LiteralPath $installerPath).Length
        sha256 = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash
        appSha256 = $appHash
        pluginSha256 = (Get-FileHash -LiteralPath $pluginPath -Algorithm SHA256).Hash
        identity = $config.identifier
        product = $config.productName
        version = $config.version
        updaterArtifacts = [bool]$config.bundle.createUpdaterArtifacts
        shortcutArguments = ''
        launchMode = 'companion-only; start ATS manually or use the explicit in-app launch button'
        generatedScript = (Join-Path $stagingRelease 'nsis\x64\installer.nsi')
        installedFiles = @($installedFiles | Sort-Object path)
    }
    $manifestPath = Join-Path $repoPath 'docs\package-manifest.json'
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding utf8
    Write-PackageLog ('Installed-file manifest: ' + $manifestPath + ' (' + $installedFiles.Count + ' files)')
}
catch {
    Write-PackageLog ('FAILED: ' + $_.Exception.Message)
    throw
}
finally {
    [Environment]::SetEnvironmentVariable('TEMP', $oldTemp, 'Process')
    [Environment]::SetEnvironmentVariable('TMP', $oldTmp, 'Process')
    [Environment]::SetEnvironmentVariable('CARGO_TARGET_DIR', $oldCargoTarget, 'Process')
    Pop-Location
}
