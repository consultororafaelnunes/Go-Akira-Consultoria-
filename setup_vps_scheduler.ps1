# setup_vps_scheduler.ps1
# Cria as tarefas agendadas do Agente GoAkira no VPS (Windows Server / EC2).
# Adaptado de agendar_tarefa.ps1 (versão notebook local) — aqui não há
# configuração de bateria porque o VPS fica sempre ligado.
# Execute como Administrador: botão direito -> Executar com o PowerShell

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatAgente   = Join-Path $ScriptDir "executar_agente_vps.bat"
$BatSemanal  = Join-Path $ScriptDir "executar_semanal_vps.bat"
$BatMonitor  = Join-Path $ScriptDir "executar_monitor_vps.bat"
$BatAuditoria = Join-Path $ScriptDir "executar_auditoria_vps.bat"
$Usuario     = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host "Pasta do projeto detectada: $ScriptDir"
Write-Host "Usuario: $Usuario"
Write-Host ""

# Gera os .bat aqui mesmo, com o caminho real deste VPS — evita depender dos
# .bat originais do notebook local, que têm o caminho do OneDrive fixo.
# Usa "python" do PATH em vez de um caminho fixo de instalação.
$PythonCmd = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonCmd) {
    Write-Host "ERRO: 'python' nao encontrado no PATH. Instale o Python 3.12 e marque 'Add to PATH'." -ForegroundColor Red
    exit 1
}
Write-Host "Python detectado: $PythonCmd"

# Janela de 72h (nao 24h): a dedup por _message_id (summaries_*.json) impede ata
# duplicada, entao ampliar a busca so tem upside — qualquer dia sem execucao
# (fim de semana, VPS reiniciando) se autocura no proximo run. Foi exatamente o
# vao sexta-tarde -> proximo run que orfanou uma reuniao real (Acai Island 24/07).
@"
@echo off
chcp 65001 > nul
set PYTHONUTF8=1
cd /d "$ScriptDir"
echo === %DATE% %TIME% INICIADO === >> agente.log
"$PythonCmd" main.py --hours 72 >> agente.log 2>&1
echo === %DATE% %TIME% FINALIZADO === >> agente.log
"@ | Set-Content -Path $BatAgente -Encoding ASCII

@"
@echo off
chcp 65001 > nul
set PYTHONUTF8=1
cd /d "$ScriptDir"
echo === %DATE% %TIME% INICIADO === >> semanal.log
"$PythonCmd" weekly_report.py >> semanal.log 2>&1
echo === %DATE% %TIME% FINALIZADO === >> semanal.log
"@ | Set-Content -Path $BatSemanal -Encoding ASCII

@"
@echo off
chcp 65001 > nul
set PYTHONUTF8=1
cd /d "$ScriptDir"
echo === %DATE% %TIME% INICIADO === >> monitor.log
"$PythonCmd" monitor_agente.py >> monitor.log 2>&1
echo === %DATE% %TIME% FINALIZADO === >> monitor.log
"@ | Set-Content -Path $BatMonitor -Encoding ASCII

# Auditoria de cobertura: roda depois do diario e checa se toda reuniao de
# cliente de ontem virou ata. --alertar envia e-mail (padrao do monitor) quando
# ha furo; sempre registra no auditoria.log (exit code 2 quando ha furo).
# E a rede de seguranca que teria pego a Acai Island no mesmo dia.
@"
@echo off
chcp 65001 > nul
set PYTHONUTF8=1
cd /d "$ScriptDir"
echo === %DATE% %TIME% INICIADO === >> auditoria.log
"$PythonCmd" audit_cobertura.py --alertar >> auditoria.log 2>&1
echo === %DATE% %TIME% FINALIZADO === >> auditoria.log
"@ | Set-Content -Path $BatAuditoria -Encoding ASCII

Write-Host "OK: .bat gerados (agente, semanal, monitor, auditoria)"
Write-Host ""

# Como o VPS fica sempre ligado (sem bateria), so precisamos garantir que a
# tarefa inicie assim que possivel e nao dependa de rede local especial.
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

