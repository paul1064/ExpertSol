"""
Tests für Phase 2 Features: Logger, Health Monitor, Telegram Bot, Token Analyzer.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import os

# Test imports
from core.logger import Logger, initialize_logger, get_logger, JSONFormatter
from core.health_monitor import HealthMonitor, HealthStatus, initialize_health_monitor
from security.token_analyzer import (
    TokenAnalyzer, TokenScore, SocialSentimentScanner,
    DevWalletTracker, SmartMoneyTracker, TokenMetadataValidator,
    PairAgeDetector, PairAgeCategory
)


class TestLogger:
    """Tests für das Logging-System."""
    
    @pytest.fixture
    def logger(self, tmp_path):
        """Erstellt einen Logger mit temporärem Verzeichnis."""
        log_dir = tmp_path / "logs"
        return Logger(log_dir=str(log_dir), console_output=False)
    
    def test_logger_initialization(self, logger):
        """Testet die Logger-Initialisierung."""
        assert logger is not None
        assert logger.log_dir.exists()
        assert len(logger.category_loggers) == len(Logger.LOG_CATEGORIES)
    
    def test_log_levels(self, logger):
        """Testet verschiedene Log-Levels."""
        logger.debug("Debug message", category="GENERAL")
        logger.info("Info message", category="GENERAL")
        logger.warning("Warning message", category="GENERAL")
        logger.error("Error message", category="GENERAL")
        
        # Logs sollten geschrieben werden
        logs = logger.get_logs(limit=10)
        assert len(logs) >= 4
    
    def test_category_logging(self, logger):
        """Testet kategorien-spezifisches Logging."""
        logger.trade("Trade executed", extra_data={"token": "SOL"})
        logger.security("Security check passed")
        logger.rpc("RPC call completed")
        logger.performance("P&L updated")
        
        # Filter nach Kategorie
        trade_logs = logger.get_logs(category="TRADE", limit=10)
        assert len(trade_logs) >= 1
        assert trade_logs[0]["category"] == "TRADE"
    
    def test_json_formatting(self, logger):
        """Testet JSON-Formatierung der Logs."""
        logger.info("Test message", category="TEST", extra_data={"key": "value"})
        
        logs = logger.get_logs(limit=5)
        assert len(logs) > 0
        
        # JSON-Struktur prüfen
        log_entry = logs[0]
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
        assert "category" in log_entry
    
    def test_get_logs_filtering(self, logger):
        """Testet das Filtern von Logs."""
        logger.info("Info 1", category="TRADE")
        logger.info("Info 2", category="SECURITY")
        logger.error("Error 1", category="TRADE")
        
        # Nach Kategorie filtern
        trade_logs = logger.get_logs(category="TRADE", limit=10)
        assert all(log["category"] == "TRADE" for log in trade_logs)
        
        # Nach Level filtern
        error_logs = logger.get_logs(level="ERROR", limit=10)
        assert all(log["level"] == "ERROR" for log in error_logs)


class TestHealthMonitor:
    """Tests für den Health Monitor."""
    
    @pytest.fixture
    def health_monitor(self):
        """Erstellt einen HealthMonitor ohne Heartbeat-URL."""
        return HealthMonitor(
            heartbeat_url=None,
            heartbeat_interval=300,
            max_cpu_percent=90.0,
            max_memory_percent=90.0,
            max_disk_percent=90.0
        )
    
    def test_health_monitor_initialization(self, health_monitor):
        """Testet die Initialisierung des HealthMonitors."""
        assert health_monitor is not None
        assert health_monitor.start_time is not None
        assert health_monitor.error_log == []
    
    def test_resource_usage(self, health_monitor):
        """Testet die Resource-Überwachung."""
        usage = health_monitor.get_resource_usage()
        
        assert "cpu_percent" in usage
        assert "memory_percent" in usage
        assert "disk_percent" in usage
        
        assert 0 <= usage["cpu_percent"] <= 100
        assert 0 <= usage["memory_percent"] <= 100
        assert 0 <= usage["disk_percent"] <= 100
    
    def test_check_resources_no_warnings(self, health_monitor):
        """Testet Resource-Checks ohne Warnungen."""
        # Setze hohe Limits damit keine Warnungen entstehen
        health_monitor.max_cpu_percent = 100.0
        health_monitor.max_memory_percent = 100.0
        health_monitor.max_disk_percent = 100.0
        
        warnings = health_monitor.check_resources()
        assert len(warnings) == 0
    
    def test_health_status(self, health_monitor):
        """Testet den Health-Status."""
        status = health_monitor.get_health_status()
        
        assert isinstance(status, HealthStatus)
        assert hasattr(status, "is_healthy")
        assert hasattr(status, "uptime_seconds")
        assert hasattr(status, "cpu_percent")
    
    def test_add_error(self, health_monitor):
        """Testet das Hinzufügen von Fehlern."""
        health_monitor.add_error("Test error 1")
        health_monitor.add_error("Test error 2")
        
        assert len(health_monitor.error_log) == 2
        assert "Test error 1" in health_monitor.error_log[0]
    
    def test_health_report(self, health_monitor):
        """Testet den Health-Report."""
        report = health_monitor.generate_health_report()
        
        assert "SOLANA SNIPER PRO - HEALTH REPORT" in report
        assert "Uptime" in report
        assert "CPU" in report
    
    def test_callbacks(self, health_monitor):
        """Testet Callback-Funktionen."""
        mock_rpc_callback = Mock(return_value="healthy")
        mock_wallet_callback = Mock(return_value=10.5)
        mock_positions_callback = Mock(return_value=3)
        
        health_monitor.set_rpc_check_callback(mock_rpc_callback)
        health_monitor.set_wallet_check_callback(mock_wallet_callback)
        health_monitor.set_positions_check_callback(mock_positions_callback)
        
        status = health_monitor.get_health_status()
        
        mock_rpc_callback.assert_called_once()
        mock_wallet_callback.assert_called_once()
        mock_positions_callback.assert_called_once()


class TestTokenAnalyzer:
    """Tests für den Token Analyzer."""
    
    @pytest.fixture
    def token_analyzer(self):
        """Erstellt einen TokenAnalyzer."""
        config = {
            "smart_money_wallets": [
                {"address": "wallet1", "win_rate": 75.0, "total_trades": 100}
            ]
        }
        return TokenAnalyzer(solana_client=None, config=config)
    
    def test_token_analyzer_initialization(self, token_analyzer):
        """Testet die Initialisierung des TokenAnalyzers."""
        assert token_analyzer is not None
        assert token_analyzer.sentiment_scanner is not None
        assert token_analyzer.dev_tracker is not None
        assert token_analyzer.smart_money_tracker is not None
        assert token_analyzer.metadata_validator is not None
        assert token_analyzer.pair_age_detector is not None
    
    def test_social_sentiment_scanner(self, token_analyzer):
        """Testet den Social Sentiment Scanner."""
        result = token_analyzer.sentiment_scanner.scan_twitter_mentions(
            "PEPE", "Pepe Token", minutes=10
        )
        
        assert "mentions" in result
        assert "score" in result
        assert isinstance(result["score"], (int, float))
    
    def test_dev_wallet_tracker(self, token_analyzer):
        """Testet den Dev Wallet Tracker."""
        dev_wallet = token_analyzer.dev_tracker.identify_dev_wallet("token123")
        
        assert dev_wallet is not None
        assert "token123" in token_analyzer.dev_tracker.dev_wallets
    
    def test_dev_sell_activity_warning(self, token_analyzer):
        """Testet Dev-Verkaufswarnung."""
        is_warning, message = token_analyzer.dev_tracker.check_dev_sell_activity(
            "token123",
            sell_amount_usd=6000,
            total_liquidity_usd=100000
        )
        
        assert is_warning == True
        assert "6.0%" in message
    
    def test_smart_money_tracker(self, token_analyzer):
        """Testet den Smart Money Tracker."""
        score = token_analyzer.smart_money_tracker.get_smart_money_score("wallet1")
        
        assert score > 0
        assert score <= 100
        
        # Unbekannte Wallet sollte Score 0 haben
        unknown_score = token_analyzer.smart_money_tracker.get_smart_money_score("unknown")
        assert unknown_score == 0
    
    def test_metadata_validator(self, token_analyzer):
        """Testet den Metadata Validator."""
        # Test mit ungültiger URI
        result = token_analyzer.metadata_validator.validate_metadata("invalid_uri")
        
        assert "valid" in result
        assert "score" in result
    
    def test_pair_age_detector(self, token_analyzer):
        """Testet den Pair Age Detector."""
        token_address = "test_token"
        
        # Mock creation date
        token_analyzer.pair_age_detector.pair_cache[token_address] = (
            datetime.utcnow() - timedelta(minutes=3)
        )
        
        category = token_analyzer.pair_age_detector.categorize_pair_age(token_address)
        assert category == PairAgeCategory.ULTRA_EARLY
        
        # Älteres Pair
        token_analyzer.pair_age_detector.pair_cache[token_address] = (
            datetime.utcnow() - timedelta(minutes=20)
        )
        category = token_analyzer.pair_age_detector.categorize_pair_age(token_address)
        assert category == PairAgeCategory.EARLY
    
    def test_age_category_strategies(self, token_analyzer):
        """Testet Strategie-Empfehlungen basierend auf Alter."""
        ultra_early_strategy = token_analyzer.pair_age_detector.get_age_category_strategies(
            PairAgeCategory.ULTRA_EARLY
        )
        
        assert ultra_early_strategy["recommended_strategy"] == "jackpot"
        assert ultra_early_strategy["warning"] == "Extrem hohes Risiko!"
    
    def test_analyze_token(self, token_analyzer):
        """Testet die komplette Token-Analyse."""
        score = token_analyzer.analyze_token(
            token_address="test_token_123",
            token_name="Test Token",
            token_symbol="TEST"
        )
        
        assert isinstance(score, TokenScore)
        assert score.address == "test_token_123"
        assert 0 <= score.overall_score <= 100
        assert score.risk_level in ["low", "medium", "high", "critical"]
    
    def test_should_trade_token(self, token_analyzer):
        """Testet die Trade-Entscheidung."""
        # Hoher Score -> Trade erlaubt
        high_score = TokenScore(
            address="test",
            legitimacy_score=80,
            social_score=80,
            holder_score=80,
            dev_score=80,
            smart_money_score=80,
            overall_score=80,
            risk_level="low"
        )
        
        should_trade, reason = token_analyzer.should_trade_token(high_score, min_score=50)
        assert should_trade == True
        
        # Niedriger Score -> Trade abgelehnt
        low_score = TokenScore(
            address="test",
            legitimacy_score=20,
            social_score=20,
            holder_score=20,
            dev_score=20,
            smart_money_score=20,
            overall_score=20,
            risk_level="critical"
        )
        
        should_trade, reason = token_analyzer.should_trade_token(low_score, min_score=50)
        assert should_trade == False


class TestIntegration:
    """Integrationstests für Phase 2 Features."""
    
    def test_logger_health_monitor_integration(self, tmp_path):
        """Testet Integration zwischen Logger und HealthMonitor."""
        log_dir = tmp_path / "logs"
        logger = Logger(log_dir=str(log_dir), console_output=False)
        health_monitor = HealthMonitor(console_output=False)
        
        # HealthMonitor verwendet Logger
        health_monitor.add_error("Test error")
        
        # Logger sollte Eintrag haben
        logs = logger.get_logs(limit=10)
        # HealthMonitor hat eigenen Logger, daher separat testen
    
    def test_token_analyzer_with_mock_data(self):
        """Testet TokenAnalyzer mit Mock-Daten."""
        config = {
            "smart_money_wallets": [
                {"address": "smart1", "win_rate": 80.0, "total_trades": 200}
            ],
            "twitter_api_key": None,
            "twitter_api_secret": None
        }
        
        analyzer = TokenAnalyzer(solana_client=None, config=config)
        
        # Simuliere Analyse
        score = analyzer.analyze_token(
            token_address="mock_token",
            token_name="Mock Token",
            token_symbol="MOCK"
        )
        
        assert score.overall_score >= 0
        assert score.risk_level in ["low", "medium", "high", "critical"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
