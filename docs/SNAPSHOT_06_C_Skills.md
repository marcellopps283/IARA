
--- FILE: deep_research.py ---
"""
deep_research.py — Pesquisa profunda Plan & Execute
Fluxo: Plano → Aprovação → Execução iterativa → Relatório com citações

Inspirado na arquitetura do Gemini Deep Research:
1. LLM decompõe tema em sub-tarefas
2. Usuário aprova/edita plano
3. Loop iterativo com detecção de lacunas
4. Progresso em tempo real
5. Relatório com citações granulares [1], [2]
"""

import asyncio
import json
import logging
import re
from typing import Callable, Awaitable

import web_search

logger = logging.getLogger("deep_research")

# Armazena planos pendentes de aprovação: {chat_id: plan_data}
_pending_plans: dict = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fase 1: Planejamento
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def create_plan(topic: str, router) -> list[dict]:
    """
    LLM analisa o tema e gera um plano de pesquisa com sub-tarefas.
    
    Returns:
        Lista de sub-tarefas: [{"title": "...", "objective": "...", "queries": ["..."]}]
    """
    result = await router.generate([
        {"role": "system", "content": (
            "Você é um planejador de pesquisa. Analise o tópico e decomponha-o "
            "em 4-6 SUB-TAREFAS de pesquisa, cobrindo diferentes ângulos.\n\n"
            "Responda APENAS em JSON válido, sem markdown, sem ```.\n"
            "Formato:\n"
            '[{"title": "Título curto", "objective": "O que buscar", "queries": ["query1", "query2"]}]\n\n'
            "Cada sub-tarefa deve ter:\n"
            "- title: Título descritivo curto\n"
            "- objective: O que essa etapa busca descobrir\n"
            "- queries: 2-3 queries de busca variadas\n\n"
            "Exemplos de ângulos:\n"
            "- Definição e contexto\n"
            "- Dados quantitativos e estatísticas\n"
            "- Players e concorrentes\n"
            "- Preços e custos\n"
            "- Análises de especialistas\n"
            "- Perspectivas e tendências futuras\n"
            "- Contexto brasileiro (se relevante)\n\n"
            "Escreva queries em português."
        )},
        {"role": "user", "content": f"Tópico de pesquisa: {topic}"},
    ], temperature=0.2)

    if not isinstance(result, str):
        return [{"title": "Pesquisa geral", "objective": topic, "queries": [topic]}]

    # Parsear JSON
    try:
        # Limpar possíveis wrappers de markdown
        clean = result.strip()
        if clean.startswith("```"):
            clean = re.sub(r'^```\w*\n?', '', clean)
            clean = re.sub(r'\n?```$', '', clean)
        plan = json.loads(clean)
        if isinstance(plan, list) and len(plan) > 0:
            return plan[:6]  # Máximo 6 sub-tarefas
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Falha ao parsear plano, usando fallback")

    # Fallback: gerar plano simples
    return [
        {"title": "Visão geral", "objective": f"Contexto e definição de {topic}", "queries": [topic, f"{topic} definição contexto"]},
        {"title": "Dados e números", "objective": f"Estatísticas e dados sobre {topic}", "queries": [f"{topic} dados estatísticas números", f"{topic} pesquisa quantitativa"]},
        {"title": "Análises", "objective": f"Opiniões de especialistas sobre {topic}", "queries": [f"{topic} análise especialista opinião", f"{topic} vantagens desvantagens"]},
        {"title": "Tendências", "objective": f"Futuro e perspectivas de {topic}", "queries": [f"{topic} tendências futuro previsão", f"{topic} 2025 2026"]},
    ]


def format_plan_message(topic: str, plan: list[dict]) -> str:
    """Formata o plano para exibição no Telegram."""
    lines = [f"🔬 **Plano de Pesquisa**\n📋 Tema: _{topic}_\n"]
    for i, step in enumerate(plan, 1):
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


