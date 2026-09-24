# Projeto: Correção do rastreamento de gravações do Google Meet

Status: **implementado e validado tecnicamente, ainda não plugado no pipeline principal.**
Última atualização: 24/09/2026.

## 1. Problema

Desde 22/07/2026 (Rapid Release), o Google passou a salvar gravação, transcrição
e notas de reuniões numa pasta **"Google Meet"** no Drive do organizador, com uma
subpasta por reunião. A pasta antiga "Meet Recordings" virou "Legacy Meet
Recordings" dentro dela.

O pipeline original (`fetch_transcripts.py`) descobre reuniões varrendo uma
pasta do Drive por caminho/ID, previamente compartilhada por cada consultor com
`c10@goakira.com.br`. Essa dependência gerou dois furos de cobertura reais:

1. **24/07 a 10/08/2026** — a pasta nova não era varrida (só a antiga), fazendo
   reuniões de Viavolt (10/08) e Urla (06/08) sumirem do pipeline.
2. **Ago–set/2026** — quatro consultores (Ivan Orefice, Thais Andrade, Kelly
   Almeida, Marco Paixão) nunca chegaram a compartilhar a pasta nova com
   `c10@`, ficando **invisíveis ao pipeline por 1 a 3 meses**, sem nenhum erro
   visível — a auditoria de cobertura não pegava porque a causa era estrutural
   (pasta nunca compartilhada), não um parsing incorreto.

Causa raiz: o pipeline depende de "alguém lembrar de compartilhar uma pasta",
e essa pasta muda de lugar/estrutura por decisão do Google, fora do nosso
controle. Qualquer solução que continue varrendo pastas está sujeita a repetir
o mesmo furo com o próximo consultor novo ou a próxima reorganização do Google.

## 2. Solução

Eliminar a dependência de pasta compartilhada: ler as gravações direto da
**Google Meet REST API**, por usuário, via uma service account com
**Domain-Wide Delegation (DWD)** — sem depender de where o Google decide
guardar o arquivo.

```
service account (DWD) ──impersona──> cada consultor (sub=email)
                                          │
                                          ├─ Meet API v2: conferenceRecords → recordings/transcripts
                                          │  (retorna o file ID no Drive, não o caminho da pasta)
                                          │
                                          └─ Directory API: lista usuários ativos do domínio
                                             (fallback: lista fixa em consultants.py)
```

### Por que isso resolve o problema de raiz

- `conferenceRecords.list` busca por **organizador/participante**, não por
  pasta — um consultor novo aparece automaticamente assim que participa de uma
  reunião, sem precisar compartilhar nada.
- `recordings[].driveDestination.file` e `transcripts[].docsDestination.document`
  dão o **ID do arquivo no Drive diretamente**, que não muda mesmo que o Google
  reorganize pastas de novo.
- Fallback de histórico (`files.list` por `mimeType=video/mp4`, sem filtro de
  pasta) cobre o que ficou em "Legacy Meet Recordings" ou qualquer pasta antiga.

## 3. Arquitetura de acesso (sem arquivo de chave)

- Projeto GCP: `backup-vps-504817`
- Service account: `meet-collector@backup-vps-504817.iam.gserviceaccount.com`
  (Client ID DWD `109382709593139755988`)
- Escopos autorizados no Admin Console (Segurança → Delegação em todo o
  domínio), todos **somente leitura**:
  - `meetings.space.readonly`
  - `drive.readonly`
  - `admin.directory.user.readonly`
- `c10@goakira.com.br` tem o papel **Criador de token da conta de serviço**
  (`roles/iam.serviceAccountTokenCreator`) direto na service account — **não
  existe arquivo de chave JSON**.
- A impersonação de cada consultor (`sub=<email>`) é feita assinando um JWT via
  **IAM Service Account Credentials API** (`signJwt`), usando a credencial ADC
  local de quem roda o script, depois trocado por um access token OAuth de
  curta duração (1h).

Esse desenho foi escolhido em vez de uma chave de arquivo porque uma chave
`drive.readonly` com DWD dá acesso de leitura ao Drive inteiro de todo o
domínio — reduzir a superfície a "só quem tem o papel IAM certo pode assinar o
JWT, e só nesta máquina autenticada" é mais seguro do que um `.json` que
poderia vazar.

## 4. Arquivos do projeto

