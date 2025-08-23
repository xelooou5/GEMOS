#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Smart Health System
AI-powered health monitoring and predictive wellness
"""

import asyncio
import json
import logging
import numpy as np
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3


@dataclass
class HealthReading:
    """Health sensor reading."""
    sensor_type: str = ""
    value: float = 0.0
    unit: str = ""
    timestamp: str = ""
    confidence: float = 1.0
    source: str = "manual"  # manual, wearable, sensor


@dataclass
class HealthAlert:
    """Health alert with severity and recommendations."""
    alert_type: str = ""
    severity: str = "info"  # info, warning, critical, emergency
    message: str = ""
    recommendations: List[str] = None
    timestamp: str = ""
    acknowledged: bool = False
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class WearableIntegration:
    """Integration with wearable devices and health sensors."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.connected_devices = {}
        self.supported_devices = [
            "apple_watch", "fitbit", "garmin", "samsung_health",
            "google_fit", "polar", "withings", "oura_ring"
        ]
    
    async def discover_devices(self) -> List[str]:
        """Discover available health devices."""
        # Simulate device discovery
        # In real implementation, this would use Bluetooth/WiFi scanning
        
        discovered = []
        
        # Check for common health apps/APIs
        health_sources = {
            "apple_health": self._check_apple_health,
            "google_fit": self._check_google_fit,
            "samsung_health": self._check_samsung_health
        }
        
        for source, check_func in health_sources.items():
            if await check_func():
                discovered.append(source)
        
        self.logger.info(f"Discovered health sources: {discovered}")
        return discovered
    
    async def _check_apple_health(self) -> bool:
        """Check if Apple Health is available."""
        # Simulate Apple Health availability check
        return False  # Would check for HealthKit availability
    
    async def _check_google_fit(self) -> bool:
        """Check if Google Fit is available."""
        # Simulate Google Fit availability check
        return False  # Would check for Google Fit API access
    
    async def _check_samsung_health(self) -> bool:
        """Check if Samsung Health is available."""
        # Simulate Samsung Health availability check
        return False  # Would check for Samsung Health SDK
    
    async def connect_device(self, device_type: str) -> bool:
        """Connect to a health device."""
        try:
            if device_type in self.supported_devices:
                # Simulate device connection
                self.connected_devices[device_type] = {
                    "connected": True,
                    "last_sync": datetime.now().isoformat(),
                    "battery_level": 85,
                    "signal_strength": "good"
                }
                
                self.logger.info(f"Connected to {device_type}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Device connection error: {e}")
            return False
    
    async def sync_health_data(self, device_type: str) -> List[HealthReading]:
        """Sync health data from connected device."""
        if device_type not in self.connected_devices:
            return []
        
        # Simulate health data sync
        readings = []
        current_time = datetime.now()
        
        # Generate simulated health data
        if device_type in ["apple_watch", "fitbit", "garmin"]:
            readings.extend([
                HealthReading(
                    sensor_type="heart_rate",
                    value=72.0 + np.random.normal(0, 5),
                    unit="bpm",
                    timestamp=current_time.isoformat(),
                    source=device_type
                ),
                HealthReading(
                    sensor_type="steps",
                    value=8500 + np.random.randint(-1000, 1000),
                    unit="steps",
                    timestamp=current_time.isoformat(),
                    source=device_type
                ),
                HealthReading(
                    sensor_type="sleep_hours",
                    value=7.5 + np.random.normal(0, 1),
                    unit="hours",
                    timestamp=(current_time - timedelta(hours=8)).isoformat(),
                    source=device_type
                )
            ])
        
        self.connected_devices[device_type]["last_sync"] = current_time.isoformat()
        return readings


