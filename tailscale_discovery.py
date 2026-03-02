import asyncio
import json
import logging

logger = logging.getLogger("tailscale_discovery")

async def get_tailscale_ip(hostname_or_alias: str) -> str | None:
    """
    Executa `tailscale status --json` para descobrir dinamicamente o IP 100.x.x.x
    do nó no tailnet a partir de seu Hostname (ex: 'S21FE', 'MotoG4').
    Isso substitui o hardcoding de IPs e é resiliente a mudanças e apagões de MagicDNS.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "tailscale", "status", "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        
        if proc.returncode != 0:
            err = stderr.decode("utf-8").strip()
            logger.error(f"⚠️ [Tailscale] Erro ao buscar status: {err}")
            return None
            
        data = json.loads(stdout.decode("utf-8"))
        target_lower = hostname_or_alias.lower()
        
        # Iterar sobre todos os peers (os nós além deste)
        peers = data.get("Peer", {})
        for peer_id, peer_info in peers.items():
            name = peer_info.get("HostName", "").lower()
            dns_name = peer_info.get("DNSName", "").lower()
            
            # Se bateu o nome exato ou parte significativa do DNS Tailscale
            if target_lower == name or target_lower in dns_name.split(".")[0]:
                ips = peer_info.get("TailscaleIPs", [])
                if ips:
                    logger.info(f"🔎 [Tailscale] IP recuperado para '{hostname_or_alias}': {ips[0]}")
                    return ips[0]
                    
        logger.warning(f"🔎 [Tailscale] Hostname '{hostname_or_alias}' não encontrado na tailnet.")
        return None
        
    except asyncio.TimeoutError:
        logger.error(f"⚠️ [Tailscale] CLI demorou muito para responder (Timeout).")
        return None
    except Exception as e:
        logger.error(f"⚠️ [Tailscale] Exceção na descoberta de '{hostname_or_alias}': {e}")
        return None
