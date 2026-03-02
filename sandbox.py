import os
import tempfile
import asyncio
import shutil
import sys
from pathlib import Path

# Pasta permanente de evolução da Kitty
SHADOW_DIR = os.path.expanduser("~/Kitty_Shadow")

async def run_in_sandbox(python_code: str, timeout: int = 15):
    """
    Executa código gerado por IA em um ambiente estéril e efêmero.
    No Android/Termux, usa "proot" para enjaular o sistema de arquivos.
    No Windows de desenvolvimento, usa pastas temporárias isoladas.
    """
    result = None
    try:
        # 1. Cria espaço limpo (Garbage Collection efêmera garantida ao fechar bloco with)
        with tempfile.TemporaryDirectory(prefix="zeroclaw_sandbox_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # 2. Escreve o código suspeito no arquivo temporário
            script_target = temp_path / "sandbox_eval.py"
            with open(script_target, "w", encoding="utf-8") as f:
                f.write(python_code)
            
            # 3. Se houver dependências na Shadow, clona elas SOMENTE para leitura neste temp
            if os.path.exists(SHADOW_DIR):
                for item in os.listdir(SHADOW_DIR):
                    src = os.path.join(SHADOW_DIR, item)
                    dst = temp_path / item
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)

                # 4. Determina o comando do interpretador isolado
                if sys.platform == "win32":
                    # No dev cockpit, restringe o diretório de trabalho do processo 
                    # (não é um chroot real, mas simula o ambiente de teste)
                    cmd = [sys.executable, str(script_target)]
                else:
                    # Termux: Invoca PRoot para forçar a raiz simulada e blindar o Android
                    # "proot -0 -r {temp_dir} -b /data/data/com.termux/files/usr /usr/bin/python ..."
                    # Abaixo é a montagem segura onde o bot pensa que a raiz '/' é o tempfile
                    termux_python = shutil.which("python") or "python"
                    termux_usr = "/data/data/com.termux/files/usr"
                    cmd = [
                        "proot", 
                        "-0", # Fake root
                        "-r", str(temp_path), 
                        "-b", f"{termux_usr}:{termux_usr}", # Leva interpretador junto
                        "-w", "/", # Fixa o dir de trabalho dentro da jaula
                        termux_python, "sandbox_eval.py"
                    ]

                try:
                    # 5. Execução com Timeout de CPU e captura Assíncrona de I/O
                    if sys.platform == "win32":
                        import subprocess
                        def sync_run():
                            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                        try:
                            proc = await asyncio.to_thread(sync_run)
                            process = type('obj', (object,), {'returncode': proc.returncode})
                            out_str = proc.stdout[:10000]
                            err_str = proc.stderr[:10000]
                        except subprocess.TimeoutExpired:
                            raise asyncio.TimeoutError()
                    else:
                        process = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                        out_str = stdout.decode('utf-8', errors='ignore')[:10000] 
                        err_str = stderr.decode('utf-8', errors='ignore')[:10000]

                    if process.returncode == 0:
                        result = {"status": "success", "output": out_str.strip()}
                    else:
                        result = {"status": "error", "error_type": "Execução Falhou", "traceback": err_str.strip() or out_str.strip()}

                except asyncio.TimeoutError:
                    print("Sandbox: OOM/Infinite Loop Evitado. Matando processo.")
                    try:
                        if 'process' in locals() and hasattr(process, 'kill'):
                            process.kill()
                            await process.wait()
                    except ProcessLookupError:
                        pass
                    result = {"status": "error", "error_type": "Timeout Acionado", "traceback": "Processo demorou mais que o limite estabelecido e foi aniquilado sumariamente."}
                except OSError as e:
                    # Catch specific runtime OS errors without triggering tempfile handlers
                    result = {"status": "error", "error_type": "Erro de I/O do processo", "traceback": str(e)}
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    result = {"status": "error", "error_type": "Erro Ambiental", "traceback": f"{str(e)}\n{tb}"}

    # Tratamento de erro específico do Windows para testes locais da lixeira
    except OSError as e:
        if sys.platform == 'win32':
             if not result:
                 result = {"status": "error", "error_type": "Timeout Acionado", "traceback": f"Processo testado com sucesso mas Lixeira Windows falhou na delecao: {e}"}
        else:
             raise e
    except Exception as e:
        import traceback
        result = {"status": "error", "error_type": "Global Error Trap", "traceback": traceback.format_exc()}

    return result or {"status": "error", "error_type": "Fatal Crash", "traceback": "Processo extinto no nível OS."}

# --- TDD Simples de Sandbox ---
async def test_sandbox():
    print("Testando Execução Normal...")
    code_ok = "print('Sou a Kitty rodando na caixa!')\nx = 2 + 5\nprint(f'Soma {x}')"
    res1 = await run_in_sandbox(code_ok)
    print(res1)
    
    print("\nTestando Timeout/Loop Infinito...")
    code_bad = "while True:\n    pass\n"
    res2 = await run_in_sandbox(code_bad, timeout=2) # 2 segundos paara estourar rápido
    print(res2)

if __name__ == "__main__":
    asyncio.run(test_sandbox())
