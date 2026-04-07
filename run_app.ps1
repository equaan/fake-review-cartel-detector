$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$uvicornExe = Join-Path $repoRoot "venv\Scripts\uvicorn.exe"
$ngrokWinGetPath = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ngrok.exe"

if (-not (Test-Path $uvicornExe)) {
  throw "uvicorn not found at '$uvicornExe'. Create venv and install backend requirements first."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is not available in this shell. Install Node.js and retry."
}

$ngrokCommand = "ngrok"
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
  if (Test-Path $ngrokWinGetPath) {
    $ngrokCommand = "`"$ngrokWinGetPath`""
  } else {
    throw "ngrok command not found. Install ngrok or add it to PATH."
  }
}

$backendCmd = "Set-Location '$backendDir'; '$uvicornExe' src.api:app --reload --port 8000"
$frontendCmd = "Set-Location '$frontendDir'; npm start"
$ngrokCmd = "Set-Location '$repoRoot'; $ngrokCommand http 3000 --log stdout"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd | Out-Null
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList "-NoExit", "-Command", $ngrokCmd | Out-Null

Write-Output "Started backend, frontend, and ngrok in separate PowerShell windows."
Write-Output "Open http://localhost:3000 on this PC."
Write-Output "Use the ngrok https URL from the ngrok window on your laptop."
