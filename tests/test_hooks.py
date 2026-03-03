import pytest
from hooks import before_shell_execution, before_submit_prompt

@pytest.mark.asyncio
async def test_before_shell_execution_blocked():
    # Testa comandos maliciosos mapeados no tuple do hooks
    assert await before_shell_execution("rm -rf /") is False
    assert await before_shell_execution("dd if=/dev/zero of=/dev/sda") is False
    assert await before_shell_execution("poweroff") is False

@pytest.mark.asyncio
async def test_before_shell_execution_allowed():
    # Testa comandos do dia a dia
    assert await before_shell_execution("ls -la") is True
    assert await before_shell_execution("cat script.py") is True
    assert await before_shell_execution("echo 'Hello World'") is True

@pytest.mark.asyncio
async def test_before_submit_prompt_redacts_credentials():
    # As chaves listadas em hooks usam regex que pega 'sk-' seguido de num/chars
    # ex: sk-abc123def456ghi789jkl012mno345pqr678stu901
    
    dirty_prompt = "Oi Iara, minha chave é sk-abc123def456ghi789jkl012mno345pqr678stu901"
    clean_prompt = await before_submit_prompt(dirty_prompt)
    
    assert "sk-" not in clean_prompt
    assert "[REDACTED_CREDENTIAL]" in clean_prompt

@pytest.mark.asyncio
async def test_before_submit_prompt_clean():
    normal_prompt = "texto normal sem chave e sem nada de errado"
    clean_prompt = await before_submit_prompt(normal_prompt)
    assert clean_prompt == normal_prompt
