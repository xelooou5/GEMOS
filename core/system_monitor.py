#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - System Monitor
Health monitoring and performance tracking for accessibility
"""

import asyncio
import logging
import psutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import json


class SystemMetrics:
    """System performance metrics."""
    
    def __init__(self):
        self.timestamp = time.time()
        self.cpu_percent = 0.0
        self.memory_percent = 0.0
        self.memory_available = 0
        self.disk_usage = 0.0
        self.network_sent = 0
        self.network_recv = 0
        self.temperature = None
        self.battery_percent = None
        self.processes_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available": self.memory_available,
            "disk_usage": self.disk_usage,
            "network_sent": self.network_sent,
            "network_recv": self.network_recv,
            "temperature": self.temperature,
            "battery_percent": self.battery_percent,
            "processes_count": self.processes_count
        }


class HealthAlert:
    """System health alert."""
    
    def __init__(self, level: str, message: str, metric: str, value: float, threshold: float):
        self.level = level  # info, warning, critical
        self.message = message
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "message": self.message,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp
        }


class SystemMonitor:
    """System health and performance monitor."""
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("SystemMonitor")
        
        # Monitoring settings
        self.monitoring_interval = getattr(config, 'monitoring_interval', 30)  # seconds
        self.metrics_history_size = getattr(config, 'metrics_history_size', 1000)
        
        # Thresholds
        self.cpu_warning_threshold = getattr(config, 'cpu_warning_threshold', 80.0)
        self.cpu_critical_threshold = getattr(config, 'cpu_critical_threshold', 95.0)
        self.memory_warning_threshold = getattr(config, 'memory_warning_threshold', 80.0)
        self.memory_critical_threshold = getattr(config, 'memory_critical_threshold', 95.0)
        self.disk_warning_threshold = getattr(config, 'disk_warning_threshold', 85.0)
        self.disk_critical_threshold = getattr(config, 'disk_critical_threshold', 95.0)
        self.temperature_warning_threshold = getattr(config, 'temperature_warning_threshold', 70.0)
        self.temperature_critical_threshold = getattr(config, 'temperature_critical_threshold', 85.0)
        
        # State
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Data storage
        self.metrics_history: List[SystemMetrics] = []
        self.alerts_history: List[HealthAlert] = []
        self.alert_callbacks: List[Callable] = []
        
        # Performance tracking
        self.gem_process = None
        self.gem_start_time = time.time()
        
        # Data directory
        self.data_dir = Path.home() / ".gem" / "monitoring"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def start_monitoring(self):
        """Start system monitoring."""
        if self.is_monitoring:
            self.logger.warning("System monitoring already running")
            return
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        # Get GEM process info
        try:
            self.gem_process = psutil.Process()
        except Exception as e:
            self.logger.warning(f"Could not get GEM process info: {e}")
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        # Save final metrics
        self._save_metrics_to_file()
        
        self.logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self.stop_event.wait(self.monitoring_interval):
            try:
                metrics = self._collect_metrics()
                self._store_metrics(metrics)
                self._check_health(metrics)
            
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    def _collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        metrics = SystemMetrics()
        
        try:
            # CPU usage
            metrics.cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.memory_percent = memory.percent
            metrics.memory_available = memory.available
            
            # Disk usage
            disk = psutil.disk_usage('/')
            metrics.disk_usage = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            metrics.network_sent = network.bytes_sent
            metrics.network_recv = network.bytes_recv
            
            # Temperature (if available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get CPU temperature
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            if entries:
                                metrics.temperature = entries[0].current
                                break
            except (AttributeError, OSError):
                pass  # Temperature sensors not available
            
            # Battery (if available)
            try:
                battery = psutil.sensors_battery()
                if battery:
                    metrics.battery_percent = battery.percent
            except (AttributeError, OSError):
                pass  # Battery not available
            
            # Process count
            metrics.processes_count = len(psutil.pids())
        
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _store_metrics(self, metrics: SystemMetrics):
        """Store metrics in history."""
        self.metrics_history.append(metrics)
        
        # Keep history size manageable
        if len(self.metrics_history) > self.metrics_history_size:
            self.metrics_history = self.metrics_history[-self.metrics_history_size:]
    
    def _check_health(self, metrics: SystemMetrics):
        """Check system health and generate alerts."""
        alerts = []
        
        # CPU check
        if metrics.cpu_percent >= self.cpu_critical_threshold:
            alerts.append(HealthAlert(
                "critical", 
                f"CPU usage crítico: {metrics.cpu_percent:.1f}%",
                "cpu_percent", 
                metrics.cpu_percent, 
                self.cpu_critical_threshold
            ))
        elif metrics.cpu_percent >= self.cpu_warning_threshold:
            alerts.append(HealthAlert(
                "warning", 
                f"CPU usage alto: {metrics.cpu_percent:.1f}%",
                "cpu_percent", 
                metrics.cpu_percent, 
                self.cpu_warning_threshold
            ))
        
        # Memory check
        if metrics.memory_percent >= self.memory_critical_threshold:
            alerts.append(HealthAlert(
                "critical", 
                f"Memória crítica: {metrics.memory_percent:.1f}%",
                "memory_percent", 
                metrics.memory_percent, 
                self.memory_critical_threshold
            ))
        elif metrics.memory_percent >= self.memory_warning_threshold:
            alerts.append(HealthAlert(
                "warning", 
                f"Memória alta: {metrics.memory_percent:.1f}%",
                "memory_percent", 
                metrics.memory_percent, 
                self.memory_warning_threshold
            ))
        
        # Disk check
        if metrics.disk_usage >= self.disk_critical_threshold:
            alerts.append(HealthAlert(
                "critical", 
                f"Disco crítico: {metrics.disk_usage:.1f}%",
                "disk_usage", 
                metrics.disk_usage, 
                self.disk_critical_threshold
            ))
        elif metrics.disk_usage >= self.disk_warning_threshold:
            alerts.append(HealthAlert(
                "warning", 
                f"Disco cheio: {metrics.disk_usage:.1f}%",
                "disk_usage", 
                metrics.disk_usage, 
                self.disk_warning_threshold
            ))
        
        # Temperature check
        if metrics.temperature is not None:
            if metrics.temperature >= self.temperature_critical_threshold:
                alerts.append(HealthAlert(
                    "critical", 
                    f"Temperatura crítica: {metrics.temperature:.1f}°C",
                    "temperature", 
                    metrics.temperature, 
                    self.temperature_critical_threshold
                ))
            elif metrics.temperature >= self.temperature_warning_threshold:
                alerts.append(HealthAlert(
                    "warning", 
                    f"Temperatura alta: {metrics.temperature:.1f}°C",
                    "temperature", 
                    metrics.temperature, 
                    self.temperature_warning_threshold
                ))
        
        # Store and notify alerts
        for alert in alerts:
            self._handle_alert(alert)
    
    def _handle_alert(self, alert: HealthAlert):
        """Handle system alert."""
        self.alerts_history.append(alert)
        
        # Keep alerts history manageable
        if len(self.alerts_history) > 100:
            self.alerts_history = self.alerts_history[-100:]
        
        # Log alert
        if alert.level == "critical":
            self.logger.critical(alert.message)
        elif alert.level == "warning":
            self.logger.warning(alert.message)
        else:
            self.logger.info(alert.message)
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback."""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable):
        """Remove alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        if not self.metrics_history:
            return {"status": "no_data", "message": "Nenhum dado de monitoramento disponível"}
        
        latest_metrics = self.metrics_history[-1]
        
        # Determine overall health status
        critical_alerts = [a for a in self.alerts_history[-10:] if a.level == "critical"]
        warning_alerts = [a for a in self.alerts_history[-10:] if a.level == "warning"]
        
        if critical_alerts:
            status = "critical"
            message = f"Sistema com {len(critical_alerts)} alertas críticos"
        elif warning_alerts:
            status = "warning"
            message = f"Sistema com {len(warning_alerts)} avisos"
        else:
            status = "healthy"
            message = "Sistema funcionando normalmente"
        
        # GEM process info
        gem_info = {}
        if self.gem_process:
            try:
                gem_info = {
                    "cpu_percent": self.gem_process.cpu_percent(),
                    "memory_mb": self.gem_process.memory_info().rss / 1024 / 1024,
                    "uptime_seconds": time.time() - self.gem_start_time
                }
            except Exception as e:
                self.logger.warning(f"Could not get GEM process info: {e}")
        
        return {
            "status": status,
            "message": message,
            "metrics": latest_metrics.to_dict(),
            "gem_process": gem_info,
            "recent_alerts": [a.to_dict() for a in self.alerts_history[-5:]],
            "uptime": time.time() - self.gem_start_time
        }
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for the last N hours."""
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {"error": "No metrics available for the specified period"}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_usage for m in recent_metrics) / len(recent_metrics)
        
        # Calculate peaks
        max_cpu = max(m.cpu_percent for m in recent_metrics)
        max_memory = max(m.memory_percent for m in recent_metrics)
        
        return {
            "period_hours": hours,
            "samples_count": len(recent_metrics),
            "averages": {
                "cpu_percent": round(avg_cpu, 1),
                "memory_percent": round(avg_memory, 1),
                "disk_usage": round(avg_disk, 1)
            },
            "peaks": {
                "cpu_percent": round(max_cpu, 1),
                "memory_percent": round(max_memory, 1)
            },
            "alerts_count": len([a for a in self.alerts_history if a.timestamp >= cutoff_time])
        }
    
    def _save_metrics_to_file(self):
        """Save metrics history to file."""
        try:
            metrics_file = self.data_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
            
            # Convert metrics to serializable format
            data = {
                "timestamp": time.time(),
                "metrics": [m.to_dict() for m in self.metrics_history[-100:]],  # Last 100 entries
                "alerts": [a.to_dict() for a in self.alerts_history[-50:]]  # Last 50 alerts
            }
            
            with open(metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Metrics saved to {metrics_file}")
        
        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")
    
    def load_metrics_from_file(self, date: Optional[str] = None):
        """Load metrics from file."""
        try:
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            
            metrics_file = self.data_dir / f"metrics_{date}.json"
            
            if not metrics_file.exists():
                self.logger.warning(f"Metrics file not found: {metrics_file}")
                return
            
            with open(metrics_file, 'r') as f:
                data = json.load(f)
            
            # Load metrics
            for metric_data in data.get('metrics', []):
                metrics = SystemMetrics()
                metrics.timestamp = metric_data['timestamp']
                metrics.cpu_percent = metric_data['cpu_percent']
                metrics.memory_percent = metric_data['memory_percent']
                metrics.memory_available = metric_data['memory_available']
                metrics.disk_usage = metric_data['disk_usage']
                metrics.network_sent = metric_data['network_sent']
                metrics.network_recv = metric_data['network_recv']
                metrics.temperature = metric_data.get('temperature')
                metrics.battery_percent = metric_data.get('battery_percent')
                metrics.processes_count = metric_data['processes_count']
                
                self.metrics_history.append(metrics)
            
            # Load alerts
            for alert_data in data.get('alerts', []):
                alert = HealthAlert(
                    alert_data['level'],
                    alert_data['message'],
                    alert_data['metric'],
                    alert_data['value'],
                    alert_data['threshold']
                )
                alert.timestamp = alert_data['timestamp']
                self.alerts_history.append(alert)
            
            self.logger.info(f"Loaded {len(data.get('metrics', []))} metrics and {len(data.get('alerts', []))} alerts")
        
        except Exception as e:
            self.logger.error(f"Error loading metrics: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get static system information."""
        try:
            return {
                "platform": psutil.LINUX if hasattr(psutil, 'LINUX') else "unknown",
                "cpu_count": psutil.cpu_count(),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total,
                "boot_time": psutil.boot_time(),
                "python_version": f"{psutil.version_info.major}.{psutil.version_info.minor}.{psutil.version_info.micro}"
            }
        
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}
    
    def cleanup_old_files(self, days: int = 7):
        """Clean up old monitoring files."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for file_path in self.data_dir.glob("metrics_*.json"):
                try:
                    # Extract date from filename
                    date_str = file_path.stem.split('_')[1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        file_path.unlink()
                        self.logger.info(f"Deleted old metrics file: {file_path}")
                
                except (ValueError, IndexError):
                    continue  # Skip files with invalid names
        
        except Exception as e:
            self.logger.error(f"Error cleaning up old files: {e}")