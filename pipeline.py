"""
pipeline.py — Cascata de 5 Estágios Sequenciais da IARA v2
Implementa o workflow estruturado para tarefas complexas:
1. RESEARCH
2. PLAN
3. IMPLEMENT
4. REVIEW
5. VERIFY
"""

import asyncio
import logging
from typing import Callable, Awaitable
from pathlib import Path

import config
import deep_research
import telegram_bot
from llm_router import LLMRouter

logger = logging.getLogger("pipeline")

class PipelineManager:
    """Gerencia a execução da cascata de 5 fases."""
    
    def __init__(self, chat_id: int, router: LLMRouter):
        self.chat_id = chat_id
        self.router = router
        
        # Pasta temporária para os artefatos do pipeline
        self.tmp_dir = Path("/tmp/iara_pipeline")
        self.tmp_dir.mkdir(exist_ok=True, parents=True)

    async def _send_analysis(self, msg: str):
        """Log do pensamento invisível."""
        await telegram_bot.send_channel_message(self.chat_id, msg, channel="analysis")

    async def _send_commentary(self, msg: str):
        """Update de status da UI."""
        await telegram_bot.send_channel_message(self.chat_id, msg, channel="commentary")

    async def run_stage_research(self, topic: str) -> str:
        """Fase 1: Coleta dados abertos."""
        await self._send_commentary(f"🔎 Fase 1/5: INICIANDO RESEARCH\nTopico: {topic}")
        
        # Realiza pesquisa profunda (Deep Research)
        plan = await deep_research.create_plan(topic, self.router)
        
        async def mock_progress(msg: str):
            await self._send_analysis(f"[RESEARCH] {msg}")

        all_data, sources = await deep_research.execute_plan(topic, plan, self.router, mock_progress)
        report = await deep_research.synthesize_with_citations(
            topic, all_data, sources, self.router, tipo="Arquitetural"
        )
        
        # Salva o arquivo em tmp
        out_path = self.tmp_dir / "research-summary.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
            
        await self._send_analysis(f"Research summary salvo em {out_path}")
        return report

    async def run_stage_plan(self, topic: str, research_data: str) -> str:
        """Fase 2: Council delibera e gera plano."""
        await self._send_commentary("🧠 Fase 2/5: INICIANDO PLAN (Council Deliberation)")
        
        prompt = [
            {"role": "system", "content": "Você é o Conselho de Arquitetura. Baseado na pesquisa, gere um plan.md técnico e estruturado com os componentes a serem criados/modificados. RETORNE APENAS O MARKDOWN."},
            {"role": "user", "content": f"Tópico: {topic}\n\nPesquisa:\n{research_data}"}
        ]
        
        # Usa o DeepSeek R1 (reasoning) ou equivalente pesado
        plan_content = await self.router.generate(prompt, task_type="plan")
        if not isinstance(plan_content, str):
            plan_content = str(plan_content)
            
        out_path = self.tmp_dir / "plan.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(plan_content)
            
        await self._send_analysis(f"Plan Draft salvo em {out_path}")
        return plan_content

    async def run_stage_implement(self, plan: str) -> str:
        """Fase 3: Executa sequencial ou via ferramentas."""
        await self._send_commentary("🏗️ Fase 3/5: IMPLEMENTAÇÃO (Bloqueado por aprovação)")
        # Na prática, esta fase precisa de integração com tools de edição de arquivo (ex: python_user_visible)
        # Por enquanto, retornamos um stub indicando dependência da aprovação formal (Plan Mode Lock)
        return "Implementação pausada aguardando ExitPlanMode do Usuário."

    async def run_stage_review(self, implementation_result: str) -> str:
        """Fase 4: Code Reviewer, Security Reviewer e Auditor (Blue/Red Team)."""
        await self._send_commentary("🛡️ Fase 4/5: REVIEW (Auditoria Ativa)")
        
        prompt = [
            {"role": "system", "content": "Você é o Security Reviewer / Auditor (Red Team). Revise as mudanças acima em busca de falhas lógicas, credenciais vazadas e OOM risks. Retorne um relatório crítico (review-comments.md)."},
            {"role": "user", "content": f"Implementação:\n{implementation_result}"}
        ]
        
        review = await self.router.generate(prompt, task_type="reasoning")
        review = str(review)
        
        out_path = self.tmp_dir / "review-comments.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(review)
            
        return review

    async def run_stage_verify(self, review: str) -> str:
        """Fase 5: Confirmação e encerramento (CI Resolve)."""
        await self._send_commentary("🏁 Fase 5/5: VERIFY (Finalização)")
        
        prompt = [
            {"role": "system", "content": "Avalie o relatório de review e diga se a tarefa está aprovada para deploy final (YES/NO). Dê um veredito curto."},
            {"role": "user", "content": f"Review:\n{review}"}
        ]
        
        verdict = await self.router.generate(prompt, task_type="chat_fast")
        return str(verdict)

    async def execute_full_pipeline(self, topic: str):
        """Orquestra o pipeline completo de ponta a ponta."""
        try:
            # Stage 1
            research_data = await self.run_stage_research(topic)
            
            # Stage 2
            plan_data = await self.run_stage_plan(topic, research_data)
            await telegram_bot.send_channel_message(self.chat_id, f"📝 **PLANO ARQUITETURAL GERADO:**\n\n{plan_data[:3000]}...", channel="final")
            await telegram_bot.send_channel_message(self.chat_id, "Use `/plan off` para aprovar o plano e prosseguir para a Fase 3 (Implement).", channel="commentary")
            
            # (Aqui o loop será interrompido na vida real aguardando o usuário descer o lock)
            
        except Exception as e:
            logger.error(f"Erro catastrófico no pipeline: {e}")
            await self._send_commentary(f"🚨 Falha no pipeline: {str(e)[:100]}")
