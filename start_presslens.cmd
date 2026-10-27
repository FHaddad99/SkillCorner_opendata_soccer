@echo off
setlocal
set "PRESSLENS_PYTHON=%USERPROFILE%\.local\bin\python3.14.exe"
if exist "%PRESSLENS_PYTHON%" goto local_python
python "%~dp0scripts\run_presslens.py" %*
exit /b %errorlevel%
:local_python
"%PRESSLENS_PYTHON%" "%~dp0scripts\run_presslens.py" %*
exit /b %errorlevel%
