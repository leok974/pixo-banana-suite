# Pixel Banana Suite - Development Startup Script
# Run from project root

Write-Host "Starting Pixel Banana Suite..." -ForegroundColor Green

# Start backend
Write-Host "`nStarting backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd apps\backend; python -m venv .venv; .\.venv\Scripts\activate; pip install -r requirements.txt; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1"

Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd apps\web; pnpm install; pnpm dev"

Start-Sleep -Seconds 2

Write-Host "`nServices starting up:" -ForegroundColor Green
Write-Host "  Backend:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "`nPress any key to open the browser..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Start-Process "http://localhost:5173"