"""
deep_research.py — Pesquisa profunda Plan & Execute
Fluxo: Plano → Aprovação → Execução iterativa → Relatório com citações

Melhorias v2:
- Plano adaptado ao tipo de pergunta (FACTUAL / COMPARATIVA / EXPLORATÓRIA / OPERACIONAL)
- Loop de lacunas iterativo com anti-espiral (até 3 iterações por sub-tarefa)
- Budget por qualidade: até 5 URLs por rodada, para ao atingir 6000 chars úteis
- Filtro de domínios fracos antes do webread
- Síntese com estrutura adaptada ao tipo
- Progresso com raciocínio visível via progress_cb
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Callable, Awaitable

import web_search

logger = logging.getLogger("deep_research")

# Armazena planos pendentes de aprovação: {chat_id: plan_data}
_pending_plans: dict = {}

# Domínios de baixa qualidade — ignorados no webread
DOMINIOS_FRACOS = [
    "brainly.com", "brainly.com.br", "answers.yahoo.com",
    "quora.com", "mundoeducacao.uol.com.br", "todamateria.com.br",
    "resumoescolar.com.br", "wikianswers", "/r/ask",
    "superrespostas.com.br", "perguntasrespostas.net",
]

def _url_confiavel(url: str) -> bool:
    return not any(d in url for d in DOMINIOS_FRACOS)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fase 1: Planejamento adaptado ao tipo de pergunta
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def create_plan(topic: str, router) -> dict:
    """
    LLM classifica o tipo da pergunta e gera plano adaptado.

    Returns:
        {"tipo": "FACTUAL|COMPARATIVA|EXPLORATÓRIA|OPERACIONAL", "subtarefas": [...]}
        Cada subtarefa: {"title", "objective", "queries", "sufficiency_check"}
    """
    result = await router.generate([
        {"role": "system", "content": (
            "Você é um planejador de pesquisa especializado.\n\n"
            "PASSO 1 — Classifique o tipo da pergunta em uma destas categorias:\n"
            "- FACTUAL: 'o que é', 'como funciona', 'quais são' (conceitos, tecnologias, histórico)\n"
            "- COMPARATIVA: 'X vs Y', 'qual o melhor', 'diferenças entre'\n"
            "- EXPLORATÓRIA: panorama geral de um campo, tendências, mapeamento\n"
            "- OPERACIONAL: 'como fazer', 'como implementar', decisões técnicas\n\n"
            "PASSO 2 — Crie o plano com base no tipo classificado:\n\n"
            "Se FACTUAL:\n"
            "  subtarefas = [definição precisa + escopo] + [mecanismo/funcionamento]\n"
            "  + [dados/números concretos] + [limitações e edge cases] + [fontes primárias]\n\n"
            "Se COMPARATIVA:\n"
            "  subtarefas = [critérios de comparação relevantes] + [perfil detalhado de A]\n"
            "  + [perfil detalhado de B] + [trade-offs diretos] + [quando usar cada um]\n\n"
            "Se EXPLORATÓRIA:\n"
            "  subtarefas = [mapa do campo e players] + [estado atual com dados]\n"
            "  + [tendências com evidências] + [perspectivas críticas e contra-argumentos]\n"
            "  + [referências de qualidade]\n\n"
            "Se OPERACIONAL:\n"
            "  subtarefas = [contexto e pré-requisitos] + [abordagens existentes com prós/contras]\n"
            "  + [melhor prática atual] + [riscos e armadilhas] + [exemplos concretos]\n\n"
            "REGRAS:\n"
            "- Máximo 6 sub-tarefas\n"
            "- Cada sub-tarefa deve ter EXATAMENTE estes campos:\n"
            "    title: string curta\n"
            "    objective: o que esta etapa precisa fechar\n"
            "    queries: lista de 2-3 queries de busca em português\n"
            "    sufficiency_check: 1 frase começando com 'Esta etapa está completa quando...'\n"
            "- Responda APENAS em JSON válido, sem markdown, sem blocos de código\n"
            '- Formato raiz: {"tipo": "FACTUAL", "subtarefas": [...]}'
        )},
        {"role": "user", "content": f"Tópico de pesquisa: {topic}"},
    ], temperature=0.2)

    if not isinstance(result, str):
        return _fallback_plan(topic)

    try:
        clean = result.strip()
        if clean.startswith("```"):
            clean = re.sub(r'^```\w*\n?', '', clean)
            clean = re.sub(r'\n?```$', '', clean)
        parsed = json.loads(clean)
        if isinstance(parsed, dict) and "subtarefas" in parsed:
            parsed["subtarefas"] = parsed["subtarefas"][:6]
            for st in parsed["subtarefas"]:
                if "sufficiency_check" not in st:
                    st["sufficiency_check"] = (
                        f"Esta etapa está completa quando o objetivo '{st.get('objective', '')}' "
                        "foi respondido com dados concretos."
                    )
            return parsed
        if isinstance(parsed, list):
            return {"tipo": "EXPLORATÓRIA", "subtarefas": parsed[:6]}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Falha ao parsear plano, usando fallback")

    return _fallback_plan(topic)


def _fallback_plan(topic: str) -> dict:
    return {
        "tipo": "EXPLORATÓRIA",
        "subtarefas": [
            {
                "title": "Visão geral",
                "objective": f"Contexto e definição de {topic}",
                "queries": [topic, f"{topic} definição contexto"],
                "sufficiency_check": f"Esta etapa está completa quando há uma definição clara de {topic}.",
            },
            {
                "title": "Dados e números",
                "objective": f"Estatísticas e dados sobre {topic}",
                "queries": [f"{topic} dados estatísticas números", f"{topic} pesquisa quantitativa"],
                "sufficiency_check": f"Esta etapa está completa quando há ao menos 3 dados numéricos sobre {topic}.",
            },
            {
                "title": "Análises e opiniões",
                "objective": f"Perspectivas de especialistas sobre {topic}",
                "queries": [f"{topic} análise especialista opinião", f"{topic} vantagens desvantagens"],
                "sufficiency_check": f"Esta etapa está completa quando há ao menos uma análise qualificada sobre {topic}.",
            },
            {
                "title": "Tendências",
                "objective": f"Futuro e perspectivas de {topic}",
                "queries": [f"{topic} tendências futuro previsão", f"{topic} 2025 2026"],
                "sufficiency_check": f"Esta etapa está completa quando há perspectivas ou previsões concretas sobre {topic}.",
            },
        ],
    }


def format_plan_message(topic: str, plan: "dict | list") -> str:
    """Formata o plano para exibição. Aceita novo formato (dict) ou antigo (list)."""
    if isinstance(plan, list):
        subtarefas = plan
        tipo = "GERAL"
    else:
        subtarefas = plan.get("subtarefas", [])
        tipo = plan.get("tipo", "GERAL")

    lines = [f"🔬 **Plano de Pesquisa**\n📋 Tema: _{topic}_\n🏷️ Tipo: `{tipo}`\n"]
    for i, step in enumerate(subtarefas, 1):
        title = step.get("title", f"Etapa {i}")
        obj = step.get("objective", "")
        queries = step.get("queries", [])
        lines.append(f"**{i}.** {title}")
        lines.append(f"   _{obj}_")
        for q in queries[:3]:
            lines.append(f"   🔍 `{q}`")
        lines.append("")
    lines.append("✅ Responda **ok** para iniciar ou descreva mudanças.")
    return "\n".join(lines)


def save_pending_plan(chat_id: int, topic: str, plan: "dict | list"):
    _pending_plans[chat_id] = {"topic": topic, "plan": plan}


def get_pending_plan(chat_id: int) -> "dict | None":
    return _pending_plans.get(chat_id)


def clear_pending_plan(chat_id: int):
    _pending_plans.pop(chat_id, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fase 3: Execução iterativa
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def execute_plan(
    topic: str,
    plan: "dict | list",
    router,
    progress_cb: "Callable[[str], Awaitable[None]] | None" = None,
) -> "tuple[dict, list[dict]]":
    """
    Executa o plano de pesquisa iterativamente.
    Returns: (all_data, sources)
    """
    if isinstance(plan, list):
        subtarefas = plan
        tipo = "EXPLORATÓRIA"
    else:
        subtarefas = plan.get("subtarefas", [])
        tipo = plan.get("tipo", "EXPLORATÓRIA")

    all_data = {}
    sources = []
    source_counter = [0]

    for i, subtask in enumerate(subtarefas):
        title = subtask.get("title", f"Etapa {i+1}")
        queries = subtask.get("queries", [])
        sufficiency_check = subtask.get(
            "sufficiency_check",
            f"Esta etapa está completa quando o objetivo '{subtask.get('objective', '')}' foi respondido."
        )

        if progress_cb:
            await progress_cb(
                f"🔎 [{i+1}/{len(subtarefas)}] **{title}**\n"
                f"💡 Objetivo: _{subtask.get('objective', '')}_\n"
                f"✅ Suficiente quando: _{sufficiency_check}_"
            )

        subtask_data, new_sources = await _execute_subtask(queries, source_counter, progress_cb)
        sources.extend(new_sources)

        # Loop de lacunas com anti-espiral
        MAX_GAP_ITERATIONS = 3
        queries_tentadas = list(queries)

        for _ in range(MAX_GAP_ITERATIONS):
            gap = await _evaluate_gaps(subtask, subtask_data, router, queries_tentadas)
            if not gap or gap.upper() == "COMPLETO":
                break

            palavras_gap = set(gap.lower().split())
            repetido = any(
                len(palavras_gap & set(q.lower().split())) / max(len(palavras_gap), 1) > 0.6
                for q in queries_tentadas
            )
            if repetido:
                break

            queries_tentadas.append(gap)
            if progress_cb:
                await progress_cb(f"🔄 Lacuna identificada → buscando: _{gap[:80]}_")

            gap_data, gap_sources = await _execute_subtask([gap], source_counter, None)
            subtask_data += "\n\n" + gap_data
            sources.extend(gap_sources)

        if progress_cb:
            await progress_cb(f"✓ **{title}** concluída. Avançando...")

        all_data[title] = subtask_data if subtask_data else "Sem dados encontrados."
        logger.info(f"📊 Sub-tarefa '{title}': {len(subtask_data)} chars")

    return all_data, sources


async def _execute_subtask(
    queries: list,
    source_counter: list,
    progress_cb=None,
) -> tuple:
    """Executa buscas para uma sub-tarefa e retorna dados + sources."""
    sources = []
    data_parts = []

    search_tasks = [web_search.web_search(q, max_results=3) for q in queries]
    results = await asyncio.gather(*search_tasks, return_exceptions=True)

    all_snippets = ""
    for idx, result in enumerate(results):
        if isinstance(result, Exception) or not isinstance(result, str):
            continue
        if len(result) > 50:
            all_snippets += f"\n\n### Busca: {queries[idx]}\n{result[:3000]}"

    urls = _extract_urls(all_snippets)
    urls_confiaveis = [u for u in urls if _url_confiavel(u)]

    conteudo_acumulado = 0
    MAX_CONTEUDO = 6000

    for url in urls_confiaveis[:5]:
        if conteudo_acumulado >= MAX_CONTEUDO:
            break
        try:
            content = await web_search.web_read(url)
            if content and len(content) > 200 and not content.startswith("❌"):
                source_counter[0] += 1
                sid = source_counter[0]
                sources.append({"id": sid, "url": url, "title": _extract_title(content)})
                data_parts.append(f"[Fonte {sid}] ({url}):\n{content[:4000]}")
                conteudo_acumulado += len(content)
                logger.info(f"📖 [{sid}] Leu: {url[:60]} ({len(content)} chars)")
        except Exception as e:
            logger.debug(f"Leitura falhou: {e}")

    combined = all_snippets + "\n\n" + "\n\n---\n\n".join(data_parts)
    return combined, sources


async def _evaluate_gaps(subtask: dict, data: str, router, queries_tentadas: list) -> "str | None":
    """
    Avalia lacunas com base no sufficiency_check.
    Retorna uma query de lacuna, 'COMPLETO', ou None.
    """
    if len(data) < 200:
        return subtask.get("queries", [""])[0]

    sufficiency_check = subtask.get(
        "sufficiency_check",
        "Esta etapa está completa quando o objetivo foi respondido com dados concretos."
    )
    queries_str = ", ".join(f'"{q}"' for q in queries_tentadas)

    try:
        result = await router.generate([
            {"role": "system", "content": (
                "Você é um avaliador crítico de pesquisa.\n\n"
                f"Critério de suficiência desta etapa: {sufficiency_check}\n\n"
                "Analise os dados coletados e responda com UMA das opções:\n\n"
                "1. Se o critério foi atendido → responda exatamente: COMPLETO\n\n"
                "2. Se há lacuna clara que impede o critério → "
                "responda com UMA query de busca (máximo 10 palavras)\n\n"
                "3. Se os dados são fragmentados mas nenhuma query nova resolveria → "
                "responda exatamente: COMPLETO\n\n"
                f"Queries já tentadas (não repita a mesma intenção): {queries_str}\n\n"
                f"Dados coletados (primeiros 5000 chars):\n{data[:5000]}"
            )},
            {"role": "user", "content": (
                f"Sub-tarefa: {subtask.get('title', '')} — {subtask.get('objective', '')}"
            )},
        ], temperature=0.1)

        if isinstance(result, str):
            clean = result.strip().split("\n")[0][:120]
            if "COMPLETO" in clean.upper():
                return "COMPLETO"
            if len(clean) > 10:
                return clean
    except Exception as e:
        logger.debug(f"Gap eval falhou: {e}")

    return None


def _extract_urls(text: str) -> list:
    urls = []
    seen = set()
    found = re.findall(r'https?://[^\s\)>\]]+', text)
    for url in found:
        url = url.rstrip('.,;:')
        if url not in seen and 'jina.ai' not in url:
            seen.add(url)
            urls.append(url)
    return urls


def _extract_title(content: str) -> str:
    first_line = content.strip().split("\n")[0][:100]
    return first_line.strip("# ").strip() if first_line else "Sem título"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fase 4: Síntese com citações (formato adaptado ao tipo)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ESTRUTURA_POR_TIPO = {
    "FACTUAL": (
        "# {título}\n"
        "## O que é\n## Como funciona\n## Dados concretos\n"
        "## Limitações e casos especiais\n## Fontes"
    ),
    "COMPARATIVA": (
        "# {título}\n"
        "## Critérios de comparação\n## {entidade A}\n## {entidade B}\n"
        "## Trade-offs diretos\n## Quando usar cada um\n## Fontes"
    ),
    "EXPLORATÓRIA": (
        "# {título}\n"
        "## Estado atual\n## Players e referências principais\n"
        "## Tendências com evidências\n## Perspectivas críticas\n## Fontes"
    ),
    "OPERACIONAL": (
        "# {título}\n"
        "## Contexto e pré-requisitos\n## Abordagens disponíveis\n"
        "## Recomendação com justificativa\n## Riscos e armadilhas\n## Fontes"
    ),
}


async def synthesize_with_citations(
    topic: str,
    all_data: dict,
    sources: list,
    router,
    tipo: str = "EXPLORATÓRIA",
) -> str:
    """Sintetiza dados em relatório com citações [1],[2] e estrutura adaptada ao tipo."""

    data_text = ""
    for section, content in all_data.items():
        data_text += f"\n\n## Dados da seção: {section}\n{content[:5000]}"

    source_ref = "\n".join([f"[{s['id']}] {s['url']} — {s['title']}" for s in sources])

    if len(data_text) > 20000:
        data_text = data_text[:20000] + "\n\n[... truncado por limite de contexto]"

    estrutura = ESTRUTURA_POR_TIPO.get(tipo, ESTRUTURA_POR_TIPO["EXPLORATÓRIA"])

    result = await router.generate([
        {"role": "system", "content": (
            f"Você é um analista de pesquisa especializado.\n"
            f"Tipo desta pesquisa: {tipo}\n\n"
            "REGRAS OBRIGATÓRIAS:\n"
            "1. Use citações [1], [2] ao lado de cada afirmação factual. "
            "Cada número corresponde a uma fonte real listada nos dados.\n"
            "2. Use APENAS dados dos resultados fornecidos. Se faltar dado, "
            "escreva: 'Não encontrado nas fontes consultadas.'\n"
            "3. Escreva em português brasileiro.\n"
            "4. Seja denso em fatos, não em palavras. Evite frases genéricas.\n"
            "5. Nunca invente dados, nomes, números ou URLs.\n\n"
            f"ESTRUTURA A SEGUIR:\n{estrutura}"
        )},
        {"role": "user", "content": (
            f"TÓPICO: {topic}\n\n"
            f"FONTES DISPONÍVEIS:\n{source_ref}\n\n"
            f"DADOS COLETADOS:\n{data_text}"
        )},
    ], temperature=0.2)

    if not isinstance(result, str):
        return "Erro na síntese da pesquisa."

    if "## Fontes" not in result and sources:
        result += "\n\n## Fontes\n"
        for s in sources:
            result += f"[{s['id']}] {s['url']}\n"

    try:
        base_dir = os.path.dirname(__file__)
        research_dir = os.path.join(base_dir, "research")
        os.makedirs(research_dir, exist_ok=True)
        safe_topic = "".join([c if c.isalnum() else "_" for c in topic])[:30].strip("_")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_topic}.md"
        with open(os.path.join(research_dir, filename), "w", encoding="utf-8") as f:
            f.write(result)
    except Exception as e:
        logger.warning(f"Erro ao salvar pesquisa no disco: {e}")

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fluxo legado — execução direta sem aprovação
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def research(topic: str, router, progress_cb=None) -> str:
    """Execução direta sem aprovação prévia. Mantido para compatibilidade."""
    logger.info(f"🔬 Deep Research (direto): {topic}")
    plan = await create_plan(topic, router)
    tipo = plan.get("tipo", "EXPLORATÓRIA") if isinstance(plan, dict) else "EXPLORATÓRIA"
    logger.info(f"🔬 Plano: {len(plan.get('subtarefas', []))} sub-tarefas, tipo: {tipo}")
    all_data, sources = await execute_plan(topic, plan, router, progress_cb)
    report = await synthesize_with_citations(topic, all_data, sources, router, tipo=tipo)
    logger.info(f"🔬 Relatório: {len(report)} chars, {len(sources)} fontes")
    return report
