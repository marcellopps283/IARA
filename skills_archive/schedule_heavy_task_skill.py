from core import DB_NAME
import aiosqlite
import json

"""
Skill: schedule_heavy_task
Description: Módulo do Cloud Bursting. Permite agendar tarefas demoradas (ex: processamento de horas de áudio/vídeo) para serem resolvidas pelo nó pesado (Google Colab) via Google Drive/Queue.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "schedule_heavy_task",
            "description": "Schedule a heavy task (e.g., video rendering, data science) to the Cloud Bursting queue (Google Colab).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "Type of task (e.g., 'transcription', 'video_render')."
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of what the Cloud Worker should do."
                    },
                    "file_references": {
                        "type": "string",
                        "description": "Links or paths to heavy files to be processed."
                    }
                },
                "required": ["task_type", "description"]
            }
        }
    }

async def execute(kwargs):
    task_type = kwargs.get("task_type")
    description = kwargs.get("description")
    file_references = kwargs.get("file_references", "N/A")
    
    if not task_type or not description:
        return "Erro: task_type e description são obrigatórios."
        
    payload = json.dumps({
        "description": description,
        "file_references": file_references
    })
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO task_queue (task_type, payload, status) VALUES (?, ?, 'PENDENTE')",
                (task_type, payload)
            )
            await db.commit()
            
        return f"Sucesso! Tarefa pesada '{task_type}' agendada na Fila (Queue) com status [PENDENTE]. Ela será processada na próxima janela de nuvem."
    except Exception as e:
        return f"Falha ao agendar tarefa pesada no Cloud Bursting: {e}"
