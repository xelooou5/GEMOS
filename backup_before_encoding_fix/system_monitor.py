#!/usr/bin/env python3
"""
💎 GEM OS - System Monitor
Monitors system health, performance, and resource usage
"""

import psutil
import logging
import time
import threading
import os
import glob
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# Configuração de logging para este módulo se usado de forma independente
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@dataclass
class SystemStats:
    """Estrutura de dados para estatísticas do sistema"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: Optional[float] = None
    uptime: str = ""
    active_processes: int = 0
    
class SystemMonitor:
    """Monitoriza a saúde e o desempenho do sistema"""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Inicializa o SystemMonitor com configurações e um logger.

        Args:
            config: Dicionário de configuração para o monitor do sistema.
                    Deve incluir: update_interval, cpu_threshold, memory_threshold,
                    disk_threshold, max_history, alerts_enabled, log_dir.
            logger: Instância opcional do logger.
        """
        self.config = config
        self.update_interval = self.config.get("update_interval", 30)
        self.logger = logger or logging.getLogger(__name__)
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stats_history: List[SystemStats] = []
        self.max_history = self.config.get("max_history", 100)  # Manter as últimas 100 leituras
        self.alerts_enabled = self.config.get("alerts_enabled", True)
        
        # Limiares de desempenho do config
        self.cpu_threshold = self.config.get("cpu_threshold", 80.0)
        self.memory_threshold = self.config.get("memory_threshold", 85.0)
        self.disk_threshold = self.config.get("disk_threshold", 90.0)
        
        # Diretório de logs para limpeza, configurável
        self.log_dir = Path(self.config.get("log_dir", "data/logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True) # Garantir que o diretório de logs exista

        self.logger.info(f"SystemMonitor inicializado com intervalo de {self.update_interval}s.")
        self.logger.debug(f"Limiares: CPU={self.cpu_threshold}%, Memória={self.memory_threshold}%, Disco={self.disk_threshold}%.")
        
    def start_monitoring(self):
        """Inicia o monitoramento contínuo do sistema."""
        if self.is_monitoring:
            self.logger.warning("O monitoramento do sistema já está em execução.")
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Monitoramento do sistema iniciado.")
        
    def stop_monitoring(self):
        """Para o monitoramento do sistema."""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.logger.info("Aguardando o thread do monitoramento terminar...")
                self.monitor_thread.join(timeout=5) # Espera até 5 segundos pelo thread
                if self.monitor_thread.is_alive():
                    self.logger.warning("O thread do monitoramento não terminou a tempo.")
            self.logger.info("Monitoramento do sistema parado.")
        else:
            self.logger.info("O monitoramento do sistema não estava em execução.")
        
    def _monitor_loop(self):
        """Loop principal de monitoramento."""
        while self.is_monitoring:
            try:
                stats = self.get_current_stats()
                self._update_history(stats)
                self._check_alerts(stats)
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Erro no loop de monitoramento: {e}", exc_info=True)
                time.sleep(self.update_interval) # Espera antes de tentar novamente
                
    def get_current_stats(self) -> SystemStats:
        """Obtém as estatísticas atuais do sistema."""
        try:
            # Uso de CPU
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Uso de memória
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Uso de disco
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # Tempo de atividade do sistema
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = str(datetime.now() - boot_time).split('.')[0]
            
            # Processos ativos
            active_processes = len(psutil.pids())
            
            # Temperatura (se disponível)
            temperature = self._get_temperature()
            
            return SystemStats(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                temperature=temperature,
                uptime=uptime,
                active_processes=active_processes
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas do sistema: {e}", exc_info=True)
            return SystemStats(0.0, 0.0, 0.0) # Retorna valores padrão em caso de erro
            
    def _get_temperature(self) -> Optional[float]:
        """Obtém a temperatura do sistema se disponível."""
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                # Tenta encontrar uma temperatura relevante para a CPU ou package
                for name, entries in temps.items():
                    if "cpu" in name.lower() or "package" in name.lower():
                        if entries:
                            return entries[0].current # Retorna a primeira temperatura encontrada para essa categoria
                # Se nenhuma temperatura específica da CPU for encontrada, retorna a primeira disponível
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            return entries[0].current
            return None
        except Exception as e:
            self.logger.debug(f"Não foi possível obter a temperatura do sistema: {e}")
            return None
            
    def _update_history(self, stats: SystemStats):
        """Atualiza o histórico de estatísticas."""
        self.stats_history.append(stats)
        if len(self.stats_history) > self.max_history:
            self.stats_history.pop(0)
            
    def _check_alerts(self, stats: SystemStats):
        """Verifica alertas de desempenho."""
        if not self.alerts_enabled:
            return
            
        alerts = []
        
        if stats.cpu_usage > self.cpu_threshold:
            alerts.append(f"Uso de CPU elevado: {stats.cpu_usage:.1f}% (Limite: {self.cpu_threshold:.1f}%)")
            
        if stats.memory_usage > self.memory_threshold:
            alerts.append(f"Uso de memória elevado: {stats.memory_usage:.1f}% (Limite: {self.memory_threshold:.1f}%)")
            
        if stats.disk_usage > self.disk_threshold:
            alerts.append(f"Uso de disco elevado: {stats.disk_usage:.1f}% (Limite: {self.disk_threshold:.1f}%)")
            
        for alert in alerts:
            self.logger.warning(f"🚨 ALERTA DO SISTEMA: {alert}")
            
    def get_system_info(self) -> Dict[str, Any]:
        """Obtém informações abrangentes do sistema."""
        try:
            info = {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'cpu_count_physical': psutil.cpu_count(logical=False),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                'memory_total_bytes': psutil.virtual_memory().total,
                'disk_total_bytes': psutil.disk_usage('/').total,
                'boot_time_iso': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            }
            
            # Adicionar interfaces de rede (apenas nomes)
            info['network_interfaces'] = list(psutil.net_if_addrs().keys())
            
            return info
            
        except Exception as e:
            self.logger.error(f"Erro ao obter informações do sistema: {e}", exc_info=True)
            return {}
            
    def get_resource_usage(self) -> Dict[str, Any]:
        """Obtém um resumo do uso atual de recursos."""
        stats = self.get_current_stats()
        return {
            'cpu_usage_percent': stats.cpu_usage,
            'memory_usage_percent': stats.memory_usage,
            'disk_usage_percent': stats.disk_usage,
            'uptime': stats.uptime,
            'active_processes': stats.active_processes,
            'temperature_celsius': stats.temperature
        }
        
    def get_top_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtém os principais processos por uso de CPU."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    # Apenas inclui processos com uso de CPU > 0 e status não "zombie"
                    if proc_info['cpu_percent'] > 0 and proc_info['status'] != psutil.STATUS_ZOMBIE:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Processo pode ter terminado ou acesso negado, ignora
                    continue
                    
            # Ordena por uso de CPU
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            return processes[:limit]
            
        except Exception as e:
            self.logger.error(f"Erro ao obter os principais processos: {e}", exc_info=True)
            return []
            
    def cleanup_resources(self) -> bool:
        """Limpa recursos do sistema e ficheiros de log antigos."""
        try:
            # Limpar logs antigos do diretório configurado
            if not self.log_dir.is_dir():
                self.logger.info(f"Diretório de logs '{self.log_dir}' não encontrado. A ignorar limpeza de logs.")
                return True

            log_files_cleaned = 0
            for log_file_path in self.log_dir.glob("*.log*"): # Inclui .log, .log.1, .log.gz etc.
                try:
                    file_stat = log_file_path.stat()
                    file_age = time.time() - file_stat.st_mtime
                    if file_age > 7 * 24 * 3600:  # Mais antigo que 7 dias
                        log_file_path.unlink()
                        self.logger.info(f"Removido ficheiro de log antigo: {log_file_path}")
                        log_files_cleaned += 1
                except Exception as e:
                    self.logger.error(f"Erro ao remover ficheiro de log '{log_file_path}': {e}", exc_info=True)
                    
            self.logger.info(f"Limpeza de recursos concluída. {log_files_cleaned} ficheiros de log removidos.")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro durante a limpeza de recursos: {e}", exc_info=True)
            return False
            
    def generate_health_report(self) -> str:
        """Gera um relatório completo da saúde do sistema."""
        try:
            stats = self.get_current_stats()
            info = self.get_system_info()
            
            report = f"""
=== Relatório de Saúde do Sistema GEM OS ===
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

STATUS ATUAL:
- Uso de CPU: {stats.cpu_usage:.1f}%
- Uso de Memória: {stats.memory_usage:.1f}%
- Uso de Disco: {stats.disk_usage:.1f}%
- Tempo de Atividade: {stats.uptime}
- Processos Ativos: {stats.active_processes}
- Temperatura (CPU/Principal): {f'{stats.temperature:.1f}°C' if stats.temperature is not None else 'N/A'}

INFORMAÇÕES DO SISTEMA:
- Plataforma: {info.get('platform', 'Desconhecida')} ({info.get('platform_version', 'N/A')})
- Arquitetura: {info.get('architecture', 'N/A')}
- Cores de CPU (Físicos/Lógicos): {info.get('cpu_count_physical', 'N/A')}/{info.get('cpu_count_logical', 'N/A')}
- Frequência da CPU: {f"{info['cpu_freq']['current']:.1f} MHz (Min: {info['cpu_freq']['min']:.1f}, Max: {info['cpu_freq']['max']:.1f})" if info.get('cpu_freq') else 'N/A'}
- Memória Total: {info.get('memory_total_bytes', 0) // (1024**3):.1f} GB
- Disco Total: {info.get('disk_total_bytes', 0) // (1024**3):.1f} GB
- Início do Sistema: {info.get('boot_time_iso', 'N/A')}
- Interfaces de Rede: {', '.join(info.get('network_interfaces', ['N/A']))}

STATUS DE SAÚDE GERAL: {'✅ SAUDÁVEL' if self._is_system_healthy(stats) else '⚠️ REQUER ATENÇÃO'}
"""
            
            return report.strip()
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar relatório de saúde: {e}", exc_info=True)
            return "Erro ao gerar relatório de saúde do sistema."
            
    def _is_system_healthy(self, stats: SystemStats) -> bool:
        """Verifica se o sistema está em um estado saudável com base nos limiares configurados."""
        return (
            stats.cpu_usage < self.cpu_threshold and
            stats.memory_usage < self.memory_threshold and
            stats.disk_usage < self.disk_threshold
        )
        
    def enable_alerts(self):
        """Ativa os alertas do sistema."""
        self.alerts_enabled = True
        self.logger.info("Alertas do sistema ativados.")
        
    def disable_alerts(self):
        """Desativa os alertas do sistema."""
        self.alerts_enabled = False
        self.logger.info("Alertas do sistema desativados.")
        
# Instância global do monitor
_monitor_instance: Optional[SystemMonitor] = None
_monitor_lock = threading.Lock() # Para garantir a criação de singleton thread-safe

def get_monitor(config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None) -> SystemMonitor:
    """
    Obtém a instância global do monitor do sistema (Singleton).
    Se chamada pela primeira vez, inicializa com a configuração e o logger fornecidos.
    """
    global _monitor_instance
    with _monitor_lock:
        if _monitor_instance is None:
            if config is None:
                raise RuntimeError("SystemMonitor deve ser inicializado com uma configuração na primeira vez que get_monitor é chamado.")
            _monitor_instance = SystemMonitor(config=config, logger=logger)
        return _monitor_instance

# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    # Configurar logging para teste autônomo
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestSystemMonitor")

    # Configuração dummy para testes
    test_monitor_config = {
        "update_interval": 5, # Intervalo de atualização mais curto para testes
        "cpu_threshold": 90.0, # Limiares mais altos para facilitar o teste de "saudável"
        "memory_threshold": 95.0,
        "disk_threshold": 99.0,
        "log_dir": "data/test_logs", # Usar um diretório de logs de teste
        "max_history": 10,
        "alerts_enabled": True
    }
    
    # Garantir que o diretório de logs de teste exista e limpá-lo antes do teste
    test_log_dir = Path(test_monitor_config["log_dir"])
    if test_log_dir.exists():
        for f in test_log_dir.iterdir():
            f.unlink()
        test_log_dir.rmdir()
    test_log_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Diretório de logs de teste criado/limpo: {test_log_dir}")


    monitor = get_monitor(config=test_monitor_config, logger=logger)
    monitor.start_monitoring()
    
    try:
        logger.info("\n--- Monitoramento do sistema em execução por 20 segundos (Ctrl+C para parar mais cedo). ---")
        time.sleep(20) # Executa o monitor por 20 segundos

        logger.info("\n--- Gerando Relatório de Saúde do Sistema ---")
        print(monitor.generate_health_report())

        logger.info("\n--- Verificando Top Processos (os 3 principais por uso de CPU) ---")
        top_procs = monitor.get_top_processes(limit=3)
        if top_procs:
            for i, proc in enumerate(top_procs):
                print(f"{i+1}. PID: {proc.get('pid', 'N/A')}, Nome: {proc.get('name', 'N/A')}, CPU: {proc.get('cpu_percent', 0.0):.1f}%, Memória: {proc.get('memory_percent', 0.0):.1f}%")
        else:
            print("Nenhum processo significativo encontrado.")

        logger.info("\n--- Testando Limpeza de Recursos (logs) ---")
        # Criar um ficheiro de log antigo dummy
        old_log_file = test_log_dir / "old_test.log"
        with open(old_log_file, "w") as f:
            f.write("Este é um log antigo de teste.")
        # Definir o tempo de modificação para 8 dias atrás
        os.utime(old_log_file, (time.time() - (8 * 24 * 3600), time.time() - (8 * 24 * 3600))) 
        logger.info(f"Ficheiro de log antigo dummy criado: {old_log_file}")
        
        # Criar um ficheiro de log novo dummy
        new_log_file = test_log_dir / "new_test.log"
        with open(new_log_file, "w") as f:
            f.write("Este é um log novo de teste.")
        logger.info(f"Ficheiro de log novo dummy criado: {new_log_file}")

        monitor.cleanup_resources()
        
        # Verificar se o ficheiro antigo foi removido e o novo permaneceu
        assert not old_log_file.exists()
        assert new_log_file.exists()
        logger.info("✅ Teste de limpeza de logs concluído: Ficheiro antigo removido, novo ficheiro permaneceu.")

    except KeyboardInterrupt:
        logger.info("Monitoramento interrompido pelo usuário (Ctrl+C).")
    finally:
        monitor.stop_monitoring()
        # Limpar diretório de logs de teste
        if test_log_dir.exists():
            for f in test_log_dir.iterdir():
                f.unlink()
            test_log_dir.rmdir()
            logger.info("Recursos de teste limpos.")

