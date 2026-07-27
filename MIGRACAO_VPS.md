# Migração do Agente de Relatórios GoAkira para o VPS

Este guia é para colar na conversa do Claude Desktop **já aberto na máquina do VPS**
(via Área de Trabalho Remota). Aquela sessão do Claude não tem o histórico desta
conversa — este documento contém tudo que ela precisa saber para executar a
migração sozinha, com acesso local real à máquina.

## Contexto (resuma isso para o Claude do VPS)

O "Agente de Relatórios GoAkira" é um pipeline Python que lê transcrições de
reunião do Google Meet (via Drive/Gmail), gera atas e resumos com Claude, e
envia relatórios diário/semanal/mensal por e-mail. Hoje ele roda no notebook
local do Rafael via Windows Task Scheduler — e falha com frequência porque o
notebook dorme ou desliga. O objetivo desta migração é rodar o mesmo pipeline
neste VPS (que fica ligado 24/7), usando a mesma arquitetura (Windows +
Task Scheduler), só que num servidor sempre disponível.

## Passo 1 — Pré-requisitos

Verificar/instalar nesta máquina (Windows Server, EC2):

- **Python 3.12** — https://www.python.org/downloads/ (marcar "Add to PATH" na instalação)
- **Git for Windows** — https://git-scm.com/download/win
- **Node.js LTS** — https://nodejs.org (necessário só para gerar os PPTX mensais)

Confirme com:
```powershell
python --version
git --version
node --version
```

## Passo 2 — Clonar o repositório

Repositório: `https://github.com/consultororafaelnunes/Go-Akira-Consultoria-.git`
(privado — o Git vai abrir o navegador para login do GitHub na primeira vez).

```powershell
cd C:\
mkdir GoAkira
cd GoAkira
git clone https://github.com/consultororafaelnunes/Go-Akira-Consultoria-.git "Agente de Relatorios"
cd "Agente de Relatorios"
```

## Passo 3 — Instalar dependências

```powershell
pip install -r requirements.txt
npm install pptxgenjs
```

> Nota: `requirements.txt` também tem `sentence-transformers`, `numpy` e
> `pypdf`, usados por uma outra iniciativa ("segundo cérebro", `brain_*.py`)
> não relacionada a este pipeline. Pode instalar tudo mesmo assim (não atrapalha),
> ou comentar essas 3 linhas se quiser uma instalação mais enxuta.

## Passo 4 — Recriar o `.env`

O `.env` **nunca é versionado** (está no `.gitignore`) — precisa ser recriado
manualmente. Peça ao Rafael os valores reais (ele tem o `.env` original no
notebook) e crie um arquivo `.env` na raiz do projeto com esta estrutura:

```
ANTHROPIC_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
SMTP_USER=c10@goakira.com.br
SMTP_PASSWORD=
RECIPIENT_EMAIL=patricia.cotti@goakira.com.br
DIRECTORS_EMAILS=jose.fugice@goakira.com.br,patricia.cotti@goakira.com.br
WEEKLY_EXTRA_RECIPIENTS=fabiana.hamada@goakira.com.br,antonio.prates@goakira.com.br
DAILY_EXTRA_RECIPIENTS=fabiana.hamada@goakira.com.br,antonio.prates@goakira.com.br
OPPORTUNITY_EXTRA_RECIPIENTS=fabiana.hamada@goakira.com.br,antonio.prates@goakira.com.br
MONTHLY_RECIPIENTS=patricia.cotti@goakira.com.br
SENDER_NAME=Agente de Reuniões GoAkira
SMTP_HOST=smtp.gmail.com
DRIVE_ROOT_FOLDER_ID=
```

**Importante**: o `GOOGLE_REFRESH_TOKEN` funciona igual em qualquer máquina
(não é preso ao notebook) — não precisa gerar um token novo, só copiar o valor
atual.

## Passo 5 — Validar antes de agendar

Rode manualmente uma vez, em modo seguro (não envia nada, não cria atas):

```powershell
python main.py --dry-run
```

Se aparecer `Pipeline diário concluído!` sem erro de credenciais, está pronto.

## Passo 6 — Agendar (Task Scheduler)

Use o script `setup_vps_scheduler.ps1` (está na raiz do projeto). Ele gera os
`.bat` de execução com o caminho real desta máquina (não usa os `.bat` do
notebook local, que têm caminho fixo do OneDrive) e cria as 3 tarefas —
diário (ter-sex 08:30), semanal (segunda 09:00) e monitor (ter-sex 09:30).
Rode como Administrador:

```powershell
cd "C:\GoAkira\Agente de Relatorios"
powershell -ExecutionPolicy Bypass -File .\setup_vps_scheduler.ps1
```

## Passo 7 — Rodar em paralelo antes de desligar o local

Recomendação: deixar o VPS e o notebook local rodando ao mesmo tempo por
alguns dias (o notebook pode ficar em `--dry-run` para não duplicar
e-mails/atas), só para confirmar que o VPS está estável. Depois disso,
desabilitar as tarefas do Task Scheduler no notebook local:

```powershell
# No notebook LOCAL, não no VPS:
Disable-ScheduledTask -TaskName "GoAkira - Agente de Reunioes"
Disable-ScheduledTask -TaskName "GoAkira - Resumo Semanal"
Disable-ScheduledTask -TaskName "GoAkira - Monitor do Agente"
```

## Checklist final

- [ ] Python, Git, Node.js instalados no VPS
- [ ] Repositório clonado
- [ ] Dependências instaladas (`pip` + `npm`)
- [ ] `.env` recriado com os valores reais
- [ ] `python main.py --dry-run` rodou sem erro
- [ ] Tarefas agendadas criadas (`setup_vps_scheduler.ps1`)
- [ ] Rodou em paralelo por alguns dias sem diferença
- [ ] Task Scheduler do notebook local desabilitado