def save_pending_plan(chat_id: int, topic: str, plan: list[dict]):
    """Salva plano pendente de aprovação."""
    _pending_plans[chat_id] = {"topic": topic, "plan": plan}


def get_pending_plan(chat_id: int) -> dict | None:
    """Recupera plano pendente."""
    return _pending_plans.get(chat_id)


def clear_pending_plan(chat_id: int):
    """Limpa plano pendente após aprovação."""
    _pending_plans.pop(chat_id, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fase 3: Execução iterativa
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def execute_plan(
    topic: str,
    plan: list[dict],
    router,
    progress_cb: Callable[[str], Awaitable[None]] | None = None,
) -> tuple[dict, list[dict]]:
    """
    Executa o plano de pesquisa iterativamente.
    
    Returns:
        (all_data, sources) — dados por sub-tarefa + lista de fontes com URLs
    """
    all_data = {}
    sources = []  # [{"id": 1, "url": "...", "title": "..."}]
    source_counter = [0]  # Mutable counter

    for i, subtask in enumerate(plan):
        title = subtask.get("title", f"Etapa {i+1}")
        queries = subtask.get("queries", [])

        if progress_cb:
            await progress_cb(f"📊 **{i+1}/{len(plan)}**: {title}...")

        # Buscar com queries planejadas
        subtask_data, new_sources = await _execute_subtask(
            queries, source_counter, progress_cb
        )
        sources.extend(new_sources)

        # Avaliar lacunas
        if subtask_data and progress_cb:
            gaps = await _evaluate_gaps(subtask, subtask_data, router)
            if gaps:
                await progress_cb(f"🔍 Lacuna detectada, buscando mais: _{gaps[:80]}_")
                gap_data, gap_sources = await _execute_subtask(
                    [gaps], source_counter, None
                )
                subtask_data += "\n\n" + gap_data
                sources.extend(gap_sources)

        all_data[title] = subtask_data if subtask_data else "Sem dados encontrados."
        logger.info(f"📊 Sub-tarefa '{title}': {len(subtask_data)} chars")

    return all_data, sources


async def _execute_subtask(
    queries: list[str],
    source_counter: list[int],
    progress_cb: Callable | None = None,
) -> tuple[str, list[dict]]:
    """Executa buscas para uma sub-tarefa e retorna dados + sources."""
    sources = []
    data_parts = []

    # Busca paralela
    search_tasks = [web_search.web_search(q, max_results=3) for q in queries]
    results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Coletar snippets
    all_snippets = ""
    for idx, result in enumerate(results):
        if isinstance(result, Exception) or not isinstance(result, str):
            continue
        if len(result) > 50:
            all_snippets += f"\n\n### Busca: {queries[idx]}\n{result[:3000]}"

    # Extrair e ler URLs
    urls = _extract_urls(all_snippets)
    for url in urls[:3]:  # Máximo 3 leituras profundas por sub-tarefa
        try:
            content = await web_search.web_read(url)
            if content and len(content) > 200:
                source_counter[0] += 1
                sid = source_counter[0]
                sources.append({"id": sid, "url": url, "title": _extract_title(content)})
                data_parts.append(f"[Fonte {sid}] ({url}):\n{content[:4000]}")
                logger.info(f"📖 [{sid}] Leu: {url[:60]}")
        except Exception as e:
            logger.debug(f"Leitura falhou: {e}")

    combined = all_snippets + "\n\n" + "\n\n---\n\n".join(data_parts)
    return combined, sources


async def _evaluate_gaps(subtask: dict, data: str, router) -> str | None:
    """LLM avalia se há lacunas nos dados coletados para essa sub-tarefa."""
    if len(data) < 200:
        return subtask.get("queries", [""])[0]  # Dados muito escassos, rebuscar

    try:
        result = await router.generate([
            {"role": "system", "content": (
                "Analise os dados coletados para a sub-tarefa. "
                "Se há uma lacuna importante (informação que deveria estar mas não está), "
                "responda com UMA query de busca para preencher essa lacuna.\n"
                "Se os dados são suficientes, responda APENAS: COMPLETO\n"
                "Responda em português."
            )},
            {"role": "user", "content": (
                f"Sub-tarefa: {subtask.get('title', '')} — {subtask.get('objective', '')}\n\n"
                f"Dados coletados (primeiros 3000 chars):\n{data[:3000]}"
            )},
        ], temperature=0.1)

        if isinstance(result, str) and "COMPLETO" not in result.upper():
            gap_query = result.strip().split("\n")[0][:120]
            if len(gap_query) > 10:
                return gap_query
    except Exception as e:
        logger.debug(f"Gap eval falhou: {e}")

    return None


def _extract_urls(text: str) -> list[str]:
    """Extrai URLs únicas do texto."""
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
    """Tenta extrair título do conteúdo."""
    first_line = content.strip().split("\n")[0][:100]
    return first_line.strip("# ").strip() if first_line else "Sem título"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fase 4: Síntese com citações
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def synthesize_with_citations(
    topic: str,
    all_data: dict,
    sources: list[dict],
    router,
) -> str:
    """Sintetiza todos os dados em relatório com citações [1], [2]."""
    
    # Montar contexto com dados rotulados por fonte
    data_text = ""
    for section, content in all_data.items():
        data_text += f"\n\n## Dados da seção: {section}\n{content[:5000]}"

    # Montar referência de fontes
    source_ref = "\n".join([f"[{s['id']}] {s['url']} — {s['title']}" for s in sources])

    # Limitar tamanho
    if len(data_text) > 20000:
        data_text = data_text[:20000] + "\n\n[... truncado por limite de contexto]"

    result = await router.generate([
        {"role": "system", "content": (
            "Você é um analista de pesquisa profissional. Com base nos dados coletados, "
            "crie um RELATÓRIO DE PESQUISA completo e estruturado.\n\n"
            "REGRAS OBRIGATÓRIAS:\n"
            "1. Use citações granulares [1], [2] etc. ao lado de cada afirmação factual\n"
            "2. Os números das citações correspondem às fontes listadas\n"
            "3. Use APENAS dados dos resultados fornecidos — NUNCA invente dados\n"
            "4. Se não há dados para alguma seção, diga explicitamente\n"
            "5. Escreva em português brasileiro\n\n"
            "ESTRUTURA OBRIGATÓRIA:\n"
            "# [Título da Pesquisa]\n\n"
            "## Resumo Executivo\n"
            "[2-3 parágrafos resumindo as principais descobertas]\n\n"
            "## [Seções temáticas com dados e citações]\n"
            "[Use quantas seções forem necessárias baseado nos dados]\n\n"
            "## Dados e Números Chave\n"
            "[Estatísticas com citações]\n\n"
            "## Perspectivas e Tendências\n"
            "[Se houver dados sobre futuro]\n\n"
            "## Fontes\n"
            "[Lista numerada de todas as fontes citadas com URL]"
        )},
        {"role": "user", "content": (
            f"TÓPICO: {topic}\n\n"
            f"FONTES DISPONÍVEIS:\n{source_ref}\n\n"
            f"DADOS COLETADOS:\n{data_text}"
        )},
    ], temperature=0.2)

    if not isinstance(result, str):
        return "Erro na síntese da pesquisa."

    # Append source reference at end if not included
    if "## Fontes" not in result and sources:
        result += "\n\n## Fontes\n"
        for s in sources:
            result += f"[{s['id']}] {s['url']}\n"

    # Salva em disco para o dashboard
    try:
        import os
        from datetime import datetime
        base_dir = os.path.dirname(__file__)
        research_dir = os.path.join(base_dir, "research")
        os.makedirs(research_dir, exist_ok=True)
        safe_topic = "".join([c if c.isalnum() else "_" for c in topic])[:30].strip("_")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_topic}.md"
        with open(os.path.join(research_dir, filename), "w", encoding="utf-8") as f:
            f.write(result)
    except Exception as e:
        import logging
        logging.getLogger("deep_research").warning(f"Erro ao salvar pesquisa no disco: {e}")

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fluxo principal (legacy — execução direta sem aprovação)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def research(topic: str, router, progress_cb=None) -> str:
    """
    Execução direta (sem aprovação prévia).
    Mantido para compatibilidade — usado como fallback.
    """
    logger.info(f"🔬 Deep Research (direto): {topic}")

    # Gerar plano
    plan = await create_plan(topic, router)
    logger.info(f"🔬 Plano: {len(plan)} sub-tarefas")

    # Executar
    all_data, sources = await execute_plan(topic, plan, router, progress_cb)

    # Sintetizar
    report = await synthesize_with_citations(topic, all_data, sources, router)
    logger.info(f"🔬 Relatório: {len(report)} chars, {len(sources)} fontes")

    return report

