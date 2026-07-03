# agendar_tarefa.ps1
# Cria as tarefas agendadas do Agente GoAkira.
# Execute como Administrador: Right-click -> Run with PowerShell

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatAgente   = Join-Path $ScriptDir "executar_agente.bat"
$BatSemanal  = Join-Path $ScriptDir "executar_semanal.bat"
$BatMonitor  = Join-Path $ScriptDir "executar_monitor.bat"
$Usuario     = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -WakeToRun `
    -RunOnlyIfNetworkAvailable
# O notebook roda com frequencia na bateria — sem isto o Windows nao inicia
# (nem acorda) as tarefas quando desconectado da tomada.
$Settings.DisallowStartIfOnBatteries = $false
$Settings.StopIfGoingOnBatteries = $false

# Permitir que despertadores (RTC wake) funcionem tambem na bateria, nao so
# na tomada — sem isto o -WakeToRun acima nao tem efeito quando o PC dorme
# desconectado.
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
powercfg /SETACTIVE SCHEME_CURRENT | Out-Null
Write-Host "OK: despertadores (RTC wake) habilitados tambem na bateria"

$Principal = New-ScheduledTaskPrincipal `
    -UserId $Usuario `
    -LogonType S4U `
    -RunLevel Highest

# ── Tarefa 1: Pipeline diario (ter-sex 08:30) ─────────────────────────────────

$NomePipeline = "GoAkira - Agente de Reunioes"

if (Get-ScheduledTask -TaskName $NomePipeline -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomePipeline -Confirm:$false
    Write-Host "Tarefa anterior removida: $NomePipeline"
}

$AcaoPipeline = New-ScheduledTaskAction -Execute $BatAgente

$GatilhoPipeline = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Tuesday,Wednesday,Thursday,Friday -At "08:30"

Register-ScheduledTask `
    -TaskName $NomePipeline `
    -Action $AcaoPipeline `
    -Trigger $GatilhoPipeline `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Pipeline diario do Agente de Reunioes GoAkira - ter a sex as 08:30" | Out-Null

Write-Host "OK: $NomePipeline (ter-sex 08:30)"

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
    -Description "Resumo semanal por consultor GoAkira - segunda as 09:00" | Out-Null

Write-Host "OK: $NomeSemanal (segunda 09:00)"

# ── Tarefa 3: Monitor de falhas (ter-sex 09:30) ───────────────────────────────
# Le o agente.log apos o pipeline diario e avisa por e-mail se houve erro critico
# (ou se o log nao existe, indicando que o pipeline nem rodou).

$NomeMonitor = "GoAkira - Monitor do Agente"

if (Get-ScheduledTask -TaskName $NomeMonitor -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomeMonitor -Confirm:$false
    Write-Host "Tarefa anterior removida: $NomeMonitor"
}

$AcaoMonitor = New-ScheduledTaskAction -Execute $BatMonitor

$GatilhoMonitor = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Tuesday,Wednesday,Thursday,Friday -At "09:30"

Register-ScheduledTask `
    -TaskName $NomeMonitor `
    -Action $AcaoMonitor `
    -Trigger $GatilhoMonitor `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Monitor do pipeline diario GoAkira - avisa por e-mail em caso de falha - ter a sex as 09:30" | Out-Null

Write-Host "OK: $NomeMonitor (ter-sex 09:30)"

# ── Resultado ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Tarefas ativas:"
Write-Host "  Diario  : ter-sex as 08:30 -> $BatAgente"
Write-Host "  Semanal : segunda as 09:00 -> $BatSemanal"
Write-Host "  Monitor : ter-sex as 09:30 -> $BatMonitor"