$Principal = New-ScheduledTaskPrincipal `
    -UserId $Usuario `
    -LogonType S4U `
    -RunLevel Highest

# ── Tarefa 1: Pipeline diario (seg-sex 08:30) ─────────────────────────────────
# Segunda incluida de proposito: com janela de 72h, a run de segunda varre a
# sexta a tarde e o fim de semana, fechando o vao que orfanou a Acai Island.

$NomePipeline = "GoAkira - Agente de Reunioes"

if (Get-ScheduledTask -TaskName $NomePipeline -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomePipeline -Confirm:$false
    Write-Host "Tarefa anterior removida: $NomePipeline"
}

$AcaoPipeline = New-ScheduledTaskAction -Execute $BatAgente

$GatilhoPipeline = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "08:30"

Register-ScheduledTask `
    -TaskName $NomePipeline `
    -Action $AcaoPipeline `
    -Trigger $GatilhoPipeline `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Pipeline diario do Agente de Reunioes GoAkira - seg a sex as 08:30, janela 72h (VPS)" | Out-Null

Write-Host "OK: $NomePipeline (seg-sex 08:30, janela 72h)"

# ── Tarefa 2: Resumo semanal (segunda 09:00) ──────────────────────────────────

$NomeSemanal = "GoAkira - Resumo Semanal"

if (Get-ScheduledTask -TaskName $NomeSemanal -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomeSemanal -Confirm:$false
    Write-Host "Tarefa anterior removida: $NomeSemanal"
}

$AcaoSemanal = New-ScheduledTaskAction -Execute $BatSemanal

$GatilhoSemanal = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Monday -At "09:00"

Register-ScheduledTask `
    -TaskName $NomeSemanal `
    -Action $AcaoSemanal `
    -Trigger $GatilhoSemanal `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Resumo semanal por consultor GoAkira - segunda as 09:00 (VPS)" | Out-Null

Write-Host "OK: $NomeSemanal (segunda 09:00)"

# ── Tarefa 3: Monitor de falhas (ter-sex 09:30) ───────────────────────────────

$NomeMonitor = "GoAkira - Monitor do Agente"

if (Get-ScheduledTask -TaskName $NomeMonitor -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomeMonitor -Confirm:$false
    Write-Host "Tarefa anterior removida: $NomeMonitor"
}

$AcaoMonitor = New-ScheduledTaskAction -Execute $BatMonitor

$GatilhoMonitor = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "09:30"

Register-ScheduledTask `
    -TaskName $NomeMonitor `
    -Action $AcaoMonitor `
    -Trigger $GatilhoMonitor `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Monitor do pipeline diario GoAkira - avisa por e-mail em caso de falha - seg a sex as 09:30 (VPS)" | Out-Null

Write-Host "OK: $NomeMonitor (seg-sex 09:30)"

# ── Tarefa 4: Auditoria de cobertura (seg-sex 09:00) ──────────────────────────
# Roda entre o diario (08:30) e o monitor (09:30). Confere se toda reuniao de
# cliente de ontem virou ata; registra furos em auditoria.log (exit code 2).

$NomeAuditoria = "GoAkira - Auditoria de Cobertura"

if (Get-ScheduledTask -TaskName $NomeAuditoria -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomeAuditoria -Confirm:$false
    Write-Host "Tarefa anterior removida: $NomeAuditoria"
}

$AcaoAuditoria = New-ScheduledTaskAction -Execute $BatAuditoria

$GatilhoAuditoria = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "09:00"

Register-ScheduledTask `
    -TaskName $NomeAuditoria `
    -Action $AcaoAuditoria `
    -Trigger $GatilhoAuditoria `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Auditoria de cobertura de atas GoAkira - seg a sex as 09:00 (VPS)" | Out-Null

Write-Host "OK: $NomeAuditoria (seg-sex 09:00)"

# ── Resultado ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Tarefas ativas neste VPS:"
Write-Host "  Diario    : seg-sex as 08:30 (janela 72h) -> $BatAgente"
Write-Host "  Auditoria : seg-sex as 09:00 -> $BatAuditoria"
Write-Host "  Monitor   : seg-sex as 09:30 -> $BatMonitor"
Write-Host "  Semanal   : segunda as 09:00 -> $BatSemanal"
Write-Host ""
Write-Host "Lembrete: confirme que o .env e o batch (.bat) apontam para este"
Write-Host "caminho ($ScriptDir) antes de considerar a migracao concluida."
