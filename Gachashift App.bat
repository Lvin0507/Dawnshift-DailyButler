@echo off
rem Opens the Gachashift app from source, using the Python launcher (pyw) that the
rem python.org installer adds. Set GACHASHIFT_PYTHON to use a specific pythonw.exe instead.
cd /d "%~dp0"
if defined GACHASHIFT_PYTHON (
    start "" "%GACHASHIFT_PYTHON%" -m gachashift.ui
) else (
    start "" pyw -3 -m gachashift.ui
)