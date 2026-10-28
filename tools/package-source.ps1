param(
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$PythonCommand = 'python'
)
$ErrorActionPreference = 'Stop'
$repoPath = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$outputPath = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $outputPath) { throw 'Output directory already exists; choose a new directory.' }
if ($outputPath.Equals($repoPath, [StringComparison]::OrdinalIgnoreCase) -or $outputPath.StartsWith($repoPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Choose a separate output directory outside the source repository.'
}
if (-not (Get-Command $PythonCommand -ErrorAction SilentlyContinue)) { throw 'Python 3.10+ is required for the source allowlist audit.' }

Push-Location $repoPath
try {
    # The helper starts with git ls-files --cached --others --exclude-standard -z,
    # then applies the reviewed source-only policy to the CURRENT working tree.
    & $PythonCommand (Join-Path $PSScriptRoot 'audit-source-package.py')
    if ($LASTEXITCODE -ne 0) { throw 'Source allowlist audit failed. No archive was created.' }
    $audit = Get-Content -LiteralPath 'docs\source-package-audit.json' -Raw | ConvertFrom-Json
    if (-not $audit.readyForArchiveReview -or -not $audit.files.Count) { throw 'Source file list is not ready for archive review.' }
    $version = (Get-Content -LiteralPath 'app\tauri.conf.json' -Raw | ConvertFrom-Json).version
    if ($version -notmatch '^[0-9A-Za-z._-]+$') { throw 'Unexpected version string.' }
    $revision = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read source revision.' }

    New-Item -ItemType Directory -Path $outputPath -ErrorAction Stop | Out-Null
    $zipPath = Join-Path $outputPath ('ATS-WestPlay-source-' + $version + '.zip')
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zipStream = [IO.File]::Open($zipPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $zip = [IO.Compression.ZipArchive]::new($zipStream, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($item in $audit.files) {
            $relative = [string]$item.path
            $filePath = [IO.Path]::GetFullPath((Join-Path $repoPath $relative))
            if (-not $filePath.StartsWith($repoPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw ('Source path escapes the repository: ' + $relative)
            }
            if ((Get-Item -LiteralPath $filePath).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw ('Source path became a reparse point: ' + $relative)
            }
            if ((Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) {
                throw ('Source changed after the audit: ' + $relative)
            }
            [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $filePath, $relative.Replace('\', '/'), [IO.Compression.CompressionLevel]::Optimal)
        }
    }
    finally { $zip.Dispose(); $zipStream.Dispose() }

    # Read every archived byte back. A concurrent edit must fail verification,
    # and an archive with missing/extra entries must never receive final manifests.
    $expected = @{}
    foreach ($item in $audit.files) { $expected[[string]$item.path] = [string]$item.sha256 }
    $readZip = [IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        if ($readZip.Entries.Count -ne $expected.Count) { throw 'Archive entry count differs from the audited list.' }
        foreach ($entry in $readZip.Entries) {
            if (-not $expected.ContainsKey($entry.FullName)) { throw ('Unexpected archive entry: ' + $entry.FullName) }
            $entryStream = $entry.Open()
            $hasher = [Security.Cryptography.SHA256]::Create()
            try { $entryHash = ([BitConverter]::ToString($hasher.ComputeHash($entryStream))).Replace('-', '').ToLowerInvariant() }
            finally { $hasher.Dispose(); $entryStream.Dispose() }
            if ($entryHash -ne $expected[$entry.FullName]) { throw ('Archived content hash differs: ' + $entry.FullName) }
        }
    }
    finally { $readZip.Dispose() }

    $utf8 = [Text.UTF8Encoding]::new($false)
    $fileListPath = Join-Path $outputPath 'source-files.json'
    $fileHashesPath = Join-Path $outputPath 'source-files.sha256'
    $manifest = [ordered]@{
        kind = 'source-only working-tree snapshot'
        version = $version
        baseRevision = $revision
        includesUncommittedChanges = $true
        createdUtc = [DateTime]::UtcNow.ToString('o')
        archive = [IO.Path]::GetFileName($zipPath)
        fileCount = $audit.files.Count
        files = $audit.files
    }
    [IO.File]::WriteAllText($fileListPath, ($manifest | ConvertTo-Json -Depth 6), $utf8)
    $fileHashes = ($audit.files | ForEach-Object { $_.sha256 + '  ' + $_.path }) -join "`n"
    [IO.File]::WriteAllText($fileHashesPath, $fileHashes + "`n", $utf8)
    $sums = foreach ($path in @($zipPath, $fileListPath, $fileHashesPath)) {
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() + '  ' + [IO.Path]::GetFileName($path)
    }
    [IO.File]::WriteAllText((Join-Path $outputPath 'SHA256SUMS.txt'), ($sums -join "`n") + "`n", $utf8)
    Write-Output ('Verified source files: ' + $audit.files.Count)
    Write-Output $zipPath
    $sums | Write-Output
}
finally { Pop-Location }
