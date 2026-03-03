import pytest
import pytest_asyncio
from datetime import datetime
import core
import config

@pytest_asyncio.fixture(autouse=True)
async def isolated_db(tmp_path, monkeypatch):
    """Garante que todos os testes rodem em um SQLite limpo e descartável."""
    test_db = tmp_path / "test_kitty_memory.db"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    
    # Roda init_db obrigatoriamente
    await core.init_db()
    yield

@pytest.mark.asyncio
async def test_init_db():
    # Se o fixture rodou, o banco já existe e as tabelas devem estar lá
    # Criar um projeto de teste pra provar que writes funcionam
    pid = await core.get_or_create_project("test")
    assert pid > 0

@pytest.mark.asyncio
async def test_save_and_get_conversation():
    await core.save_message("user", "Global MSG1")
    await core.save_message("assistant", "Global MSG2")
    
    pid = await core.get_or_create_project("proj1")
    await core.save_message("user", "Project MSG1", project_id=pid)
    
    # Testar recuperar apenas a global
    global_conv = await core.get_conversation()
    assert len(global_conv) == 2
    assert global_conv[0]["content"] == "Global MSG1"
    
    # Testar recuperar projeto
    proj_conv = await core.get_conversation(project_id=pid)
    assert len(proj_conv) == 3 # Pega as 2 globais + 1 do projeto

@pytest.mark.asyncio
async def test_get_or_create_project():
    pid1 = await core.get_or_create_project("XPTO")
    pid2 = await core.get_or_create_project("XPTO")
    assert pid1 == pid2 # Deve ser idem

@pytest.mark.asyncio
async def test_save_episode_and_get_recent():
    await core.save_episode("Episodio global", "global")
    pid = await core.get_or_create_project("P2")
    await core.save_episode("Episodio P2", "p2", project_id=pid)
    
    # mock get_all_episodes to test this logic
    # getting all global episodes:
    global_eps = await core.get_all_episodes(project_id=None)
    assert len(global_eps) == 1
    assert "global" in global_eps[0]
    
    # p2 episodes
    p2_eps = await core.get_all_episodes(project_id=pid)
    assert len(p2_eps) == 2 # 1 global + 1 proj

@pytest.mark.asyncio
async def test_core_memory_confidence():
    # Salvar fatos com confiança diferente
    await core.save_core_fact("pref", "gosta de teste")
    text = await core.get_core_memory_text()
    assert "gosta de teste" in text

@pytest.mark.asyncio
async def test_scheduled_jobs_crud():
    jid = await core.add_scheduled_job("test_job", "10:00", "test_action", {"a": 1}, enabled=False)
    
    jobs = await core.get_all_scheduled_jobs()
    assert len(jobs) == 1
    assert jobs[0]["name"] == "test_job"
    assert jobs[0]["enabled"] is False
    assert jobs[0]["params"] == {"a": 1}
    
    # Toggle
    new_state = await core.toggle_job("test_job")
    assert new_state is True
    
    # Update last run
    await core.update_job_last_run(jobs[0]["id"])
    jobs_after = await core.get_all_scheduled_jobs()
    assert jobs_after[0]["last_run"] is not None
    
    # Delete
    deleted = await core.delete_scheduled_job("test_job")
    assert deleted is True
    assert len(await core.get_all_scheduled_jobs()) == 0

@pytest.mark.asyncio
async def test_get_all_tasks():
    await core.add_task_state("Task Pendente")
    tid = await core.add_task_state("Task Em Progresso")
    await core.set_task_status(tid, "in_progress")
    
    tasks = await core._get_all_tasks()
    assert len(tasks) == 2
    statuses = [t["status"] for t in tasks]
    assert "pending" in statuses
    assert "in_progress" in statuses