--- END FILE ---

--- FILE: doc_reader.py ---
"""
doc_reader.py — Leitor e analisador de documentos multi-formato
Suporta: PDF, TXT, DOCX, CSV, XLSX
"""

import csv
import io
import logging
import os

logger = logging.getLogger("doc_reader")

# Imports opcionais — falham graciosamente
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    logger.warning("pdfplumber não instalado — PDF desabilitado")

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    logger.warning("python-docx não instalado — DOCX desabilitado")

try:
    from openpyxl import load_workbook
    HAS_XLSX = True
except ImportError:
    HAS_XLSX = False
    logger.warning("openpyxl não instalado — XLSX desabilitado")


SUPPORTED_EXTENSIONS = {
    ".pdf": "PDF",
    ".txt": "Texto",
    ".docx": "Word",
    ".csv": "CSV",
    ".xlsx": "Excel",
    ".md": "Markdown",
    ".json": "JSON",
    ".py": "Python",
    ".js": "JavaScript",
    ".log": "Log",
}


def extract_text(file_path: str) -> str:
    """
    Extrai texto de qualquer formato suportado.
    
    Returns:
        Texto extraído (limitado a 10000 chars pra não estourar LLM context)
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return f"Formato '{ext}' não suportado. Formatos aceitos: {', '.join(SUPPORTED_EXTENSIONS.keys())}"

    try:
        if ext == ".pdf":
            text = _read_pdf(file_path)
        elif ext == ".docx":
            text = _read_docx(file_path)
        elif ext == ".csv":
            text = _read_csv(file_path)
        elif ext == ".xlsx":
            text = _read_xlsx(file_path)
        else:
            # TXT, MD, JSON, PY, JS, LOG — tudo é texto
            text = _read_text(file_path)

        # Limitar tamanho
        if len(text) > 10000:
            text = text[:10000] + f"\n\n[... documento truncado, {len(text)} chars total]"

        logger.info(f"📄 Extraído {len(text)} chars de {os.path.basename(file_path)}")
        return text

    except Exception as e:
        logger.error(f"Erro lendo {file_path}: {e}")
        return f"Erro ao ler arquivo: {str(e)[:200]}"


def _read_pdf(path: str) -> str:
    """Extrai texto de PDF via pdfplumber."""
    if not HAS_PDF:
        return "pdfplumber não está instalado. Rode: pip install pdfplumber"

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(f"--- Página {page_num + 1} ---\n{text}")

    return "\n\n".join(text_parts) if text_parts else "PDF sem texto extraível (pode ser escaneado/imagem)."


def _read_docx(path: str) -> str:
    """Extrai texto de DOCX via python-docx."""
    if not HAS_DOCX:
        return "python-docx não está instalado. Rode: pip install python-docx"

    doc = DocxDocument(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs) if paragraphs else "Documento DOCX vazio."


def _read_csv(path: str) -> str:
    """Lê CSV e formata como tabela legível."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return "CSV vazio."

    # Header + primeiras 50 linhas
    header = rows[0]
    data_rows = rows[1:51]

    lines = [" | ".join(header)]
    lines.append("-" * len(lines[0]))
    for row in data_rows:
        lines.append(" | ".join(row))

    if len(rows) > 51:
        lines.append(f"\n[... {len(rows) - 51} linhas adicionais omitidas]")

    return "\n".join(lines)


