@echo off
echo Starting service...
python "C:\Users\benos\Desktop\Personal Projects\commercial-realestate-crawler-v3\service\service.py" start
echo Start completed with exit code %errorlevel%
echo Check logs at C:\Users\benos\Desktop\Personal Projects\commercial-realestate-crawler-v3\debug
if %errorlevel% neq 0 (
  echo Error occurred during start
  pause
)
