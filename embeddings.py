import os
import json
import logging
import numpy as np
import config
from typing import List, Optional

try:
    import cohere
except ImportError:
    cohere = None

logger = logging.getLogger("embeddings")

_cohere_client = None

def get_client():
    global _cohere_client
    if _cohere_client is None and cohere is not None:
        api_key = config.COHERE_API_KEY
        if api_key:
            _cohere_client = cohere.Client(api_key=api_key)
        else:
            logger.warning("COHERE_API_KEY não configurada no config.py")
    return _cohere_client

async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Gera embedding para um texto usando Cohere assincronamente.
    (Cohere SDK Client oficial é síncrono, então pode rodar rápido ou usar async se a SDK permitir).
    No python, o .embed é blocking se não for AsyncClient.
    Para não bloquear, usaremos cohere.AsyncClient se disponível, senão devolve None.
    """
    api_key = config.COHERE_API_KEY
    if not api_key:
        return None
        
    try:
        # Tentar usar cliente assíncrono para não travar o loop do bot
        async_client = cohere.AsyncClient(api_key=api_key)
        response = await async_client.embed(
            texts=[text],
            model="embed-multilingual-v3.0",
            input_type="search_document"
        )
        await async_client.close()
        
        # O Cohere retorna embeddings. Dependendo da versão, está em .embeddings
        embeds = response.embeddings
        if embeds and len(embeds) > 0:
            return embeds[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao gerar embedding: {e}")
        return None

async def generate_query_embedding(text: str) -> Optional[List[float]]:
    """Gera o embedding para a query do usuário (search_query)."""
    api_key = config.COHERE_API_KEY
    if not api_key:
        return None
        
    try:
        async_client = cohere.AsyncClient(api_key=api_key)
        response = await async_client.embed(
            texts=[text],
            model="embed-multilingual-v3.0",
            input_type="search_query"
        )
        await async_client.close()
        embeds = response.embeddings
        if embeds and len(embeds) > 0:
            return embeds[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao gerar embedding de query: {e}")
        return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calcula a similaridade de cosseno entre dois vetores Python (transformados em numpy arrays)"""
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

def serialize_embedding(embedding: List[float]) -> bytes:
    """Converte a lista de floats para um BLOB (JSON format em bytes) para salvar no SQLite."""
    return json.dumps(embedding).encode('utf-8')

def deserialize_embedding(blob: bytes) -> Optional[List[float]]:
    """Reverte o BLOB (bytes JSON) do SQLite para uma lista de floats."""
    if not blob:
        return None
    try:
        return json.loads(blob.decode('utf-8'))
    except Exception as e:
        logger.error(f"Erro ao desserializar embedding: {e}")
        return None
