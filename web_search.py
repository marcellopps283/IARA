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
