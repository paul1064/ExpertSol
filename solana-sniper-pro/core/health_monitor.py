"""
Health Monitoring System für Solana Sniper Pro.

Bietet:
- Heartbeat-Funktionalität für Monitoring-Services
- Resource-Monitoring (CPU, RAM, Disk)
- Health-Check Endpoints
- Auto-Benachrichtigung bei Problemen
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import json

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from core.logger import get_logger

logger = get_logger()


class HealthStatus:
    """Repräsentiert den Gesundheitsstatus des Bots."""
    
    def __init__(
        self,
        is_healthy: bool = True,
        last_heartbeat: Optional[datetime] = None,
        rpc_status: str = "unknown",
        wallet_balance: Optional[float] = None,
        open_positions: int = 0,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0,
        disk_percent: float = 0.0,
        uptime_seconds: float = 0.0,
        errors: Optional[List[str]] = None
    ):
        """Initialisiert den HealthStatus."""
        self.is_healthy = is_healthy
        self.last_heartbeat = last_heartbeat or datetime.utcnow()
        self.rpc_status = rpc_status
        self.wallet_balance = wallet_balance
        self.open_positions = open_positions
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.disk_percent = disk_percent
        self.uptime_seconds = uptime_seconds
        self.errors = errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert den Status in ein Dictionary."""
        return {
            "is_healthy": self.is_healthy,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "rpc_status": self.rpc_status,
            "wallet_balance": self.wallet_balance,
            "open_positions": self.open_positions,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "uptime_seconds": self.uptime_seconds,
            "errors": self.errors,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def to_json(self) -> str:
        """Konvertiert den Status in JSON."""
        return json.dumps(self.to_dict(), indent=2)


class HealthMonitor:
    """
    Überwacht die Gesundheit des Bots und sendet Heartbeats.
    
    Features:
    - Heartbeat alle X Minuten an Monitoring-Service
    - Resource-Monitoring (CPU, RAM, Disk)
    - Health-Check Status
    - Benachrichtigung bei Problemen
    """
    
    def __init__(
        self,
        heartbeat_url: Optional[str] = None,
        heartbeat_interval: int = 300,  # 5 Minuten
        discord_webhook: Optional[str] = None,
        max_cpu_percent: float = 90.0,
        max_memory_percent: float = 85.0,
        max_disk_percent: float = 90.0
    ):
        """
        Initialisiert den HealthMonitor.
        
        Args:
            heartbeat_url: URL für Heartbeat-Pings (z.B. Healthchecks.io)
            heartbeat_interval: Interval zwischen Heartbeats in Sekunden
            discord_webhook: Discord Webhook URL für Benachrichtigungen
            max_cpu_percent: Maximal erlaubte CPU-Auslastung
            max_memory_percent: Maximal erlaubte RAM-Auslastung
            max_disk_percent: Maximal erlaubte Disk-Auslastung
        """
        self.heartbeat_url = heartbeat_url
        self.heartbeat_interval = heartbeat_interval
        self.discord_webhook = discord_webhook
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_disk_percent = max_disk_percent
        
        self.start_time = datetime.utcnow()
        self.last_heartbeat_time: Optional[datetime] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.stop_heartbeat = threading.Event()
        
        # Callbacks für Health-Checks
        self.rpc_check_callback: Optional[Callable] = None
        self.wallet_check_callback: Optional[Callable] = None
        self.positions_check_callback: Optional[Callable] = None
        
        # Error-Tracking
        self.error_log: List[str] = []
        self.max_errors = 100
        
        logger.info("HealthMonitor initialisiert", category="HEALTH")
    
    def set_rpc_check_callback(self, callback: Callable) -> None:
        """Setzt einen Callback für RPC-Status-Checks."""
        self.rpc_check_callback = callback
    
    def set_wallet_check_callback(self, callback: Callable) -> None:
        """Setzt einen Callback für Wallet-Balance-Checks."""
        self.wallet_check_callback = callback
    
    def set_positions_check_callback(self, callback: Callable) -> None:
        """Setzt einen Callback für Open-Positions-Checks."""
        self.positions_check_callback = callback
    
    def start(self) -> None:
        """Startet den HealthMonitor."""
        logger.info("HealthMonitor gestartet", category="HEALTH")
        self._start_heartbeat_thread()
    
    def stop(self) -> None:
        """Stoppt den HealthMonitor."""
        logger.info("HealthMonitor gestoppt", category="HEALTH")
        self.stop_heartbeat.set()
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
    
    def _start_heartbeat_thread(self) -> None:
        """Startet den Heartbeat-Thread."""
        if not self.heartbeat_url:
            logger.warning(
                "Keine Heartbeat-URL konfiguriert, Heartbeat deaktiviert",
                category="HEALTH"
            )
            return
        
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat-Schleife im Hintergrund-Thread."""
        while not self.stop_heartbeat.is_set():
            try:
                self.send_heartbeat()
            except Exception as e:
                logger.error(
                    f"Heartbeat fehlgeschlagen: {str(e)}",
                    category="HEALTH",
                    exc_info=e
                )
            
            # Warte bis zum nächsten Heartbeat
            self.stop_heartbeat.wait(self.heartbeat_interval)
    
    def send_heartbeat(self) -> bool:
        """
        Sendet einen Heartbeat an den Monitoring-Service.
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.heartbeat_url or not REQUESTS_AVAILABLE:
            return False
        
        try:
            response = requests.get(self.heartbeat_url, timeout=10)
            if response.status_code == 200:
                self.last_heartbeat_time = datetime.utcnow()
                logger.debug("Heartbeat erfolgreich gesendet", category="HEALTH")
                return True
            else:
                logger.warning(
                    f"Heartbeat返回 Status Code {response.status_code}",
                    category="HEALTH"
                )
                return False
        except Exception as e:
            logger.error(
                f"Heartbeat Request fehlgeschlagen: {str(e)}",
                category="HEALTH",
                exc_info=e
            )
            return False
    
    def get_resource_usage(self) -> Dict[str, float]:
        """
        Ermittelt die aktuelle Resource-Auslastung.
        
        Returns:
            Dictionary mit CPU, Memory und Disk Auslastung
        """
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    
    def check_resources(self) -> List[str]:
        """
        Prüft die Resource-Auslastung auf Probleme.
        
        Returns:
            Liste von Warning-Messages bei Problemen
        """
        warnings = []
        usage = self.get_resource_usage()
        
        if usage["cpu_percent"] > self.max_cpu_percent:
            warning = f"CPU-Auslastung zu hoch: {usage['cpu_percent']}%"
            warnings.append(warning)
            logger.warning(warning, category="HEALTH")
        
        if usage["memory_percent"] > self.max_memory_percent:
            warning = f"RAM-Auslastung zu hoch: {usage['memory_percent']}%"
            warnings.append(warning)
            logger.warning(warning, category="HEALTH")
        
        if usage["disk_percent"] > self.max_disk_percent:
            warning = f"Disk-Auslastung zu hoch: {usage['disk_percent']}%"
            warnings.append(warning)
            logger.warning(warning, category="HEALTH")
        
        return warnings
    
    def get_health_status(self) -> HealthStatus:
        """
        Ermittelt den aktuellen Health-Status.
        
        Returns:
            HealthStatus-Objekt
        """
        errors = self.error_log[-10:]  # Letzte 10 Fehler
        is_healthy = len(errors) == 0
        resource_warnings = self.check_resources()
        
        # Callbacks aufrufen für detaillierte Checks
        rpc_status = "unknown"
        wallet_balance = None
        open_positions = 0
        
        if self.rpc_check_callback:
            try:
                rpc_status = self.rpc_check_callback()
            except Exception as e:
                rpc_status = f"error: {str(e)}"
                errors.append(f"RPC Check failed: {str(e)}")
        
        if self.wallet_check_callback:
            try:
                wallet_balance = self.wallet_check_callback()
            except Exception as e:
                errors.append(f"Wallet Check failed: {str(e)}")
        
        if self.positions_check_callback:
            try:
                open_positions = self.positions_check_callback()
            except Exception as e:
                errors.append(f"Positions Check failed: {str(e)}")
        
        # Gesund wenn keine Errors und keine Resource-Warnings
        is_healthy = len(errors) == 0 and len(resource_warnings) == 0
        
        usage = self.get_resource_usage()
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return HealthStatus(
            is_healthy=is_healthy,
            last_heartbeat=self.last_heartbeat_time,
            rpc_status=rpc_status,
            wallet_balance=wallet_balance,
            open_positions=open_positions,
            cpu_percent=usage["cpu_percent"],
            memory_percent=usage["memory_percent"],
            disk_percent=usage["disk_percent"],
            uptime_seconds=uptime,
            errors=errors
        )
    
    def add_error(self, error_message: str) -> None:
        """Fügt einen Fehler zum Error-Log hinzu."""
        timestamp = datetime.utcnow().isoformat()
        full_error = f"[{timestamp}] {error_message}"
        self.error_log.append(full_error)
        
        # Maximalfehler begrenzen
        if len(self.error_log) > self.max_errors:
            self.error_log = self.error_log[-self.max_errors:]
        
        logger.error(error_message, category="HEALTH")
    
    def send_discord_notification(self, message: str, is_emergency: bool = False) -> bool:
        """
        Sendet eine Benachrichtigung an Discord.
        
        Args:
            message: Die Nachricht
            is_emergency: Ob es eine Emergency-Benachrichtigung ist
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.discord_webhook or not REQUESTS_AVAILABLE:
            return False
        
        try:
            color = 0xff0000 if is_emergency else 0xffa500
            payload = {
                "embeds": [{
                    "title": "🚨 Solana Sniper Pro Alert" if is_emergency else "⚠️ Solana Sniper Pro Warning",
                    "description": message,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {
                        "text": "Solana Sniper Pro Health Monitor"
                    }
                }]
            }
            
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info("Discord-Benachrichtigung gesendet", category="HEALTH")
                return True
            else:
                logger.warning(
                    f"Discord-Benachrichtigung fehlgeschlagen: {response.status_code}",
                    category="HEALTH"
                )
                return False
        except Exception as e:
            logger.error(
                f"Discord-Benachrichtigung fehlgeschlagen: {str(e)}",
                category="HEALTH",
                exc_info=e
            )
            return False
    
    def generate_health_report(self) -> str:
        """
        Generiert einen ausführlichen Health-Report.
        
        Returns:
            Formatierte Report-String
        """
        status = self.get_health_status()
        uptime_str = str(timedelta(seconds=int(status.uptime_seconds)))
        
        report = f"""
╔══════════════════════════════════════════════════╗
║       SOLANA SNIPER PRO - HEALTH REPORT         ║
╠══════════════════════════════════════════════════╣
║ Status: {'✅ HEALTHY' if status.is_healthy else '❌ UNHEALTHY':<42} ║
╠══════════════════════════════════════════════════╣
║ Uptime: {uptime_str:<42} ║
║ Last Heartbeat: {str(status.last_heartbeat):<32} ║
╠══════════════════════════════════════════════════╣
║ RESOURCE USAGE                                  ║
├──────────────────────────────────────────────────┤
║ CPU: {status.cpu_percent:>6.1f}%                                      ║
║ Memory: {status.memory_percent:>6.1f}%                                    ║
║ Disk: {status.disk_percent:>6.1f}%                                      ║
╠══════════════════════════════════════════════════╣
║ BOT STATUS                                      ║
├──────────────────────────────────────────────────┤
║ RPC Status: {status.rpc_status:<36} ║
║ Wallet Balance: {str(status.wallet_balance):>30} ║
║ Open Positions: {status.open_positions:>30} ║
╚══════════════════════════════════════════════════╝
"""
        
        if status.errors:
            report += "\n⚠️ RECENT ERRORS:\n"
            for error in status.errors[-5:]:
                report += f"  - {error}\n"
        
        return report


# Globale HealthMonitor-Instanz
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Gibt die globale HealthMonitor-Instanz zurück."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def initialize_health_monitor(
    heartbeat_url: Optional[str] = None,
    discord_webhook: Optional[str] = None,
    heartbeat_interval: int = 300
) -> HealthMonitor:
    """
    Initialisiert den globalen HealthMonitor.
    
    Args:
        heartbeat_url: URL für Heartbeat-Pings
        discord_webhook: Discord Webhook für Benachrichtigungen
        heartbeat_interval: Interval zwischen Heartbeats in Sekunden
    
    Returns:
        Initialisierte HealthMonitor-Instanz
    """
    global _health_monitor
    _health_monitor = HealthMonitor(
        heartbeat_url=heartbeat_url,
        discord_webhook=discord_webhook,
        heartbeat_interval=heartbeat_interval
    )
    return _health_monitor