def _read_xlsx(path: str) -> str:
    """Lê XLSX e formata como tabela legível."""
    if not HAS_XLSX:
        return "openpyxl não está instalado. Rode: pip install openpyxl"

    wb = load_workbook(path, read_only=True)
    parts = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(max_row=51, values_only=True))

        if not rows:
            continue

        lines = [f"### Planilha: {sheet_name}"]
        for i, row in enumerate(rows):
            cells = [str(c) if c is not None else "" for c in row]
            lines.append(" | ".join(cells))
            if i == 0:
                lines.append("-" * len(lines[-1]))

        total_rows = ws.max_row or 0
        if total_rows > 51:
            lines.append(f"\n[... {total_rows - 51} linhas adicionais omitidas]")

        parts.append("\n".join(lines))

    wb.close()
    return "\n\n".join(parts) if parts else "Planilha vazia."


def _read_text(path: str) -> str:
    """Lê qualquer arquivo de texto."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


async def analyze_document(file_path: str, router, question: str = None) -> str:
    """
    Analisa um documento: extrai texto, pede ao LLM para resumir/analisar.
    
    Args:
        file_path: Caminho do arquivo
        router: LLMRouter
        question: Pergunta específica sobre o documento (opcional)
    """
    text = extract_text(file_path)
    filename = os.path.basename(file_path)

    if text.startswith("Erro") or text.startswith("Formato"):
        return text

    prompt_base = (
        f"Analise este documento ({filename}) e forneça:\n"
        "1. **Resumo** (2-3 parágrafos)\n"
        "2. **Pontos-chave** (lista)\n"
        "3. **Dados importantes** (se houver números/estatísticas)\n"
        "4. **Observações** (algo notável ou que merece atenção)\n\n"
        "Seja factual e cite trechos específicos quando relevante."
    )

    if question:
        prompt_base = (
            f"O Criador enviou o documento '{filename}' e perguntou: {question}\n\n"
            "Responda a pergunta com base no conteúdo do documento. "
            "Se a resposta não estiver no documento, diga isso."
        )

    result = await router.generate([
        {"role": "system", "content": prompt_base},
        {"role": "user", "content": f"Conteúdo do documento:\n\n{text}"},
    ], temperature=0.1)

    return result if isinstance(result, str) else "Erro na análise do documento."

--- END FILE ---

--- FILE: web_search.py ---
"""
web_search.py — Cascata de busca web (DDG → Brave → Jina Reader)
Economiza cotas usando fontes gratuitas primeiro.
"""

import aiohttp
import logging
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

import config

logger = logging.getLogger("web_search")


async def web_search(query: str, max_results: int = None) -> str:
    """
    Busca na web usando cascata:
    1. Jina Search (s.jina.ai — grátis, resultados formatados)
    2. DuckDuckGo (grátis, fallback)
    3. Brave Search (2000/mês) — último recurso
    
    Returns:
        Texto formatado com os resultados da busca.
    """
    if max_results is None:
        max_results = config.DDG_MAX_RESULTS

    # Tenta Jina Search primeiro (melhor formatação)
    jina_result = await _search_jina(query)
    if jina_result and len(jina_result) > 100:
        logger.info(f"🔍 Jina retornou {len(jina_result)} chars para: {query[:50]}")
        return jina_result

    # Tenta DuckDuckGo (grátis)
    results = _search_ddg(query, max_results)
    if results:
        logger.info(f"🔍 DDG retornou {len(results)} resultados para: {query[:50]}")
        return _format_results(results, source="DuckDuckGo")

    # Se DDG falhou e Brave está configurado, tenta Brave
    if config.BRAVE_API_KEY:
        results = await _search_brave(query, max_results)
        if results:
            logger.info(f"🦁 Brave retornou {len(results)} resultados para: {query[:50]}")
            return _format_results(results, source="Brave")

    return "Nenhum resultado encontrado na busca web."


async def web_search_deep(query: str, max_results: int = None) -> str:
    """
    Busca multi-turn: pesquisa → lê o melhor resultado → retorna tudo.
    1. Jina Search (já retorna conteúdo rico, não precisa deep-read)
    2. DDG/Brave → pega snippets + lê a URL do top resultado via Jina Reader
    """
    if max_results is None:
        max_results = config.DDG_MAX_RESULTS

    # Jina Search já retorna conteúdo rico
    jina_result = await _search_jina(query)
    if jina_result and len(jina_result) > 100:
        logger.info(f"🔍 Jina retornou {len(jina_result)} chars (deep não necessário)")
        return jina_result

    # DDG → snippets + deep-read do top resultado
    results = _search_ddg(query, max_results)
    if results:
        snippets = _format_results(results, source="DuckDuckGo")
        # Ler o conteúdo completo do primeiro resultado
        top_url = results[0].get("url", "")
        if top_url:
            logger.info(f"📖 Deep-read do top resultado: {top_url[:60]}")
            full_content = await web_read(top_url)
            if full_content and not full_content.startswith("❌"):
                return f"{snippets}\n\n---\n\n## Conteúdo completo do melhor resultado ({top_url}):\n{full_content}"
        return snippets

    # Brave fallback
    if config.BRAVE_API_KEY:
        results = await _search_brave(query, max_results)
        if results:
            snippets = _format_results(results, source="Brave")
            top_url = results[0].get("url", "")
            if top_url:
                full_content = await web_read(top_url)
                if full_content and not full_content.startswith("❌"):
                    return f"{snippets}\n\n---\n\n## Conteúdo completo ({top_url}):\n{full_content}"
            return snippets

    return "Nenhum resultado encontrado na busca web."


async def _search_jina(query: str) -> str:
    """Busca via Jina Search (s.jina.ai) — retorna texto formatado direto."""
    try:
        url = f"https://s.jina.ai/{query}"
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "KittyBot/2.0", "Accept": "text/plain"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    if len(content) > 4000:
                        content = content[:4000] + "\n[...truncado...]"
                    return content
                return ""
    except Exception as e:
        logger.warning(f"⚠️ Jina Search falhou: {e}")
        return ""


def _search_ddg(query: str, max_results: int) -> list[dict]:
    """Busca no DuckDuckGo (síncrona mas instantânea)."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"⚠️ DDG falhou: {e}")
        return []


