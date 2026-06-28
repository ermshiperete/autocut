REM Start OBS Studio and then after closing that call GD Wuerfel Export
cd "C:\Program Files\obs-studio\bin\64bit"
"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
start C:\Windows\System32\wsl.exe -d Ubuntu -- bash -c /home/kirche/autocut/autocut.sh --fallback-upload --autostart --use-start-time