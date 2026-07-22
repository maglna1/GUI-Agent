param(
    [string]$DestinationRoot = $(if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $HOME '.codex\skills' })
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repositoryRoot 'execution'
$resolvedDestinationRoot = [System.IO.Path]::GetFullPath($DestinationRoot)
$destination = Join-Path $resolvedDestinationRoot 'cua-midscene'
$allowedPrefix = $resolvedDestinationRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

Push-Location $source
try {
    & npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build TypeScript Skill package"
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md'))) {
    throw "Skill source not found: $source"
}

if (-not $destination.StartsWith($allowedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Skill destination must stay under DestinationRoot: $destination"
}

$publishFiles = @(
    '.env.example',
    '.gitignore',
    '.npmrc',
    'README.md',
    'SKILL.md',
    'package.json',
    'package-lock.json',
    'tsconfig.build.json',
    'tsconfig.json'
)
$publishDirectories = @('agents', 'cua', 'dist', 'executors', 'projects', 'references', 'schemas')
$packageFiles = [System.Collections.Generic.List[System.IO.FileInfo]]::new()

foreach ($relativeFile in $publishFiles) {
    $path = Join-Path $source $relativeFile
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required package file not found: $path"
    }
    $packageFiles.Add((Get-Item -LiteralPath $path))
}

foreach ($relativeDirectory in $publishDirectories) {
    $path = Join-Path $source $relativeDirectory
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "Required package directory not found: $path"
    }
    foreach ($file in Get-ChildItem -LiteralPath $path -Recurse -File) {
        $relativePath = $file.FullName.Substring($source.Length).TrimStart([char[]]@('\', '/'))
        $segments = $relativePath -split '[\\/]'
        $excludedDirectory = $segments | Where-Object {
            $_ -in @('tests', 'node_modules', '.venv', '__pycache__', 'reports', 'runs', 'cache', 'midscene_run')
        }
        $isPrivateEnvironment = $file.Name -like '.env*' -and $file.Name -ne '.env.example'
        if ($excludedDirectory -or $isPrivateEnvironment -or $file.Extension -in @('.pyc', '.log')) {
            continue
        }
        $packageFiles.Add($file)
    }
}

if (Test-Path -LiteralPath $destination) {
    Remove-Item -LiteralPath $destination -Recurse -Force
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null

foreach ($packageFile in $packageFiles) {
    $relativePath = $packageFile.FullName.Substring($source.Length).TrimStart([char[]]@('\', '/'))
    $sourcePath = $packageFile.FullName
    $destinationPath = Join-Path $destination ($relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    $destinationDirectory = Split-Path -Parent $destinationPath
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
}

Push-Location $destination
try {
    & npm ci --omit=dev --ignore-scripts
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Skill runtime dependencies"
    }
}
finally {
    Pop-Location
}

Write-Output "Installed cua-midscene Skill package: $destination ($($packageFiles.Count) files)"
