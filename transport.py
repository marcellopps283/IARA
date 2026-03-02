import asyncio
import zmq
import zmq.asyncio
import json

class TransportServer:
    """
    Implementa o padrão REQ/REP no nó Worker (que responde)
    ATENÇÃO: Na nova arquitetura Edge Tiering:
    - O 'Heavy Worker' (S21 FE) deve ser iniciado rodando este server na porta 5556.
    - O 'Light Worker' (Moto G4 Harpia) deve ser iniciado rodando este server na porta 5558.
    """
    def __init__(self, port=5556):
        self.port = port
        self.ctx = zmq.asyncio.Context()
        self.socket = self.ctx.socket(zmq.REP)
        
        # ZeroMQ Heartbeat Pings (Manter conexão resiliente caso o Wifi pisque)
        self.socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
        self.socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 10)
        self.socket.setsockopt(zmq.TCP_KEEPALIVE_INTVL, 5)
        
    async def start(self, message_handler):
        self.socket.bind(f"tcp://0.0.0.0:{self.port}")
        print(f"Server ZeroMQ (Worker Node) rodando na porta tcp://*:{self.port}")
        
        while True:
            try:
                # Recebe requisição via ZeroMQ
                msg_bytes = await self.socket.recv()
                msg_json = json.loads(msg_bytes.decode('utf-8'))
                
                # Executa a função repassada
                response_dict = await message_handler(msg_json)
                
                # Devolve a resposta
                await self.socket.send_string(json.dumps(response_dict))
            except Exception as e:
                print(f"Erro no processamento ZMQ: {e}")
                await self.socket.send_string(json.dumps({"error": str(e)}))

    def shutdown(self):
        self.socket.close()
        self.ctx.term()

class TransportClient:
    """Implementa o cliente REQ no nó Master (Orquestrador)"""
    def __init__(self):
        self.ctx = zmq.asyncio.Context()
        self.sockets = {} # Cache de sockets por ip:porta
        
    def _get_socket(self, ip, port):
        key = f"{ip}:{port}"
        if key not in self.sockets:
            sock = self.ctx.socket(zmq.REQ)
            
            # ZeroMQ Heartbeat (Resiliência do client)
            sock.setsockopt(zmq.TCP_KEEPALIVE, 1)
            sock.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 10)
            sock.setsockopt(zmq.TCP_KEEPALIVE_INTVL, 5)
            
            # Timeout importante para o S21 Ultra não prender a thead se o FE sumir do mDNS
            sock.setsockopt(zmq.RCVTIMEO, 15000) 
            sock.connect(f"tcp://{ip}:{port}")
            self.sockets[key] = sock
        return self.sockets[key]

    async def invoke_agent(self, ip, port, payload_dict, timeout=15):
        # O S21 Ultra viverá na tomada, então pulamos o cheque termal local.
        sock = self._get_socket(ip, port)
        try:
            # Envia a requisição
            await asyncio.wait_for(sock.send_string(json.dumps(payload_dict)), timeout=5.0)
            
            # Aguarda a resposta com timeout robusto para nós offline/inacessíveis
            resp_bytes = await asyncio.wait_for(sock.recv(), timeout=timeout)
            return json.loads(resp_bytes.decode('utf-8'))
        except (asyncio.TimeoutError, zmq.Again):
            # Recria o socket para lipar o state do ZMQ em caso de timeout
            if sock: sock.close(linger=0)
            self.sockets.pop(f"{ip}:{port}", None)
            return {"error": f"O Worker no IP {ip}:{port} está offline ou inacessível. (Timeout de {timeout}s atingido)"}
        except Exception as e:
            if sock: sock.close(linger=0)
            self.sockets.pop(f"{ip}:{port}", None)
            return {"error": f"Falha de Conexão ZMQ: {str(e)}"}
            
    def shutdown(self):
        for sock in self.sockets.values():
            sock.close()
        self.ctx.term()

# Teste simples (Executar mock client e servers simultaneamente)
async def test_transport():
    # Simula o servidor do S21 FE
    server_heavy = TransportServer(port=5556)
    # Simula o servidor do Moto G4 Harpia
    server_light = TransportServer(port=5558)
    
    async def mock_skill(payload):
        print(f"Worker processando payload: {payload['task']}")
        await asyncio.sleep(1) 
        return {"result": f"Processado via NÓ OFFLOAD"}
        
    asyncio.create_task(server_heavy.start(mock_skill))
    asyncio.create_task(server_light.start(mock_skill))
    
    await asyncio.sleep(0.5)
    client = TransportClient()
    
    print("\nMaster enviando scraping maçante para Moto G4 (Light Worker)...")
    res1 = await client.invoke_agent("127.0.0.1", 5558, {"task": "analisar arquivo shadow_log.txt"})
    print(res1)
    
    print("\nMaster enviando renderização para S21 FE (Heavy Worker)...")
    res2 = await client.invoke_agent("127.0.0.1", 5556, {"task": "processar dados RAG dense"})
    print(res2)
    
    client.shutdown()
    server_heavy.shutdown()
    server_light.shutdown()

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_transport())
