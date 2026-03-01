"""
llm_router.py — Roteador multi-LLM com fallback automático
Usa aiohttp com a API REST compatível com OpenAI (sem SDK compilado).
Compatível com Termux/Android (sem jiter/C extensions).
"""

import asyncio
import json
import logging
import random
from typing import AsyncGenerator

import aiohttp

import config

logger = logging.getLogger("llm_router")

# Limita requisições LLM simultâneas (evita bans por HTTP 429 Timeouts)
_api_semaphore = asyncio.Semaphore(3)


class LLMRouter:
    """
    Gerencia múltiplos provedores de LLM com fallback automático.
    
    Tenta o provedor primário (Groq). Se falhar (rate limit, timeout, erro),
    automaticamente tenta o próximo da lista. Suporta streaming.
    """

    def __init__(self):
        self.providers = []
        self._init_providers()
        self.current_provider = None

    def _init_providers(self):
        """Inicializa providers apenas com API key configurada."""
        for provider in config.LLM_PROVIDERS:
            if not provider["api_key"]:
                logger.info(f"⏭️ Provider '{provider['name']}' sem API key, pulando.")
                continue
            self.providers.append(provider)
            logger.info(f"✅ Provider '{provider['name']}' ({provider['model']}) configurado.")

        if not self.providers:
            raise RuntimeError("❌ Nenhum provider de LLM configurado! Verifique o .env")

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> str | dict:
        """
        Gera uma resposta usando o primeiro provider disponível.
        Se falhar, faz fallback para o próximo.
        
        Returns:
            Texto da resposta OU dict com tool_calls.
        """
        last_error = None

        for provider in self.providers:
            try:
                logger.info(f"🧠 Tentando: {provider['name']} ({provider['model']})")
                self.current_provider = provider["name"]

                body = {
                    "model": provider["model"],
                    "messages": messages,
                    "max_tokens": provider["max_tokens"],
                    "temperature": temperature,
                    "stream": False,
                }

                if tools and provider.get("supports_tools"):
                    body["tools"] = tools
                    body["tool_choice"] = "auto"

                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                }

                url = f"{provider['base_url']}/chat/completions"
                timeout = aiohttp.ClientTimeout(total=config.LLM_TIMEOUT_SECONDS)

                max_retries = 3
                for attempt in range(max_retries):
                    async with _api_semaphore:
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(url, headers=headers, json=body) as resp:
                                if resp.status == 429:
                                    wait_time = (2 ** attempt) + random.uniform(0.1, 1.5)
                                    logger.warning(f"⚠️ {provider['name']}: Rate limit (429). Retry {attempt+1}/{max_retries} in {wait_time:.1f}s")
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(wait_time)
                                        continue
                                    else:
                                        break # Vai pro fallback (próximo provider)
                                        
                                if resp.status != 200:
                                    error_text = await resp.text()
                                    logger.warning(f"⚠️ {provider['name']}: HTTP {resp.status} - {error_text[:200]}")
                                    break # Erros normais não dão retry, fazemos fallback

                                data = await resp.json()

                                choice = data["choices"][0]
                                message = choice["message"]

                                # Se o modelo quer chamar tools
                                if choice.get("finish_reason") == "tool_calls" or message.get("tool_calls"):
                                    return message  # Retorna o dict completo

                                return message.get("content", "")

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ {provider['name']}: Timeout ({config.LLM_TIMEOUT_SECONDS}s)")
                last_error = f"Timeout em {provider['name']}"
                continue
            except Exception as e:
                logger.warning(f"⚠️ {provider['name']} falhou: {str(e)[:200]}")
                last_error = str(e)
                continue

        raise RuntimeError(f"❌ Todos os providers falharam. Último: {last_error}")

    async def generate_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Gera resposta em streaming (token por token via SSE).
        Faz fallback automático se o provider falhar.
        """
        last_error = None

        for provider in self.providers:
            if not provider.get("supports_streaming"):
                continue

            try:
                logger.info(f"🌊 Streaming via: {provider['name']} ({provider['model']})")
                self.current_provider = provider["name"]

                body = {
                    "model": provider["model"],
                    "messages": messages,
                    "max_tokens": provider["max_tokens"],
                    "temperature": temperature,
                    "stream": True,
                }

                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                }

                url = f"{provider['base_url']}/chat/completions"
                timeout = aiohttp.ClientTimeout(total=config.LLM_TIMEOUT_SECONDS)

                max_retries = 3
                for attempt in range(max_retries):
                    async with _api_semaphore:
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(url, headers=headers, json=body) as resp:
                                if resp.status == 429:
                                    wait_time = (2 ** attempt) + random.uniform(0.1, 1.5)
                                    logger.warning(f"⚠️ Streaming {provider['name']}: Rate limit (429). Retry {attempt+1}/{max_retries} in {wait_time:.1f}s")
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(wait_time)
                                        continue
                                    else:
                                        break # Vai pro fallback

                                if resp.status != 200:
                                    error_text = await resp.text()
                                    logger.warning(f"⚠️ Streaming {provider['name']}: HTTP {resp.status}")
                                    last_error = error_text[:200]
                                    break

                                # Parse SSE stream
                                async for line in resp.content:
                                    line = line.decode("utf-8").strip()
                                    if not line or not line.startswith("data: "):
                                        continue
                                    
                                    data_str = line[6:]  # Remove "data: "
                                    if data_str == "[DONE]":
                                        return

                                    try:
                                        data = json.loads(data_str)
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                    except (json.JSONDecodeError, KeyError, IndexError):
                                        continue

                return  # Stream completou

            except Exception as e:
                logger.warning(f"⚠️ Streaming '{provider['name']}' falhou: {str(e)[:200]}")
                last_error = str(e)
                continue

        # Se streaming falhou, tenta sem stream
        logger.warning("⚠️ Streaming falhou em todos, tentando sem stream...")
        try:
            result = await self.generate(messages, temperature=temperature)
            if isinstance(result, str):
                yield result
        except Exception as e:
            yield f"😿 Desculpa Criador, todos os meus cérebros falharam. Erro: {str(e)[:100]}"

    def get_status(self) -> dict:
        """Retorna status dos providers configurados."""
        return {
            "providers_ativos": [p["name"] for p in self.providers],
            "provider_atual": self.current_provider,
            "total_providers": len(self.providers),
        }
