import os
import json
import asyncio
import aiosqlite
from core import DB_NAME

SYNC_DIR = os.path.expanduser("~/Kitty_Shadow/DriveSync")
PENDING_FILE = os.path.join(SYNC_DIR, "pending_tasks.json")
RESULTS_DIR = os.path.join(SYNC_DIR, "results")

# Certifica que os diretórios existem
os.makedirs(RESULTS_DIR, exist_ok=True)

async def export_pending_tasks():
    """Lê tarefas pendentes no banco e exporta para o arquivo de sincronização"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, task_type, payload FROM task_queue WHERE status = 'PENDENTE'") as cursor:
            tasks = await cursor.fetchall()
            
    if not tasks:
        return 0
        
    tasks_list = []
    for t_id, t_type, payload in tasks:
        try:
            payload_data = json.loads(payload)
        except:
            payload_data = {"raw": payload}
            
        tasks_list.append({
            "task_id": t_id,
            "task_type": t_type,
            "payload": payload_data
        })
        
    try:
        # A escrita é feita via threadpool para não travar o event loop
        def _write_json():
            with open(PENDING_FILE, "w", encoding="utf-8") as f:
                json.dump(tasks_list, f, indent=4, ensure_ascii=False)
                
        await asyncio.to_thread(_write_json)
        return len(tasks_list)
    except Exception as e:
        print(f"Erro ao exportar fila de tarefas: {e}")
        return 0

async def process_completed_tasks(bot, user_id):
    """
    Verifica se existem resultados retornados pelo Colab na pasta /results.
    Avisa o usuário final via Telegram.
    """
    try:
        files = os.listdir(RESULTS_DIR)
        completed_count = 0
        
        for file in files:
            if file.endswith(".json"):
                filepath = os.path.join(RESULTS_DIR, file)
                
                with open(filepath, "r", encoding="utf-8") as f:
                    result_data = json.load(f)
                    
                task_id = result_data.get("task_id")
                final_output = result_data.get("final_output", "Concluído sem mensagem de saída.")
                
                if task_id:
                    # Atualiza o banco de PENDENTE para CONCLUIDO
                    async with aiosqlite.connect(DB_NAME) as db:
                        await db.execute("UPDATE task_queue SET status = 'CONCLUIDO' WHERE id = ?", (task_id,))
                        await db.commit()
                        
                    # Alerta o usuário (Proactive Agent / Heartbeat)
                    if user_id != 0 and bot:
                        msg = f"☁️ **Cloud Bursting Finalizado!**\nSua tarefa pesada ID #{task_id} retornou da nuvem.\n\n📄 **Resultado:**\n{final_output}"
                        await bot.send_message(user_id, msg, parse_mode="Markdown")
                        
                    # Remove o arquivo processado
                    os.remove(filepath)
                    completed_count += 1
                    
        return completed_count
    except Exception as e:
        print(f"Erro ao processar resultados do Colab: {e}")
        return 0

async def run_sync_cycle(bot, user_id):
    """Encapsula a ação completa a ser chamada pelo Heartbeat"""
    exported = await export_pending_tasks()
    imported = await process_completed_tasks(bot, user_id)
    if exported > 0 or imported > 0:
        print(f"☁️ [Cloud Sync] Exportadas {exported} pendências | Importados {imported} resultados.")
