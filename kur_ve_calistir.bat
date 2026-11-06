@echo off
chcp 65001 >nul
title Asphalt 8 Kayit Duzenleyici - Otomatik Kurulum
cd /d "%~dp0"

echo === Python kontrol ediliyor ===
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)

if not defined PY (
    echo Python bulunamadi. winget ile kuruluyor...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [HATA] winget yok. Python'u https://www.python.org/downloads/ adresinden
        echo kurun ve kurulumda "Add python.exe to PATH" kutusunu isaretleyin.
        start https://www.python.org/downloads/
        pause
        exit /b 1
    )
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [HATA] Python kurulamadi.
        pause
        exit /b 1
    )
    rem Yeni kurulan Python'u bu pencerede bul
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        set "PY="%LocalAppData%\Programs\Python\Python312\python.exe""
    ) else (
        set "PY=py -3"
    )
)

echo Kullanilan: %PY%
%PY% --version || (echo [HATA] Python calismiyor. & pause & exit /b 1)

echo === Tkinter (arayuz) kontrol ediliyor ===
%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [UYARI] Tkinter yok. Python kurulumunu "Modify" ile acip
    echo "tcl/tk and IDLE" secenegini isaretleyin. Simdilik komut satiri modu calisir.
    pause
)

echo === Program baslatiliyor ===
%PY% a8_kayit_duzenleyici.py %*
if errorlevel 1 pause
