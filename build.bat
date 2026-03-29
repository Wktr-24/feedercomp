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
    --onefile ^
    --windowed ^
    --name=FeederComp ^
    --add-data "seed_data;seed_data" ^
    --collect-all customtkinter ^
    app\main.py

echo.
if exist dist\FeederComp.exe (
    echo GOTOWE! Plik: dist\FeederComp.exe
    echo Skopiuj go na pulpit i kliknij dwukrotnie.
) else (
    echo BLAD: Budowanie nie powiodlo sie.
)
pause
