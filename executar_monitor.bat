@echo off
chcp 65001 > nul
set PYTHONUTF8=1
cd /d "C:\Users\rafae\OneDrive\Desktop\DOCS GOAKIRA\Agente de Relatórios"
echo === %DATE% %TIME% INICIADO === >> monitor.log
"C:\Users\rafae\AppData\Local\Programs\Python\Python312\python.exe" monitor_agente.py >> monitor.log 2>&1
echo === %DATE% %TIME% FINALIZADO === >> monitor.log
