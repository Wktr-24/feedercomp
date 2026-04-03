@echo off
echo === Budowanie FeederComp.exe ===
echo.

if not exist .venv\Scripts\python.exe (
    echo Tworzenie srodowiska wirtualnego...
    python -m venv .venv
)

echo Instalowanie zaleznosci...
.venv\Scripts\pip install customtkinter reportlab pyinstaller --quiet

echo Budowanie...
.venv\Scripts\pyinstaller ^
    --onedir ^
    --windowed ^
    --noupx ^
    --name=FeederComp ^
    --add-data "seed_data;seed_data" ^
    --collect-all customtkinter ^
    app\main.py

echo.
if exist dist\FeederComp\FeederComp.exe (
    echo GOTOWE! Folder: dist\FeederComp\
    echo Skopiuj caly folder na pendrive lub pulpit.
) else (
    echo BLAD: Budowanie nie powiodlo sie.
)
pause
