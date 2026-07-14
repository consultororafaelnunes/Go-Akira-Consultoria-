"""
summarize.py — Sumariza transcrições do Google Meet usando Claude.

Recebe a lista bruta de transcrições (dicts de fetch_transcripts.py) e
devolve lista de resumos estruturados prontos para create_minutes.py.
"""

import json
import os
import re
import time
from datetime import date

import anthropic

MODEL      = "claude-haiku-4-5-20251001"
MAX_CHARS  = 15000   # corte máximo por transcrição
MAX_TOKENS = 4096
MAX_RETRY  = 3       # tentativas por transcrição em caso de JSON inválido

SYSTEM_PROMPT = """Você é um assistente especializado em análise de reuniões corporativas da GoAkira.
Analise a transcrição e retorne APENAS um JSON válido, sem texto adicional, sem markdown.

Campos obrigatórios:
{
  "cliente":          "Nome do cliente ou empresa principal mencionada na reunião",
  "titulo_reuniao":   "Título descritivo da reunião (ex: 'Revisão de roadmap Q3')",
  "data_reuniao":     "DD/MM/YYYY — extraia da transcrição; se ausente, use a data do email",
  "duracao_estimada": "Estimativa com base no conteúdo (ex: '45min', '1h 30min') — só é usada quando não há duração real da gravação disponível",
  "participantes":    ["Nome Sobrenome"],
  "resumo":           "Parágrafo objetivo (máx. ~600 caracteres) com os temas discutidos, decisões tomadas e contexto geral",
  "acionaveis":       ["Ação objetiva com responsável e prazo quando mencionados — máx. ~110 caracteres cada"],
  "proximos_passos":  ["Próximo passo acordado — máx. ~110 caracteres"],
  "alertas":          ["Risco ou insatisfação real, em frase objetiva — máx. ~110 caracteres — deixe [] se não houver"],
  "sentimento":       "positivo | neutro | preocupante",
  "prioridade":       "baixa | media | alta"
}

Critérios de sentimento — aplique com precisão:

POSITIVO: A reunião demonstra engajamento ativo do cliente, aprovação de entregas ou decisões
  concretas que fazem o projeto avançar. Sinais: cliente validou etapas, tomou decisões,
  mostrou entusiasmo, aprovou propostas, confirmou próximos passos com disposição.

NEUTRO: A reunião é analítica — discute desafios, gaps, oportunidades ou diagnósticos do
  negócio do cliente como parte normal do trabalho de consultoria. Mesmo que os temas sejam
  difíceis (sazonalidade, concorrência, limitações de produto, modelo de vendas), se a reunião
  fluiu dentro do escopo do projeto sem sinais de risco relacional, classifique como neutro.

PREOCUPANTE: Classifique como preocupante APENAS se houver pelo menos um dos seguintes sinais:
  1. Risco de churn — cliente sinaliza (direta ou indiretamente) que pode parar de pagar ou
     abandonar o projeto (ex: "não estou vendo resultado", "vou precisar rever o contrato",
     "não sei se vou conseguir continuar");
  2. Mudança societária — cliente menciona venda do negócio, dissolução de sociedade, saída de
     sócio relevante ou reestruturação que coloque o projeto em risco;
  3. Insatisfação com a GoAkira — reclamação sobre atendimento, entregáveis, qualidade,
     prazo ou postura da consultoria;
  4. Risco jurídico ou de imagem à GoAkira — cliente menciona práticas irregulares (ex: não
     emite nota fiscal, compra sem nota, sonegação) que possam gerar exposição à GoAkira.

Regras adicionais:
- prioridade alta: sentimento preocupante com risco imediato de churn, questão jurídica ou societária
- alertas: só preencha com riscos concretos e evidenciados na transcrição; nunca invente riscos
- Se não identificar o cliente, use "Não identificado"
- Responda SOMENTE com o JSON"""


# Singleton — criado uma vez e reutilizado em todo o processo
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    return json.loads(text)


