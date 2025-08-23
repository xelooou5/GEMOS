#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Network Manager (core/network_manager.py)
Manages network connectivity, status, and related information.

Responsibilities
----------------
- Check internet connectivity status.
- Retrieve network interface details (IP, MAC, etc.).
- Perform basic network diagnostics (ping, DNS lookup).
- Expose network capabilities as tools for the LLM.
- Publish network-related events.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import subprocess
import re # Para parsing de IPs
import socket # Para resolução de DNS
import psutil # Para informações de rede de baixo nível
from ipaddress import IPv4Address, IPv6Address, AddressValueError # Para validação de IP
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_ERROR

# Forward declarations for type hinting
class EventManager:
    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        pass

class TTSModule:
    async def speak(self, text: str) -> None:
        pass

class ConfigManager:
    def get_config(self) -> Any:
        pass

class Storage:
    pass

# --- Dataclass para Informações de Interface de Rede ---
@dataclass
class NetworkInterfaceInfo:
    name: str
    is_up: bool
    address: Optional[str] = None
    netmask: Optional[str] = None
    broadcast: Optional[str] = None
    mac_address: Optional[str] = None
    speed_mbps: Optional[int] = None # Velocidade da interface (se disponível)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "is_up": self.is_up,
            "address": self.address,
            "netmask": self.netmask,
            "broadcast": self.broadcast,
            "mac_address": self.mac_address,
            "speed_mbps": self.speed_mbps,
        }

