# Setup: Domain-Wide Delegation para o coletor da Meet API

Runbook para `meet_api_collector.py` — a solução definitiva para o furo de
cobertura documentado em 23/09/2026 (consultores cuja pasta "Google Meet"
nunca foi compartilhada com c10@ ficam invisíveis ao pipeline). Em vez de
depender de pasta compartilhada, o coletor lê direto da Meet API
impersonando cada consultor via uma service account com Domain-Wide
Delegation (DWD) — sem arquivo de chave.

## Status: setup já feito

- Projeto GCP: `backup-vps-504817`
- Service account: `meet-collector@backup-vps-504817.iam.gserviceaccount.com`
- Client ID (DWD): `109382709593139755988`
- `c10@goakira.com.br` tem o papel **Criador de token da conta de serviço**
  (`roles/iam.serviceAccountTokenCreator`) direto na service account
- DWD autorizada no Admin Console com os escopos (somente leitura):
  - `https://www.googleapis.com/auth/meetings.space.readonly`
  - `https://www.googleapis.com/auth/drive.readonly`
  - `https://www.googleapis.com/auth/admin.directory.user.readonly`

Detalhes originais em `meet_collector_setup_rafael.md` (raiz do repo).

## Como funciona sem chave

Não existe arquivo de credencial da service account. A impersonação (DWD) é
feita assinando um JWT com o claim `sub=<usuário a impersonar>` via **IAM
Service Account Credentials API** (`signJwt`), usando a identidade local de
quem roda o script — implementado em `meet_api_collector._delegated_credentials`.

## O que falta rodar (1x por máquina que for usar o coletor)

1. No projeto `backup-vps-504817`, confirmar que estas APIs estão ativas:
   - Google Meet REST API
   - Google Drive API
   - Admin SDK API
   - **IAM Service Account Credentials API** (necessária para `signJwt`)
2. Autenticar localmente com a conta `c10@goakira.com.br`:
   ```bash
   gcloud auth application-default login
   ```
3. Conferir o `.env` (ver `.env.example`):
   ```
   MEET_COLLECTOR_SA_EMAIL=meet-collector@backup-vps-504817.iam.gserviceaccount.com
   GOOGLE_WORKSPACE_ADMIN_EMAIL=c10@goakira.com.br
   ```

## Testar

```bash
python meet_api_collector.py
```

Lista os usuários ativos do domínio (Directory API) e busca `conferenceRecords`
do primeiro. Erros esperados e o que significam:

- `unauthorized_client` / `insufficient authentication scopes` — a DWD não
  propagou ainda (pode levar até ~24h) ou os escopos no Admin Console estão
  diferentes dos três acima.
- `403` no `signJwt` — a conta autenticada via `gcloud auth
  application-default login` não tem o papel Criador de token da conta de
  serviço na `meet-collector@...`.
- `PERMISSION_DENIED` na Directory API — o `GOOGLE_WORKSPACE_ADMIN_EMAIL`
  impersonado não tem privilégio de leitura de usuários no Workspace.

## Depois que o teste passar

Isso ainda não está plugado no pipeline principal (`fetch_transcripts.py` /
`main.py`) — o coletor roda isolado por enquanto. Próximo passo: decidir
entre substituir `fetch_drive_transcripts()` por `meet_api_collector.fetch_all()`
direto, ou rodar os dois em paralelo por um tempo (comparando resultados)
antes de desligar a varredura por pasta. Ver a memória
`dwd-service-account-meet-api` para o histórico da decisão.

Também vale considerar Google Workspace Events API para receber eventos de
gravação/transcrição em tempo real (evita varrer tudo periodicamente) — não
implementado ainda.
