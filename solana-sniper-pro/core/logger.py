"""
Logging & Debugging System für Solana Sniper Pro.

Bietet strukturierte Logging-Funktionalität mit:
- Mehreren Log-Levels (ERROR, WARN, INFO, DEBUG)
- Rotierenden Log-Dateien (max 10MB)
- JSON-Format für einfaches Parsing
- Kategorisierung (TRADE, SECURITY, RPC, ERROR, PERFORMANCE)
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any


class JSONFormatter(logging.Formatter):
    """Formatiert Log-Einträge als JSON für einfaches Parsing."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formattiert einen Log-Eintrag als JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "category": getattr(record, 'category', 'GENERAL'),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Füge Exception-Details hinzu falls vorhanden
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Füge zusätzliche Felder hinzu
        if hasattr(record, 'extra_data'):
            log_entry["data"] = record.extra_data
        
        return json.dumps(log_entry)


class CategoryFilter(logging.Filter):
    """Filtert Log-Einträge nach Kategorie."""
    
    def __init__(self, category: str):
        """Initialisiert den Filter mit einer Kategorie."""
        super().__init__()
        self.category = category
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filtert Einträge basierend auf der Kategorie."""
        record_category = getattr(record, 'category', 'GENERAL')
        return record_category == self.category if self.category else True


class Logger:
    """Haupt-Logger-Klasse für Solana Sniper Pro."""
    
    LOG_CATEGORIES = {
        'TRADE': 'Trade-Aktionen (Kauf/Verkauf)',
        'SECURITY': 'Sicherheitschecks (Rug-Pull, Honeypot)',
        'RPC': 'RPC-Calls und Responses',
        'ERROR': 'Exceptions und Crashes',
        'PERFORMANCE': 'P&L-Updates und Performance',
        'HEALTH': 'Health-Monitoring',
        'TELEGRAM': 'Telegram-Bot-Aktivitäten',
        'GENERAL': 'Allgemeine Logs'
    }
    
    def __init__(
        self, 
        log_dir: str = "logs",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True
    ):
        """
        Initialisiert den Logger.
        
        Args:
            log_dir: Verzeichnis für Log-Dateien
            max_file_size: Maximale Größe pro Log-Datei in Bytes
            backup_count: Anzahl der zu behaltenden Backup-Dateien
            console_output: Ob Logs auch in der Konsole ausgegeben werden sollen
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.console_output = console_output
        
        # Haupt-Logger erstellen
        self.logger = logging.getLogger("solana_sniper_pro")
        self.logger.setLevel(logging.DEBUG)
        
        # Handler einrichten
        self._setup_file_handler()
        if console_output:
            self._setup_console_handler()
        
        # Kategorie-spezifische Logger
        self.category_loggers: Dict[str, logging.Logger] = {}
        for category in self.LOG_CATEGORIES.keys():
            self.category_loggers[category] = self._create_category_logger(category)
    
    def _setup_file_handler(self) -> None:
        """Richtet den rotierenden File-Handler ein."""
        file_handler = RotatingFileHandler(
            self.log_dir / "bot.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)
    
    def _setup_console_handler(self) -> None:
        """Richtet den Console-Handler ein."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(category)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def _create_category_logger(self, category: str) -> logging.Logger:
        """Erstellt einen Logger für eine spezifische Kategorie."""
        category_logger = logging.getLogger(f"solana_sniper_pro.{category}")
        category_logger.setLevel(logging.DEBUG)
        category_logger.propagate = False
        
        # Gleiche Handler wie Haupt-Logger
        for handler in self.logger.handlers:
            category_logger.addHandler(handler)
        
        return category_logger
    
    def _log(
        self, 
        level: int, 
        message: str, 
        category: str = "GENERAL",
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> None:
        """
        Schreibt einen Log-Eintrag.
        
        Args:
            level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Die zu loggende Nachricht
            category: Kategorie des Logs (TRADE, SECURITY, etc.)
            extra_data: Zusätzliche Daten als Dictionary
            exc_info: Exception-Informationen falls vorhanden
        """
        logger = self.category_loggers.get(category, self.logger)
        
        # Extra-Daten vorbereiten
        extra = {"category": category}
        if extra_data:
            extra["extra_data"] = extra_data
        
        # Log-Eintrag erstellen
        logger.log(level, message, extra=extra, exc_info=exc_info)
    
    def debug(self, message: str, category: str = "GENERAL", **kwargs) -> None:
        """Loggt eine DEBUG-Nachricht."""
        self._log(logging.DEBUG, message, category, **kwargs)
    
    def info(self, message: str, category: str = "GENERAL", **kwargs) -> None:
        """Loggt eine INFO-Nachricht."""
        self._log(logging.INFO, message, category, **kwargs)
    
    def warning(self, message: str, category: str = "GENERAL", **kwargs) -> None:
        """Loggt eine WARNING-Nachricht."""
        self._log(logging.WARNING, message, category, **kwargs)
    
    def error(self, message: str, category: str = "GENERAL", **kwargs) -> None:
        """Loggt eine ERROR-Nachricht."""
        self._log(logging.ERROR, message, category, **kwargs)
    
    def critical(self, message: str, category: str = "GENERAL", **kwargs) -> None:
        """Loggt eine CRITICAL-Nachricht."""
        self._log(logging.CRITICAL, message, category, **kwargs)
    
    def trade(self, message: str, **kwargs) -> None:
        """Loggt eine Trade-bezogene Nachricht."""
        self.info(message, category="TRADE", **kwargs)
    
    def security(self, message: str, **kwargs) -> None:
        """Loggt eine Sicherheits-bezogene Nachricht."""
        self.info(message, category="SECURITY", **kwargs)
    
    def rpc(self, message: str, **kwargs) -> None:
        """Loggt eine RPC-bezogene Nachricht."""
        self.debug(message, category="RPC", **kwargs)
    
    def performance(self, message: str, **kwargs) -> None:
        """Loggt eine Performance-bezogene Nachricht."""
        self.info(message, category="PERFORMANCE", **kwargs)
    
    def get_logs(
        self, 
        category: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Liest Log-Einträge aus der aktuellen Log-Datei.
        
        Args:
            category: Filter nach Kategorie
            level: Filter nach Log-Level
            limit: Maximale Anzahl zurückgegebener Einträge
        
        Returns:
            Liste von Log-Einträgen als Dictionaries
        """
        logs = []
        log_file = self.log_dir / "bot.log"
        
        if not log_file.exists():
            return logs
        
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # Filter anwenden
                    if category and entry.get('category') != category:
                        continue
                    if level and entry.get('level') != level:
                        continue
                    
                    logs.append(entry)
                    
                    if len(logs) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
        
        return logs


# Globale Logger-Instanz
_logger: Optional[Logger] = None


def get_logger(category: str = "GENERAL") -> Logger:
    """
    Gibt die globale Logger-Instanz zurück oder erstellt eine neue mit Kategorie.
    
    Args:
        category: Log-Kategorie (optional)
    
    Returns:
        Logger-Instanz
    """
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def initialize_logger(log_dir: str = "logs", console_output: bool = True) -> Logger:
    """
    Initialisiert den globalen Logger.
    
    Args:
        log_dir: Verzeichnis für Log-Dateien
        console_output: Ob Logs in der Konsole ausgegeben werden sollen
    
    Returns:
        Initialisierte Logger-Instanz
    """
    global _logger
    _logger = Logger(log_dir=log_dir, console_output=console_output)
    return _logger


# Convenience-Funktionen für direktes Logging
def debug(message: str, category: str = "GENERAL", **kwargs) -> None:
    """Loggt eine DEBUG-Nachricht."""
    get_logger().debug(message, category, **kwargs)


def info(message: str, category: str = "GENERAL", **kwargs) -> None:
    """Loggt eine INFO-Nachricht."""
    get_logger().info(message, category, **kwargs)


def warning(message: str, category: str = "GENERAL", **kwargs) -> None:
    """Loggt eine WARNING-Nachricht."""
    get_logger().warning(message, category, **kwargs)


def error(message: str, category: str = "GENERAL", **kwargs) -> None:
    """Loggt eine ERROR-Nachricht."""
    get_logger().error(message, category, **kwargs)


def critical(message: str, category: str = "GENERAL", **kwargs) -> None:
    """Loggt eine CRITICAL-Nachricht."""
    get_logger().critical(message, category, **kwargs)