# --- Network Manager como um Plugin ---
class NetworkManager(BasePlugin):
    """
    Manages network-related functionalities for GEM OS, acting as a plugin.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("NetworkManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        self._internet_check_host = self.config_manager.get_config().general.internet_check_host # Host para verificar conectividade
        self._internet_check_port = self.config_manager.get_config().general.internet_check_port # Porta para verificar conectividade
        self._check_interval = self.config_manager.get_config().general.network_check_interval_seconds # Intervalo de verificação
        self._is_online: Optional[bool] = None # Estado atual da conectividade
        self._check_task: Optional[asyncio.Task] = None

        self.logger.info(f"NetworkManager configurado com host de verificação: {self._internet_check_host}:{self._internet_check_port}")

    async def initialize(self) -> None:
        """Starts the background task for periodically checking network status."""
        if not self._check_task:
            self._check_task = asyncio.create_task(self._periodic_network_check())
            self.logger.info("Verificação periódica de rede iniciada.")
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        await self._check_internet_connectivity(silent=True) # Check once at startup
        self.logger.info("NetworkManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully stop network checks."""
        self.logger.info("Recebido GEM_SHUTDOWN. A parar as verificações de rede.")
        self.shutdown()

    async def _periodic_network_check(self) -> None:
        """Periodically checks internet connectivity and publishes events on status change."""
        self.logger.debug("Loop de verificação periódica de rede iniciado.")
        while True:
            try:
                await self._check_internet_connectivity()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                self.logger.info("Tarefa de verificação periódica de rede cancelada.")
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de verificação de rede: {e}", exc_info=True)
                await asyncio.sleep(self._check_interval * 2) # Espera mais tempo em caso de erro

    async def _check_internet_connectivity(self, silent: bool = False) -> bool:
        """
        Checks if there is active internet connectivity.
        
        Args:
            silent: If True, suppresses notifications and vocal feedback unless status changes.
            
        Returns:
            True if online, False otherwise.
        """
        current_online_status = False
        try:
            # Tenta fazer uma conexão simples a um host conhecido (Google DNS)
            reader, writer = await asyncio.open_connection(self._internet_check_host, self._internet_check_port)
            writer.close()
            await writer.wait_closed()
            current_online_status = True
        except (socket.gaierror, ConnectionRefusedError, asyncio.TimeoutError):
            current_online_status = False
        except Exception as e:
            self.logger.warning(f"Erro inesperado ao verificar conectividade: {e}", exc_info=True)
            current_online_status = False # Assumir offline em caso de erro desconhecido

        if current_online_status != self._is_online:
            self._is_online = current_online_status
            if self._is_online:
                message = "Conexão à internet restabelecida."
                self.logger.info(f"🌐 {message}")
                if not silent:
                    await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
                    await self.tts_module.speak(message)
                await self.event_manager.publish("NETWORK_ONLINE", {"status": True})
            else:
                message = "Conexão à internet perdida."
                self.logger.warning(f"⛔ {message}")
                if not silent:
                    await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING)
                    await self.tts_module.speak(message)
                await self.event_manager.publish("NETWORK_OFFLINE", {"status": False})
        elif current_online_status and not silent:
            # Se ainda online e não for silencioso, podemos dar um feedback positivo
            message = "A internet está online e funcionando."
            await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO, vocalize=False)
            await self._speak_response(message)


        return current_online_status

    async def _get_network_status_command(self) -> Dict[str, Any]:
        """
        Reports the current internet connectivity status.
        """
        is_online = await self._check_internet_connectivity(silent=True)
        message = "A internet está online." if is_online else "A internet está offline."
        await self._speak_response(message)
        return {"success": True, "output": message, "error": None}

    async def _get_ip_address_command(self, interface: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves the IP address of the system or a specific network interface.
        """
        try:
            interfaces = psutil.net_if_addrs()
            output_lines = []
            
            if interface: # Specific interface requested
                if interface in interfaces:
                    output_lines.append(f"Informações para a interface '{interface}':")
                    info = self._get_interface_details(interface, interfaces[interface])
                    output_lines.append(f"  Endereço IP: {info.address or 'N/A'}")
                    output_lines.append(f"  Endereço MAC: {info.mac_address or 'N/A'}")
                    output_lines.append(f"  Máscara de Rede: {info.netmask or 'N/A'}")
                    message = "\n".join(output_lines)
                    await self._speak_response(f"O endereço IP para {interface} foi obtido. Verifique o ecrã para os detalhes.")
                    return {"success": True, "output": message, "error": None}
                else:
                    message = f"Interface de rede '{interface}' não encontrada."
                    await self._speak_response(message)
                    return {"success": False, "output": message, "error": "Interface not found"}
            else: # All active interfaces
                for name, addrs in interfaces.items():
                    info = self._get_interface_details(name, addrs)
                    if info.is_up and info.address and not info.address.startswith("127."): # Only show active, non-loopback IPs
                        output_lines.append(f"Interface: {info.name}")
                        output_lines.append(f"  Endereço IP: {info.address}")
                        output_lines.append(f"  Endereço MAC: {info.mac_address or 'N/A'}")
                        output_lines.append(f"  Máscara de Rede: {info.netmask or 'N/A'}")
                        output_lines.append("-" * 20)
                
                if output_lines:
                    message = "Endereços IP e detalhes de rede:\n" + "\n".join(output_lines)
                    await self._speak_response("Os endereços IP foram obtidos. Verifique o ecrã para os detalhes.")
                    return {"success": True, "output": message, "error": None}
                else:
                    message = "Nenhum endereço IP ativo encontrado."
                    await self._speak_response(message)
                    return {"success": True, "output": message, "error": None} # Not an error

        except Exception as e:
            error_message = f"Falha ao obter endereço IP: {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}

    def _get_interface_details(self, name: str, addrs: List[Any]) -> NetworkInterfaceInfo:
        """Helper to extract details for a specific network interface."""
        info = NetworkInterfaceInfo(name=name, is_up=False)
        for addr in addrs:
            if addr.family == socket.AF_INET: # IPv4
                info.address = addr.address
                info.netmask = addr.netmask
                info.broadcast = addr.broadcast
            elif addr.family == socket.AF_PACKET: # MAC address
                info.mac_address = addr.address
        
        # Check if interface is up (psutil.net_if_stats)
        stats = psutil.net_if_stats().get(name)
        if stats:
            info.is_up = stats.isup
            # info.speed_mbps = stats.speed # psutil.net_if_stats().speed often returns 0 or N/A on some systems
        return info

    async def _ping_host_command(self, host: str, count: int = 4) -> Dict[str, Any]:
        """
        Pings a host to check reachability and latency.
        
        Args:
            host: The hostname or IP address to ping.
            count: Number of ping packets to send.
        """
        try:
            cmd = []
            if platform.system() == "Windows":
                cmd = ["ping", "-n", str(count), host]
            else: # Linux, macOS
                cmd = ["ping", "-c", str(count), host]
            
            self.logger.debug(f"A executar comando: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode().strip()
            error_output = stderr.decode().strip()

            if process.returncode == 0:
                message = f"Ping para {host} concluído com sucesso.\n{output}"
                await self._speak_response(f"Ping para {host} concluído. Verifique o ecrã para os resultados.")
                return {"success": True, "output": message, "error": None}
            else:
                error_message = f"Falha ao fazer ping em {host}. Erro: {output}\n{error_output}"
                self.logger.error(error_message)
                await self._speak_response(f"Falha ao fazer ping em {host}.")
                return {"success": False, "output": "", "error": error_message}
        except Exception as e:
            error_message = f"Erro inesperado ao fazer ping em {host}: {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(f"Ocorreu um erro ao fazer ping em {host}.")
            return {"success": False, "output": "", "error": error_message}

    async def _dns_lookup_command(self, hostname: str) -> Dict[str, Any]:
        """
        Performs a DNS lookup for a given hostname, returning IP addresses.
        
        Args:
            hostname: The hostname to resolve.
        """
        try:
            ip_addresses = await asyncio.to_thread(socket.gethostbyname_ex, hostname)
            # ip_addresses é uma tupla: (hostname, aliaslist, ipaddrlist)
            resolved_ips = ip_addresses[2]
            
            if resolved_ips:
                message = f"Endereços IP para '{hostname}': {', '.join(resolved_ips)}"
                await self._speak_response(f"Resolução DNS para {hostname} concluída.")
                return {"success": True, "output": message, "error": None}
            else:
                message = f"Nenhum endereço IP encontrado para '{hostname}'."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}
        except socket.gaierror as e:
            error_message = f"Não foi possível resolver o hostname '{hostname}': {e}"
            self.logger.error(error_message)
            await self._speak_response(f"Não foi possível resolver o hostname {hostname}.")
            return {"success": False, "output": "", "error": error_message}
        except Exception as e:
            error_message = f"Erro inesperado durante a resolução DNS para '{hostname}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(f"Ocorreu um erro na resolução DNS para {hostname}.")
            return {"success": False, "output": "", "error": error_message}


    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers network management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin NetworkManager...")
        executor.register_command("get_network_status", self._get_network_status_command)
        executor.register_command("get_ip_address", self._get_ip_address_command)
        executor.register_command("ping_host", self._ping_host_command)
        executor.register_command("dns_lookup", self._dns_lookup_command)
        self.logger.info("Comandos NetworkManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for network management features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_network_status",
                    "description": "Verifica e reporta o status atual da conexão à internet (online/offline).",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_ip_address",
                    "description": "Obtém o endereço IP do sistema ou de uma interface de rede específica.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "interface": {
                                "type": "string",
                                "description": "O nome da interface de rede (ex: 'eth0', 'wlan0'). Opcional; se omitido, retorna para todas as interfaces ativas.",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ping_host",
                    "description": "Envia pacotes ICMP para um host para verificar a sua acessibilidade e medir a latência da rede.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host": {
                                "type": "string",
                                "description": "O hostname ou endereço IP para o qual fazer ping (ex: 'google.com', '8.8.8.8').",
                            },
                            "count": {
                                "type": "integer",
                                "description": "O número de pacotes de ping a enviar. Padrão para 4.",
                                "default": 4
                            }
                        },
                        "required": ["host"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "dns_lookup",
                    "description": "Realiza uma resolução DNS para um determinado hostname, retornando os endereços IP associados.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostname": {
                                "type": "string",
                                "description": "O hostname para o qual realizar a pesquisa DNS (ex: 'example.com').",
                            }
                        },
                        "required": ["hostname"],
                    },
                },
            },
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas através do módulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"Módulo TTS não disponível para falar: '{text}'")

    def shutdown(self) -> None:
        """Stops any ongoing background tasks and performs cleanup."""
        self.logger.info("NetworkManager a ser desligado. A parar a tarefa de verificação de rede.")
        if self._check_task:
            self._check_task.cancel()
            self._check_task = None
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestNetworkManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._listeners = defaultdict(list)
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")
            if event_type in self._listeners:
                for listener in self._listeners[event_type]:
                    asyncio.create_task(listener(data))
        def subscribe(self, event_type: str, listener: Callable) -> None:
            self.logger.debug(f"Dummy EventManager: Subscrito '{listener.__name__}' para '{event_type}'")
            self._listeners[event_type].append(listener)
        def unsubscribe(self, event_type: str, listener: Callable) -> None:
            if event_type in self._listeners and listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)
                self.logger.debug(f"Dummy EventManager: Desubscrito '{listener.__name__}' de '{event_type}'")

    class DummyNotificationManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._history: List[Dict[str, Any]] = []
        async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
            self.logger.info(f"Dummy Notification: [{level.upper()}] {message} (Vocalize: {vocalize})")
            self._history.append({"message": message, "level": level})
            await asyncio.sleep(0.01)

    class DummyTTSModule:
        def __init__(self, logger_instance):
            self.logger = logger_instance
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS: A falar: '{text}'")
            await asyncio.sleep(0.01)

    class DummyCommandExecutor:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self.commands = {}
        def register_command(self, name: str, func: Callable[..., Awaitable[Dict[str, Any]]], **kwargs) -> None:
            self.commands[name] = (func, kwargs)
            self.logger.info(f"Dummy CommandExecutor: Registou comando '{name}'.")
        async def execute(self, command_name: str, *args, **kwargs) -> Dict[str, Any]:
            self.logger.info(f"Dummy CommandExecutor: A executar '{command_name}' com args={args}, kwargs={kwargs}")
            if command_name in self.commands:
                func, default_kwargs = self.commands[command_name]
                merged_kwargs = {**default_kwargs, **kwargs}
                return await func(*args, **merged_kwargs)
            return {"success": False, "output": "", "error": "Comando desconhecido simulado."}

    class DummyConfigManager:
        def __init__(self):
            self.config = type('GEMConfig', (), {
                'general': type('GeneralConfig', (), {
                    'internet_check_host': '8.8.8.8',
                    'internet_check_port': 53,
                    'network_check_interval_seconds': 5, # Curto para testes
                    'enable_audio_notifications': True
                })()
            })()
        def get_config(self) -> Any:
            return self.config

    class DummyGEM:
        def __init__(self, logger_instance: logging.Logger):
            self.logger = logger_instance
            self.event_manager = DummyEventManager(logger_instance)
            self.notification_manager = DummyNotificationManager(logger_instance)
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager()
            self.command_executor = DummyCommandExecutor(logger_instance)
            self.storage = type('DummyStorage', (), {})() # Not used directly by NetworkManager

    async def run_network_manager_tests():
        print("\n--- Iniciando Testes do NetworkManager ---")

        dummy_gem = DummyGEM(logger)
        network_manager = NetworkManager(dummy_gem, logger)
        
        network_manager.register_commands(dummy_gem.command_executor)

        await network_manager.initialize() # Inicia a verificação periódica

        print("\n--- Teste 1: Obter Status da Rede ---")
        result_status = await dummy_gem.command_executor.execute("get_network_status")
        print(result_status["output"])
        # A assertiva pode variar dependendo da sua conexão real
        assert "A internet está online." in result_status["output"] or "A internet está offline." in result_status["output"]

        print("\n--- Teste 2: Obter Endereço IP (geral) ---")
        result_ip = await dummy_gem.command_executor.execute("get_ip_address")
        print(result_ip["output"])
        assert "Endereços IP e detalhes de rede" in result_ip["output"] or "Nenhum endereço IP ativo encontrado." in result_ip["output"]

        # Pode precisar de ajustar o nome da interface dependendo do seu sistema
        # Ex: "eth0", "wlan0" para Linux, "en0" para macOS, ou o nome que aparece na lista
        # print("\n--- Teste 3: Obter Endereço IP (interface específica) ---")
        # # Substitua 'eth0' pela sua interface real para testar
        # result_ip_specific = await dummy_gem.command_executor.execute("get_ip_address", interface="eth0")
        # print(result_ip_specific["output"])
        # assert "Informações para a interface 'eth0':" in result_ip_specific["output"]

        print("\n--- Teste 4: Ping Host ---")
        # Nota: O ping requer permissões em alguns sistemas (sudo no Linux para ICMP raw)
        # Para testes mais robustos, pode ser necessário um mock de subprocess.run
        # ou apenas verificar o sucesso do comando, assumindo o ping subjacente funciona.
        result_ping = await dummy_gem.command_executor.execute("ping_host", host="google.com", count=1)
        print(result_ping["output"])
        assert result_ping["success"] is True or "Falha ao fazer ping em google.com" in result_ping["error"] # Depende da conectividade

        print("\n--- Teste 5: Resolução DNS ---")
        result_dns = await dummy_gem.command_executor.execute("dns_lookup", hostname="example.com")
        print(result_dns["output"])
        assert "Endereços IP para 'example.com':" in result_dns["output"]

        print("\n--- Teste 6: Verificar verificação periódica (offline simulado) ---")
        # Temporariamente sobrescrever o host para simular offline
        network_manager._internet_check_host = "invalid.host.nonexistent"
        print("Simulando host offline para próxima verificação...")
        await asyncio.sleep(network_manager._check_interval + 1) # Aguarda a próxima verificação
        
        result_status_offline = await dummy_gem.command_executor.execute("get_network_status")
        print(result_status_offline["output"])
        assert "A internet está offline." in result_status_offline["output"]
        assert any(n["message"] == "Conexão à internet perdida." for n in dummy_gem.notification_manager._history)

        print("\n--- Teste 7: Restaurar e verificar online ---")
        network_manager._internet_check_host = dummy_gem.config_manager.get_config().general.internet_check_host # Restaurar host
        print("Restaurando host para online. Aguardando...")
        await asyncio.sleep(network_manager._check_interval + 1) # Aguarda a próxima verificação

        result_status_online = await dummy_gem.command_executor.execute("get_network_status")
        print(result_status_online["output"])
        assert "A internet está online." in result_status_online["output"]
        assert any(n["message"] == "Conexão à internet restabelecida." for n in dummy_gem.notification_manager._history)

        print("\n--- Testes do NetworkManager concluídos com sucesso. ---")
        network_manager.shutdown()
        await asyncio.sleep(0.1) # Give shutdown task a moment
        assert network_manager._check_task is None or network_manager._check_task.done()

    asyncio.run(run_network_manager_tests())