class HealthAnalytics:
    """AI-powered health analytics and predictions."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.health_patterns = {}
        self.baseline_values = {}
    
    async def analyze_health_trends(self, readings: List[HealthReading], 
                                  days: int = 30) -> Dict[str, Any]:
        """Analyze health trends over time."""
        
        if not readings:
            return {"error": "No health data available"}
        
        # Group readings by sensor type
        sensor_data = {}
        for reading in readings:
            if reading.sensor_type not in sensor_data:
                sensor_data[reading.sensor_type] = []
            sensor_data[reading.sensor_type].append(reading)
        
        trends = {}
        
        for sensor_type, data in sensor_data.items():
            if len(data) < 2:
                continue
            
            values = [r.value for r in data]
            timestamps = [datetime.fromisoformat(r.timestamp) for r in data]
            
            # Calculate trend
            if len(values) >= 7:  # Need at least a week of data
                recent_avg = np.mean(values[-7:])
                older_avg = np.mean(values[:-7]) if len(values) > 7 else np.mean(values)
                
                trend_direction = "stable"
                if recent_avg > older_avg * 1.05:
                    trend_direction = "increasing"
                elif recent_avg < older_avg * 0.95:
                    trend_direction = "decreasing"
                
                trends[sensor_type] = {
                    "current_average": recent_avg,
                    "trend_direction": trend_direction,
                    "change_percentage": ((recent_avg - older_avg) / older_avg) * 100,
                    "data_points": len(values),
                    "last_reading": values[-1],
                    "min_value": min(values),
                    "max_value": max(values)
                }
        
        return trends
    
    async def predict_health_risks(self, user_profile: Dict[str, Any], 
                                 recent_readings: List[HealthReading]) -> List[HealthAlert]:
        """Predict potential health risks based on data patterns."""
        
        alerts = []
        
        # Analyze heart rate patterns
        hr_readings = [r for r in recent_readings if r.sensor_type == "heart_rate"]
        if hr_readings:
            avg_hr = np.mean([r.value for r in hr_readings])
            
            if avg_hr > 100:
                alerts.append(HealthAlert(
                    alert_type="elevated_heart_rate",
                    severity="warning",
                    message=f"Frequência cardíaca média elevada: {avg_hr:.0f} bpm",
                    recommendations=[
                        "Considere reduzir atividades intensas",
                        "Pratique técnicas de relaxamento",
                        "Consulte um médico se persistir"
                    ],
                    timestamp=datetime.now().isoformat()
                ))
            elif avg_hr < 50:
                alerts.append(HealthAlert(
                    alert_type="low_heart_rate",
                    severity="info",
                    message=f"Frequência cardíaca baixa: {avg_hr:.0f} bpm",
                    recommendations=[
                        "Pode indicar boa forma física",
                        "Monitore se há sintomas associados",
                        "Consulte médico se houver tontura"
                    ],
                    timestamp=datetime.now().isoformat()
                ))
        
        # Analyze sleep patterns
        sleep_readings = [r for r in recent_readings if r.sensor_type == "sleep_hours"]
        if sleep_readings:
            avg_sleep = np.mean([r.value for r in sleep_readings])
            
            if avg_sleep < 6:
                alerts.append(HealthAlert(
                    alert_type="insufficient_sleep",
                    severity="warning",
                    message=f"Sono insuficiente: {avg_sleep:.1f} horas por noite",
                    recommendations=[
                        "Tente dormir pelo menos 7-8 horas",
                        "Estabeleça uma rotina de sono",
                        "Evite telas antes de dormir"
                    ],
                    timestamp=datetime.now().isoformat()
                ))
        
        # Analyze activity levels
        step_readings = [r for r in recent_readings if r.sensor_type == "steps"]
        if step_readings:
            avg_steps = np.mean([r.value for r in step_readings])
            
            if avg_steps < 5000:
                alerts.append(HealthAlert(
                    alert_type="low_activity",
                    severity="info",
                    message=f"Atividade física baixa: {avg_steps:.0f} passos/dia",
                    recommendations=[
                        "Tente caminhar mais durante o dia",
                        "Use escadas em vez de elevador",
                        "Faça pausas ativas no trabalho"
                    ],
                    timestamp=datetime.now().isoformat()
                ))
        
        return alerts
    
    async def generate_health_insights(self, trends: Dict[str, Any]) -> List[str]:
        """Generate personalized health insights."""
        
        insights = []
        
        for sensor_type, trend_data in trends.items():
            if sensor_type == "heart_rate":
                if trend_data["trend_direction"] == "increasing":
                    insights.append(
                        f"Sua frequência cardíaca tem aumentado {trend_data['change_percentage']:.1f}% "
                        "nas últimas semanas. Considere verificar seus níveis de estresse."
                    )
                elif trend_data["trend_direction"] == "decreasing":
                    insights.append(
                        f"Sua frequência cardíaca em repouso melhorou {abs(trend_data['change_percentage']):.1f}%. "
                        "Isso pode indicar melhora no condicionamento físico!"
                    )
            
            elif sensor_type == "steps":
                if trend_data["trend_direction"] == "increasing":
                    insights.append(
                        f"Parabéns! Você aumentou sua atividade física em {trend_data['change_percentage']:.1f}%. "
                        "Continue assim!"
                    )
                elif trend_data["trend_direction"] == "decreasing":
                    insights.append(
                        f"Sua atividade física diminuiu {abs(trend_data['change_percentage']):.1f}%. "
                        "Que tal definir uma meta de caminhada diária?"
                    )
            
            elif sensor_type == "sleep_hours":
                if trend_data["current_average"] >= 7:
                    insights.append(
                        f"Excelente! Você está dormindo {trend_data['current_average']:.1f} horas por noite. "
                        "Sono adequado é fundamental para a saúde."
                    )
                else:
                    insights.append(
                        f"Você tem dormido apenas {trend_data['current_average']:.1f} horas por noite. "
                        "Tente melhorar sua higiene do sono."
                    )
        
        return insights


class MedicationIntelligence:
    """Intelligent medication management with drug interactions."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.drug_database = self._load_drug_database()
    
    def _load_drug_database(self) -> Dict[str, Any]:
        """Load drug interaction database."""
        # Simplified drug database
        return {
            "aspirina": {
                "interactions": ["varfarina", "ibuprofeno"],
                "side_effects": ["dor de estômago", "sangramento"],
                "contraindications": ["úlcera", "alergia a salicilatos"]
            },
            "paracetamol": {
                "interactions": ["álcool", "varfarina"],
                "side_effects": ["náusea", "dor de cabeça"],
                "contraindications": ["doença hepática grave"]
            },
            "ibuprofeno": {
                "interactions": ["aspirina", "varfarina", "ACE inibidores"],
                "side_effects": ["dor de estômago", "tontura"],
                "contraindications": ["úlcera", "doença renal"]
            }
        }
    
    async def check_drug_interactions(self, medications: List[str]) -> List[str]:
        """Check for drug interactions."""
        interactions = []
        
        for i, med1 in enumerate(medications):
            med1_lower = med1.lower()
            if med1_lower in self.drug_database:
                for j, med2 in enumerate(medications[i+1:], i+1):
                    med2_lower = med2.lower()
                    if med2_lower in self.drug_database[med1_lower]["interactions"]:
                        interactions.append(
                            f"⚠️ Possível interação entre {med1} e {med2}. "
                            "Consulte seu médico."
                        )
        
        return interactions
    
    async def get_medication_info(self, medication: str) -> Dict[str, Any]:
        """Get detailed medication information."""
        med_lower = medication.lower()
        
        if med_lower in self.drug_database:
            return {
                "name": medication,
                "interactions": self.drug_database[med_lower]["interactions"],
                "side_effects": self.drug_database[med_lower]["side_effects"],
                "contraindications": self.drug_database[med_lower]["contraindications"]
            }
        
        return {"name": medication, "info": "Informações não disponíveis na base de dados local"}


