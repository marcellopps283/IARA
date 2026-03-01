import asyncio
import socket
import json
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceInfo
from zeroconf import ServiceBrowser, ServiceStateChange

# --- MÓDULO DE DESCOBERTA mDNS (ZERO_CONF) --- #
SERVICE_TYPE = "_zeroclaw._tcp.local."
MASTER_NAME = "S21_Ultra_Master"
WORKER_PREFIX = "Worker_"

class NetworkController:
    def __init__(self, node_type="master", port=5555):
        self.node_type = node_type
        self.port = port
        self.aio_zc = None
        self.info = None
        self.known_workers = {} # {nome_do_servico: (ip, porta, status)}
        self.loop = asyncio.get_running_loop()

    async def get_local_ip(self):
        """Retorna o IP local na rede Wi-Fi"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Callback acionado quando um nó entra ou sai da rede (roda em thread paralela do zc)"""
        if state_change is ServiceStateChange.Added:
            # Precisa injetar a corrotina de volta no event loop principal
            asyncio.run_coroutine_threadsafe(self.on_service_added(zeroconf, service_type, name), self.loop)
        elif state_change is ServiceStateChange.Removed:
            print(f"Nó Desconectado: {name}")
            if name in self.known_workers:
                del self.known_workers[name]

    async def on_service_added(self, zeroconf, service_type, name):
        """Resolve o endereço de um novo Worker descoberto"""
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)
        
        if info:
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            # Recupera os metadados (TXT records), como temperatura/bateria 
            properties = {k.decode('utf-8'): v.decode('utf-8') for k, v in info.properties.items()}
            print(f"Novo Nó Detectado: {name} em {ip}:{port} - Props: {properties}")
            
            if name.startswith(WORKER_PREFIX):
                self.known_workers[name] = {"ip": ip, "port": port, "props": properties}

    async def start_broadcasting(self, properties=None):
        """Anuncia a própria existência na rede local via mDNS"""
        self.aio_zc = AsyncZeroconf()
        ip = await self.get_local_ip()
        
        if self.node_type == "master":
            name = f"{MASTER_NAME}.{SERVICE_TYPE}"
        else:
            # Em um cenário distribuído real, usaríamos um ID único (MAC address)
            name = f"{WORKER_PREFIX}Local_{self.port}.{SERVICE_TYPE}"

        if properties is None:
            properties = {"status": "online", "type": self.node_type}

        self.info = AsyncServiceInfo(
            SERVICE_TYPE,
            name,
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties=properties
        )
        
        print(f"Broadcasting mDNS {self.node_type.upper()} em {ip}:{self.port} como {name}")
        await self.aio_zc.async_register_service(self.info)

        if self.node_type == "master":
            # O Master atua como um Browser para localizar os Workers
            self.browser = ServiceBrowser(self.aio_zc.zeroconf, SERVICE_TYPE, handlers=[self.on_service_state_change])

    async def shutdown(self):
        """Desliga o broadcast civilizadamente"""
        if self.aio_zc:
            if self.info:
                await self.aio_zc.async_unregister_service(self.info)
            await self.aio_zc.async_close()
            print(f"Broadcast encerrado para {self.node_type}.")

# Exemplo de teste rápido que pode ser acionado apenas importando
async def test_mdns():
    print("Iniciando testes mDNS Locais...")
    master = NetworkController(node_type="master", port=5555)
    worker1 = NetworkController(node_type="worker", port=5556)
    
    await master.start_broadcasting()
    await asyncio.sleep(1) # Aguarda master decolar
    await worker1.start_broadcasting(properties={"battery": "80%", "temp": "35C"})
    
    await asyncio.sleep(3) # Aguarda descoberta preencher o dicionário do Master
    print(f"Workers mapeados pelo Master: {list(master.known_workers.keys())}")
    
    await worker1.shutdown()
    await master.shutdown()

if __name__ == "__main__":
    asyncio.run(test_mdns())