| Arquivo | Papel |
|---|---|
| [`meet_api_collector.py`](../meet_api_collector.py) | Coletor: autenticação DWD, `list_domain_users`, `fetch_conference_records`, `fetch_all`, `export_doc_text`, `fetch_legacy_recordings_by_mimetype`. Roda isolado hoje — ainda não é importado pelo pipeline principal. |
| [`docs/DWD_MEET_API_SETUP.md`](DWD_MEET_API_SETUP.md) | Runbook operacional: o que já está configurado, o que rodar em cada máquina nova, como testar, erros esperados. |
| `meet_collector_setup_rafael.md` (raiz do repo) | Notas originais do setup, com o snippet de código mínimo usado para validar a abordagem antes de virar `meet_api_collector.py`. |
| `.env.example` | Variáveis novas: `MEET_COLLECTOR_SA_EMAIL`, `GOOGLE_WORKSPACE_ADMIN_EMAIL`. |
| `.gitignore` | Ignora `*service-account*.json` e `credentials/` (defensivo — não há chave hoje, mas evita commit acidental se a abordagem mudar). |
| `requirements.txt` | Adiciona `requests` (usado para chamar `signJwt` e o token endpoint diretamente). |

## 5. Setup necessário (1x por máquina)

1. Confirmar no projeto `backup-vps-504817` que estas APIs estão ativas:
   Google Meet REST API, Google Drive API, Admin SDK API, **IAM Service
   Account Credentials API**.
2. Autenticar localmente com `c10@goakira.com.br`:
   ```bash
   gcloud auth application-default login
   ```
   (Google Cloud SDK instalado via `winget install --id Google.CloudSDK -e` na
   VPS Windows.) Credenciais ADC ficam em
   `%APPDATA%\gcloud\application_default_credentials.json`.
3. Conferir `.env` com `MEET_COLLECTOR_SA_EMAIL` e `GOOGLE_WORKSPACE_ADMIN_EMAIL`.
4. Smoke test:
   ```bash
   python meet_api_collector.py
   ```

Detalhes de erros esperados (`unauthorized_client`, `403` no `signJwt`,
`PERMISSION_DENIED` na Directory API) estão em
[`docs/DWD_MEET_API_SETUP.md`](DWD_MEET_API_SETUP.md).

## 6. Validação (24/09/2026)

`fetch_conference_records()` foi rodado para os 4 consultores que estavam no
furo de cobertura, confirmando que a Meet API os enxerga **sem nenhuma pasta
compartilhada**:

| Consultor | E-mail | conferenceRecords | com drive_file_id |
|---|---|---|---|
| Ivan Orefice | ivan.orefice@goakira.com.br | 50 | 12 |
| Thais Andrade | c3@goakira.com.br | 23 | 14 |
| Kelly Almeida | c8@goakira.com.br | 49 | 23 |
| Marco Paixão | marco.paixao@goakira.com.br | 15 | 9 |

Isso confirma a causa raiz: o problema nunca foi um bug de parsing, foi a
pasta nunca ter sido compartilhada — e a Meet API contorna isso completamente.

## 7. Limitações conhecidas

- **Directory API exige admin do Workspace.** `admin.directory.user.readonly`
  via DWD falha com `403 Not Authorized` quando o subject impersonado
  (`c10@`) não é super admin/admin delegado — mesmo com o escopo autorizado
  na delegação. `fetch_all()` já trata isso com fallback automático para a
  lista fixa em `consultants.CONSULTANTS`, mas um consultor **novo** cadastrado
  só em `consultants.py` (sem `c10@` virar admin delegado) não é descoberto
  automaticamente — precisa continuar sendo adicionado manualmente em
  `CONSULTANTS`, como já é feito hoje.
- **`ConferenceRecord.space` é uma string** (`"spaces/abc123"`), não um objeto
  — já corrigido no coletor, mas vale registrar para quem for estender o
  parsing.
- **Nome do arquivo/cliente não vem na resposta da Meet API** — só o `doc_id`
  da transcrição. Para extrair nome do cliente é preciso buscar o nome do
  arquivo via Drive API (`files.get`) ou usar o nome do evento no Calendar.
  Isso ainda não está implementado.
- **Dedup necessário no consumidor:** a mesma reunião aparece uma vez por
  organizador e uma vez por cada participante que também é usuário do
  domínio — quem consumir o dict de `fetch_all()` deve deduplicar por
  `conference_record`.

## 8. Próximos passos

1. Decidir se `meet_api_collector.fetch_all()` **substitui**
   `fetch_transcripts.fetch_drive_transcripts()` ou roda **em paralelo** por
   um tempo (comparando resultados) antes de desligar a varredura por pasta.
2. Implementar resolução de nome de cliente a partir do `doc_id` (via Drive
   API `files.get` ou nome do evento do Calendar), já que a Meet API não
   devolve isso.
3. Implementar o export do texto da transcrição (`export_doc_text` já existe)
   no fluxo real de geração de resumo.
4. Avaliar a **Google Workspace Events API** para receber eventos de
   gravação/transcrição em tempo real, evitando varrer tudo periodicamente
   (mencionado como possível evolução, não implementado).

## Histórico / memória relacionada

Este documento consolida o que está registrado, em português mais informal e
cronológico, nas memórias de sessão: `dwd-service-account-meet-api`,
`blind-spot-4-consultores-google-meet` e `google-meet-folder-nao-varrida`.