class SmartHealthSystem:
    """Comprehensive smart health system."""
    
    def __init__(self, gem_assistant, logger: Optional[logging.Logger] = None):
        self.gem = gem_assistant
        self.logger = logger or logging.getLogger("SmartHealthSystem")
        
        # Initialize components
        self.wearable_integration = WearableIntegration(self.logger)
        self.health_analytics = HealthAnalytics(self.logger)
        self.medication_intelligence = MedicationIntelligence(self.logger)
        
        # Health database
        db_path = Path.home() / ".gem" / "data" / "smart_health.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        
        # Health monitoring state
        self.monitoring_active = False
        self.connected_devices = []
        self.health_alerts = []
        
        self._init_health_database()
    
    def _init_health_database(self):
        """Initialize health database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_readings (
                    id INTEGER PRIMARY KEY,
                    sensor_type TEXT,
                    value REAL,
                    unit TEXT,
                    timestamp TEXT,
                    confidence REAL,
                    source TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_alerts (
                    id INTEGER PRIMARY KEY,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    recommendations TEXT,
                    timestamp TEXT,
                    acknowledged BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_goals (
                    id INTEGER PRIMARY KEY,
                    goal_type TEXT,
                    target_value REAL,
                    current_value REAL,
                    unit TEXT,
                    deadline TEXT,
                    achieved BOOLEAN DEFAULT 0
                )
            ''')
            
            conn.commit()
    
    async def initialize(self):
        """Initialize smart health system."""
        self.logger.info("Initializing Smart Health System...")
        
        # Discover available health devices
        devices = await self.wearable_integration.discover_devices()
        self.logger.info(f"Found {len(devices)} health data sources")
        
        # Start health monitoring
        await self.start_health_monitoring()
        
        self.logger.info("Smart Health System initialized!")
    
    async def start_health_monitoring(self):
        """Start continuous health monitoring."""
        self.monitoring_active = True
        
        # Start monitoring loop
        asyncio.create_task(self._health_monitoring_loop())
        
        return "Monitoramento de saúde inteligente ativado!"
    
    async def _health_monitoring_loop(self):
        """Main health monitoring loop."""
        while self.monitoring_active:
            try:
                # Sync data from connected devices
                all_readings = []
                for device in self.connected_devices:
                    readings = await self.wearable_integration.sync_health_data(device)
                    all_readings.extend(readings)
                
                # Store readings in database
                if all_readings:
                    await self._store_health_readings(all_readings)
                
                # Analyze for health risks
                alerts = await self.health_analytics.predict_health_risks({}, all_readings)
                
                # Process new alerts
                for alert in alerts:
                    await self._process_health_alert(alert)
                
                # Wait before next monitoring cycle
                await asyncio.sleep(300)  # Check every 5 minutes
            
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(600)  # Wait longer on error
    
    async def _store_health_readings(self, readings: List[HealthReading]):
        """Store health readings in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for reading in readings:
                    cursor.execute('''
                        INSERT INTO health_readings 
                        (sensor_type, value, unit, timestamp, confidence, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        reading.sensor_type, reading.value, reading.unit,
                        reading.timestamp, reading.confidence, reading.source
                    ))
                
                conn.commit()
        
        except Exception as e:
            self.logger.error(f"Error storing health readings: {e}")
    
    async def _process_health_alert(self, alert: HealthAlert):
        """Process and potentially notify about health alert."""
        
        # Store alert in database
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO health_alerts 
                    (alert_type, severity, message, recommendations, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    alert.alert_type, alert.severity, alert.message,
                    json.dumps(alert.recommendations), alert.timestamp
                ))
                conn.commit()
        
        except Exception as e:
            self.logger.error(f"Error storing health alert: {e}")
        
        # Notify user if critical
        if alert.severity in ["critical", "emergency"]:
            if self.gem.tts_module:
                await self.gem.tts_module.speak(
                    f"Alerta de saúde {alert.severity}: {alert.message}"
                )
        
        self.health_alerts.append(alert)
    
    async def get_health_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive health dashboard."""
        try:
            # Get recent readings
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT sensor_type, value, unit, timestamp, source
                    FROM health_readings 
                    WHERE timestamp >= datetime('now', '-7 days')
                    ORDER BY timestamp DESC
                ''')
                
                readings = []
                for row in cursor.fetchall():
                    readings.append(HealthReading(
                        sensor_type=row[0], value=row[1], unit=row[2],
                        timestamp=row[3], source=row[4]
                    ))
            
            # Analyze trends
            trends = await self.health_analytics.analyze_health_trends(readings)
            
            # Generate insights
            insights = await self.health_analytics.generate_health_insights(trends)
            
            # Get active alerts
            active_alerts = [a for a in self.health_alerts if not a.acknowledged]
            
            return {
                "monitoring_active": self.monitoring_active,
                "connected_devices": len(self.connected_devices),
                "recent_readings_count": len(readings),
                "health_trends": trends,
                "health_insights": insights,
                "active_alerts": len(active_alerts),
                "last_sync": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error generating health dashboard: {e}")
            return {"error": "Erro ao gerar dashboard de saúde"}
    
    async def connect_health_device(self, device_type: str) -> str:
        """Connect to a health monitoring device."""
        success = await self.wearable_integration.connect_device(device_type)
        
        if success:
            self.connected_devices.append(device_type)
            return f"Dispositivo {device_type} conectado com sucesso!"
        else:
            return f"Falha ao conectar com {device_type}"
    
    async def set_health_goal(self, goal_type: str, target_value: float, 
                            unit: str, deadline: str = None) -> str:
        """Set a health goal."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO health_goals (goal_type, target_value, unit, deadline)
                    VALUES (?, ?, ?, ?)
                ''', (goal_type, target_value, unit, deadline))
                conn.commit()
            
            return f"Meta de saúde definida: {goal_type} = {target_value} {unit}"
        
        except Exception as e:
            self.logger.error(f"Error setting health goal: {e}")
            return "Erro ao definir meta de saúde"
    
    async def check_medication_safety(self, medications: List[str]) -> str:
        """Check medication safety and interactions."""
        
        # Check drug interactions
        interactions = await self.medication_intelligence.check_drug_interactions(medications)
        
        if interactions:
            safety_report = "⚠️ VERIFICAÇÃO DE MEDICAMENTOS ⚠️\n\n"
            safety_report += "\n".join(interactions)
            safety_report += "\n\nRecomendação: Consulte seu médico ou farmacêutico."
        else:
            safety_report = "✅ Nenhuma interação medicamentosa conhecida detectada."
        
        return safety_report
    
    async def emergency_health_protocol(self) -> str:
        """Activate emergency health protocol."""
        
        emergency_info = [
            "🚨 PROTOCOLO DE EMERGÊNCIA ATIVADO 🚨",
            "",
            "Informações médicas importantes:",
            "- Alergias conhecidas: [Configurar no perfil]",
            "- Medicamentos atuais: [Verificar lista]",
            "- Condições médicas: [Atualizar perfil]",
            "",
            "Contatos de emergência:",
            "- SAMU: 192",
            "- Bombeiros: 193",
            "- Polícia: 190",
            "",
            "Diga 'CHAMAR EMERGÊNCIA' para assistência imediata."
        ]
        
        # Speak emergency info
        if self.gem.tts_module:
            await self.gem.tts_module.speak(
                "Protocolo de emergência ativado. Informações médicas importantes disponíveis."
            )
        
        return "\n".join(emergency_info)