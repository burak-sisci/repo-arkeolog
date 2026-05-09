@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [HATA] Python PATH uzerinde bulunamadi. Python 3.11+ kurun veya py kullanicisiysaniz package.json icindeki api scriptini py -m uvicorn olarak degistirin.
  pause
  exit /b 1
)

if not exist "frontend\node_modules" (
  echo [bilgi] frontend bagimliliklari kuruluyor...
  cd frontend
  call npm install
  cd ..
)

if not exist "node_modules" (
  echo [bilgi] kok npm paketleri kuruluyor...
  call npm install
)

echo [bilgi] Tek komutla API + Next baslatiliyor...
call npm run dev
pause
