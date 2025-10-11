param(
    [string]$PythonExe = "python",
    [string]$NodeExe = "npm",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..")

Write-Host "Working directory: $repoRoot"
Push-Location $repoRoot

try {
    Write-Host "[1/5] Installing Python dependencies..."
    & $PythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

    Write-Host "[2/5] Applying Django migrations..."
    & $PythonExe "web/backend/manage.py" migrate
    if ($LASTEXITCODE -ne 0) { throw "Django migrate failed" }

    Write-Host "[3/5] Installing frontend dependencies..."
    Push-Location (Join-Path $repoRoot "web/frontend")
    & $NodeExe install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    Pop-Location

    Write-Host "[4/5] Starting Django development server on port $BackendPort..."
    $backendCommand = "$PythonExe web/backend/manage.py runserver 127.0.0.1:$BackendPort"
    $backendScript = "Set-Location `"$repoRoot`"; $backendCommand"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript

    Write-Host "[5/5] Starting Vite dev server on port $FrontendPort (proxying to http://localhost:$BackendPort)..."
    $frontendCommand = "$NodeExe run dev"
    $frontendScript = "& { Set-Location `"$repoRoot\web\frontend`"; `$env:VITE_API_BASE_URL = 'http://localhost:$BackendPort'; `$env:VITE_DEV_SERVER_PORT = '$FrontendPort'; `$env:VITE_DEV_SERVER_HOST = '127.0.0.1'; $frontendCommand }"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript

    Write-Host "All services launched. Backend: http://localhost:$BackendPort  Frontend: http://localhost:$FrontendPort"
    Write-Host "Close the opened terminal windows or press Ctrl+C in them to stop the servers."
}
finally {
    Pop-Location
}
