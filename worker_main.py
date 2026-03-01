import asyncio
import os
import sys
import json
import threading
import http.server
import socketserver
from transport import TransportServer
from sandbox import run_in_sandbox

async def worker_handler(payload):
    """Callback que é acionado pelo TransportServer quando o Cérebro envia uma ordem"""
    print(f"📦 [ZeroMQ] Payload Recebido do Orquestrador: {payload.get('type')}")
    
    # Avalia se é uma chamada de Delegate Shadow (A2A code execution)
    if payload.get("type") == "execute_code":
        code = payload.get("code")
        language = payload.get("language")
        print(f"🧪 Executando código {language} em ambiente estéril (Sandbox)...")
        
        if language == "python":
            result = await run_in_sandbox(code)
            return result
        else:
            return {"status": "error", "error_type": "Unsupported Language", "traceback": "Somente python suportado no Worker Base por enquanto."}
            
    # --- PHASE 3: S21 FE HEAVY WORKER (Smolagents) ---
    if payload.get("type") == "delegate_objective":
        objective = payload.get("objective")
        print(f"🤖 [CodeAgent] Objetivo recebido: {objective}")
        try:
            from smolagents import CodeAgent, DuckDuckGoSearchTool, HfApiModel
            
            # Usando uma LLM gratuita da HF Inference API para o Worker pensar sozinho
            model = HfApiModel(model_id="Qwen/Qwen2.5-Coder-32B-Instruct")
            agent = CodeAgent(tools=[DuckDuckGoSearchTool()], model=model)
            
            def _run_agent():
                return agent.run(objective)
                
            res = await asyncio.to_thread(_run_agent)
            return {"status": "success", "agent_output": str(res)}
        except Exception as e:
            return {"status": "error", "error_type": "Agent Crash", "traceback": str(e)}

    if payload.get("type") == "composio_execute_action":
        action_name = payload.get("action_name")
        params_str = payload.get("action_params", "{}")
        
        try:
            params = json.loads(params_str)
        except:
            params = {}
            
        print(f"🔗 [Composio] Executando action local no S21 FE: {action_name}")
        try:
            from composio import ComposioToolSet, Action
            api_key = os.getenv("COMPOSIO_API_KEY")
            if not api_key:
                return {"status": "error", "error_type": "Missing API Key", "traceback": "COMPOSIO_API_KEY não configurada no .env do S21 FE."}
            
            toolset = ComposioToolSet(api_key=api_key)
            action_enum = getattr(Action, action_name, action_name)
            
            def _run_composio():
                return toolset.execute_action(action=action_enum, params=params)
                
            res = await asyncio.to_thread(_run_composio)
            return {"status": "success", "composio_output": res}
        except Exception as e:
            return {"status": "error", "error_type": "Composio Crash", "traceback": str(e)}

    if payload.get("type") == "call_mcp_tool":
        server_cmd = payload.get("server_command")
        server_args = payload.get("server_args", [])
        tool_name = payload.get("tool_name")
        tool_args = payload.get("tool_args", {})
        
        print(f"🔌 [MCP] Iniciando servidor '{server_cmd}' no S21 FE e chamando '{tool_name}'...")
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            server_params = StdioServerParameters(command=server_cmd, args=server_args, env=None)
            
            async def _run_mcp():
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await session.call_tool(tool_name, arguments=tool_args)
            
            res = await _run_mcp()
            return {"status": "success", "mcp_output": str(res)}
        except Exception as e:
            return {"status": "error", "error_type": "MCP Crash", "traceback": str(e)}

    # --- PHASE 3: MOTO G4 LIGHT WORKER (Web Server) ---
    if payload.get("type") == "host_dashboard":
        folder = payload.get("folder")
        content = payload.get("content")
        
        base_path = os.path.expanduser(f"~/Kitty_Shadow/dashboards/{folder}")
        os.makedirs(base_path, exist_ok=True)
        
        with open(os.path.join(base_path, "index.html"), "w", encoding="utf-8") as f:
            f.write(content)
            
        def _start_server():
            os.chdir(base_path)
            Handler = http.server.SimpleHTTPRequestHandler
            # Tenta portas a partir de 8000
            for port in range(8000, 8050):
                try:
                    with socketserver.TCPServer(("", port), Handler) as httpd:
                        print(f"🌐 Servindo no http://127.0.0.1:{port}")
                        httpd.serve_forever()
                except OSError:
                    continue
                    
        # Inicia o servidor daemon (roda eternamente em background)
        t = threading.Thread(target=_start_server, daemon=True)
        t.start()
        
        return {"status": "success", "message": f"Server hosted at directory {base_path}."}
    
    return {"status": "error", "error_type": "Unknown Payload", "traceback": f"Payload não compreendido: {payload}"}

async def main():
    """Inicializa o Nó Trabalhador Edge e espera ordens passivamente"""
    # Define a porta default baseada no argumento.
    # Ex: python worker_main.py 5558 (Moto Harpia) ou python worker_main.py 5556 (S21 FE)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("WORKER_PORT", 5556))
    
    server = TransportServer(port=port)
    print("==================================================")
    print(f"🚀 ZeroClaw Worker Node Inicializado (Porta: {port})")
    print("==================================================")
    print("Aguardando tarefas da Master Orchestrator (Kitty)...")
    await server.start(worker_handler)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker Node desligado manualmente.")