def _truncate(text: str, max_chars: int = MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    # Corta no final de uma frase para não quebrar o JSON do Claude
    cut = text[:max_chars]
    last_period = max(cut.rfind(". "), cut.rfind(".\n"))
    return (cut[:last_period + 1] if last_period > max_chars * 0.8 else cut) + "\n[TRANSCRIÇÃO TRUNCADA]"


def summarize_transcript(transcript: dict) -> dict | None:
    """
    Envia uma transcrição ao Claude e retorna o resumo estruturado.
    Faz até MAX_RETRY tentativas em caso de JSON inválido.
    Retorna None apenas se todas as tentativas falharem ou houver erro de API.
    """
    client = _get_client()

    user_content = (
        f"Assunto do email: {transcript.get('subject', '')}\n"
        f"Data do email: {transcript.get('date', date.today().strftime('%d/%m/%Y'))}\n\n"
        f"--- TRANSCRIÇÃO ---\n"
        f"{_truncate(transcript['transcript'])}\n"
        f"--- FIM ---\n\n"
        f"Retorne o JSON estruturado."
    )

    for attempt in range(MAX_RETRY):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            summary = _parse_json(msg.content[0].text)
            summary["_message_id"] = transcript.get("message_id", "")
            # O nome de cliente já identificado a partir do nome do arquivo (canônico,
            # via client_aliases.normalize_client) é sempre mais confiável do que a Claude
            # tentando extrair o nome da empresa do texto da transcrição — nunca sobrescrever.
            if transcript.get("cliente"):
                summary["cliente"] = transcript["cliente"]
            # Consultor que de fato gravou/conduziu a reunião (pasta de origem no
            # Drive) — mais confiável que a tabela estática de consultants.py
            # quando o cliente tem fases diferentes com responsáveis diferentes
            # (ex: BP com um consultor, Manuais com outro).
            if transcript.get("consultor"):
                summary["consultor"] = transcript["consultor"]
            # Duração real do vídeo da gravação (Drive videoMediaMetadata) é
            # sempre mais precisa do que a estimativa do Claude a partir do
            # texto da transcrição — a estimativa só é usada como fallback
            # quando o vídeo da gravação não foi encontrado/sincronizado.
            if transcript.get("duracao_real"):
                summary["duracao_estimada"] = transcript["duracao_real"]
            try:
                from consultants import get_fase_reuniao
                summary["fase"] = get_fase_reuniao(summary.get("cliente"), summary.get("consultor"))
            except Exception:
                pass
            return summary

        except json.JSONDecodeError as e:
            if attempt < MAX_RETRY - 1:
                print(f"   ⚠️  JSON inválido (tentativa {attempt + 1}/{MAX_RETRY}) — retentando...")
            else:
                print(f"   ⚠️  JSON inválido após {MAX_RETRY} tentativas — pulando")
            continue

        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"   ⚠️  Rate limit — aguardando {wait}s...")
            time.sleep(wait)
            continue

        except anthropic.APIError as e:
            print(f"   ❌ Erro de API Anthropic: {e}")
            return None

        except Exception as e:
            print(f"   ❌ Erro inesperado ao sumarizar: {e}")
            return None

    return None


def summarize_all(transcripts: list[dict]) -> list[dict]:
    """
    Sumariza todas as transcrições e retorna apenas os resumos válidos.
    """
    if not transcripts:
        return []

    print(f"\n🤖 Sumarizando {len(transcripts)} transcrição(ões) com Claude ({MODEL})...")
    summaries = []

    for i, t in enumerate(transcripts, 1):
        label = t.get("subject", f"Reunião {i}")[:60]
        print(f"   [{i}/{len(transcripts)}] {label}")

        summary = summarize_transcript(t)
        if summary:
            summaries.append(summary)
            cliente = summary.get("cliente", "?")
            titulo  = summary.get("titulo_reuniao", "?")[:40]
            print(f"   ✅ {cliente} — {titulo}")
        else:
            print(f"   ⚠️  Falha — pulando esta transcrição")

    print(f"\n✅ {len(summaries)}/{len(transcripts)} resumo(s) gerado(s)")
    return summaries
