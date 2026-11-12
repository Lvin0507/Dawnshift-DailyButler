@echo off
rem Launch the Gachashift app from source.
rem Set GACHASHIFT_PYTHON to a specific pythonw.exe to bypass the py launcher's default.
cd /d "%~dp0"
if defined GACHASHIFT_PYTHON (
    start "" "%GACHASHIFT_PYTHON%" -m gachashift.ui
) else (
    start "" pyw -3 -m gachashift.ui
)