async def _search_brave(query: str, max_results: int) -> list[dict]:
    """Busca na API Brave Search (2000 req/mês grátis)."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": config.BRAVE_API_KEY,
            }
            params = {"q": query, "count": max_results}

            async with session.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Brave retornou status {resp.status}")
                    return []

                data = await resp.json()
                web_results = data.get("web", {}).get("results", [])

                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("description", ""),
                    }
                    for r in web_results
                ]
    except Exception as e:
        logger.warning(f"⚠️ Brave falhou: {e}")
        return []


async def web_read(url: str) -> str:
    """
    Lê o conteúdo de uma URL via Jina Reader.
    Converte HTML em Markdown limpo para o LLM.
    """
    try:
        jina_url = f"{config.JINA_API_URL}{url}"
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "text/markdown"}
            async with session.get(jina_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    # Limita tamanho para não estourar contexto
                    if len(content) > 8000:
                        content = content[:8000] + "\n\n[...conteúdo truncado por tamanho...]"
                    logger.info(f"📖 Jina leu {len(content)} chars de: {url[:60]}")
                    return content
                else:
                    return f"❌ Erro ao ler URL: status {resp.status}"
    except Exception as e:
        return f"❌ Erro ao ler URL: {e}"


def _format_results(results: list[dict], source: str) -> str:
    """Formata resultados de busca em texto limpo."""
    lines = [f"🔍 Resultados de busca ({source}):\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   {r['url']}")
        lines.append(f"   {r['snippet']}")
        lines.append("")
    return "\n".join(lines)

--- END FILE ---
