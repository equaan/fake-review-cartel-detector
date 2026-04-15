$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$uvicornExe = Join-Path $repoRoot "venv\Scripts\uvicorn.exe"
$ngrokWinGetPath = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ngrok.exe"

function Wait-ForHttpOk {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Url,
    [int]$TimeoutSeconds = 60,
    [int]$IntervalSeconds = 2,
    [hashtable]$Headers = @{}
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 5
      if ([int]$response.StatusCode -eq 200) {
        return $true
      }
    } catch {
      Start-Sleep -Seconds $IntervalSeconds
    }
  }

  return $false
}

function Get-NgrokTunnelInfo {
  param(
    [int]$TimeoutSeconds = 45
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    foreach ($port in 4040..4100) {
      try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/tunnels" -UseBasicParsing -TimeoutSec 3
        $payload = $resp.Content | ConvertFrom-Json
        $httpsTunnel = $payload.tunnels | Where-Object { $_.public_url -like "https://*" } | Select-Object -First 1
        if ($httpsTunnel -and $httpsTunnel.public_url) {
          return [pscustomobject]@{
            PublicUrl = [string]$httpsTunnel.public_url
            InspectPort = [int]$port
          }
        }
      } catch {
        continue
      }
    }

    Start-Sleep -Seconds 2
  }

  return $null
}

if (-not (Test-Path $uvicornExe)) {
  throw "uvicorn not found at '$uvicornExe'. Create venv and install backend requirements first."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is not available in this shell. Install Node.js and retry."
}

$ngrokExe = $null
$ngrokCmdInfo = Get-Command ngrok -ErrorAction SilentlyContinue
if ($ngrokCmdInfo) {
  $ngrokExe = $ngrokCmdInfo.Source
} elseif (Test-Path $ngrokWinGetPath) {
  $ngrokExe = $ngrokWinGetPath
} else {
  throw "ngrok command not found. Install ngrok or add it to PATH."
}

$backendCmd = "Set-Location '$backendDir'; & '$uvicornExe' src.api:app --reload --port 8000"
$frontendCmd = "Set-Location '$frontendDir'; `$env:DANGEROUSLY_DISABLE_HOST_CHECK='true'; npm start"
$ngrokCmd = "Set-Location '$repoRoot'; & '$ngrokExe' http 3000 --host-header=localhost:3000 --log stdout"

# Clean up stale ngrok process from previous runs so inspect ports are not locked.
$existingNgrok = Get-Process ngrok -ErrorAction SilentlyContinue
if ($existingNgrok) {
  $existingNgrok | ForEach-Object { Stop-Process -Id $_.Id -Force }
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null

Write-Output "Waiting for backend health check..."
$backendReady = Wait-ForHttpOk -Url "http://127.0.0.1:8000/health" -TimeoutSeconds 90
if (-not $backendReady) {
  throw "Backend did not become healthy at http://127.0.0.1:8000/health within timeout."
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd | Out-Null

Write-Output "Waiting for frontend to be available..."
$frontendReady = Wait-ForHttpOk -Url "http://127.0.0.1:3000" -TimeoutSeconds 120
if (-not $frontendReady) {
  throw "Frontend did not become available at http://127.0.0.1:3000 within timeout."
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", $ngrokCmd | Out-Null

Write-Output "Waiting for ngrok tunnel..."
$tunnelInfo = Get-NgrokTunnelInfo -TimeoutSeconds 45
if (-not $tunnelInfo) {
  throw "ngrok tunnel URL was not detected from local ngrok inspect API ports (4040-4100)."
}

$publicUrl = $tunnelInfo.PublicUrl
$inspectPort = $tunnelInfo.InspectPort

# This makes /health appear in the ngrok inspector request history.
$ngrokHealthReady = Wait-ForHttpOk -Url "$publicUrl/health" -TimeoutSeconds 45 -Headers @{ Accept = "application/json" }
$ngrokStatsReady = Wait-ForHttpOk -Url "$publicUrl/stats" -TimeoutSeconds 45 -Headers @{ Accept = "application/json" }

Set-Content -Path (Join-Path $repoRoot "ngrok_url.txt") -Value $publicUrl

Write-Output "Started backend, frontend, and ngrok in separate PowerShell windows."
Write-Output "Open http://localhost:3000 on this PC."
Write-Output "Use this ngrok URL on your laptop: $publicUrl"
Write-Output "ngrok inspector UI: http://127.0.0.1:$inspectPort"
Write-Output "Saved ngrok URL to: $repoRoot\ngrok_url.txt"
Write-Output "Laptop health check URL: $publicUrl/health"
Write-Output "Laptop health check URL: $publicUrl/stats"
if ($ngrokHealthReady) {
  Write-Output "ngrok health probe: OK (public /health is responding)."
} else {
  Write-Output "ngrok health probe: FAILED (public /health not responding yet)."
}
if ($ngrokStatsReady) {
  Write-Output "ngrok health check: OK (public /stats is responding)."
} else {
  Write-Output "ngrok health check: FAILED (public /stats not responding yet)."
}
