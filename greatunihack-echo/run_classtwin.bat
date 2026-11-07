@echo off
cd /d "%~dp0classtwin"
set PY=python
if exist "%USERPROFILE%\anaconda3\python.exe" set PY="%USERPROFILE%\anaconda3\python.exe"
echo Installing packages (first time only, about 1 minute)...
%PY% -m pip install -q -r requirements.txt
echo.
echo Starting ClassTwin... your browser will open at http://localhost:8501
echo Keep this window open. Close it to stop the app.
%PY% -m streamlit run app.py
pause
