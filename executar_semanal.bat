@echo off
chcp 65001 > nul
set PYTHONUTF8=1
cd /d "C:\Users\rafae\OneDrive\Desktop\DOCS GOAKIRA\Agente de Relatórios"
echo === %DATE% %TIME% INICIADO === >> semanal.log
"C:\Users\rafae\AppData\Local\Programs\Python\Python312\python.exe" weekly_report.py >> semanal.log 2>&1
echo === %DATE% %TIME% FINALIZADO === >> semanal.log
