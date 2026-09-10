"""
Unit-Tests für Phase 4+ Module

Testet:
- Jito Executor
- ML Token Scorer
- Backtester
- Market Regime Detector
"""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Importiere zu testende Module
from core.jito_executor import JitoExecutor, JitoBundle, BundleStatus, JitoTipManager
from analytics.ml_scorer import MLTokenScorer, TokenFeatures, MLScore
from analytics.backtester import Backtester, HistoricalToken, BacktestResult
from analytics.market_regime import (
    MarketRegimeDetector, MarketRegime, MarketIndicators, RegimeAnalysis
)


class TestJitoExecutor:
    """Tests für Jito Executor"""
    
    def test_jito_executor_initialization(self):
        """Teste Initialisierung des Jito Executors"""
        executor = JitoExecutor(default_tip=0.005)
        
        assert executor.default_tip == 0.005
        assert len(executor.JITO_ENDPOINTS) >= 3
        assert executor.max_retries == 3
    
    def test_create_bundle(self):
        """Teste Bundle-Erstellung"""
        executor = JitoExecutor()
        
        # Echte Transaction erstellen (vereinfacht)
        from solders.transaction import VersionedTransaction
        from solders.keypair import Keypair
        
        # Mock Transaction mit bytes-Unterstützung
        mock_tx_bytes = b"mock_transaction_data_12345678901234567890"
        
        # Erstelle ein einfaches Mock das bytes zurückgibt
        class MockTx:
            def __bytes__(self):
                return mock_tx_bytes
        
        mock_tx = MockTx()
        
        bundle = executor.create_bundle([mock_tx], tip_amount=0.01)
        
        assert isinstance(bundle, JitoBundle)
        assert len(bundle.transactions) == 1
        assert bundle.tip_amount == 0.01
        assert bundle.uuid is not None
    
    def test_estimate_tip(self):
        """Teste Tipp-Schätzung"""
        executor = JitoExecutor()
        
        assert executor.estimate_tip("low") == 0.001
        assert executor.estimate_tip("medium") == 0.005
        assert executor.estimate_tip("high") == 0.01
        assert executor.estimate_tip("ultra") == 0.025
        assert executor.estimate_tip("invalid") == 0.005  # Default
    
    def test_endpoint_failover(self):
        """Teste Endpoint Failover"""
        executor = JitoExecutor()
        initial_idx = executor.current_endpoint_idx
        
        executor._switch_endpoint()
        
        assert executor.current_endpoint_idx == initial_idx + 1


class TestJitoTipManager:
    """Tests für Jito Tip Manager"""
    
    def test_tip_manager_initialization(self):
        """Teste Initialisierung"""
        manager = JitoTipManager()
        
        assert manager.success_rate == 1.0
        assert manager.avg_confirmation_time == 0.4
        assert len(manager.tip_history) == 0
    
    def test_calculate_optimal_tip(self):
        """Teste optimale Tipp-Berechnung"""
        manager = JitoTipManager()
        
        # Normale Bedingungen
        tip = manager.calculate_optimal_tip(
            tx_priority="normal",
            network_congestion=0.5,
            urgency=1.0
        )
        assert tip > 0.005  # Höher als Base wegen Kongestion
        
        # Hohe Dringlichkeit
        high_tip = manager.calculate_optimal_tip(
            tx_priority="critical",
            network_congestion=0.8,
            urgency=5.0
        )
        assert high_tip > tip  # Höher wegen Dringlichkeit
    
    def test_record_tip_result(self):
        """Teste Aufnahme von Tipp-Ergebnissen"""
        manager = JitoTipManager()
        
        # Mehrere Ergebnisse aufnehmen
        for i in range(10):
            manager.record_tip_result(
                tip_amount=0.005,
                success=(i % 2 == 0),  # 50% Success Rate
                confirmation_time=0.3 + (i * 0.05)
            )
        
        assert len(manager.tip_history) == 10
        assert 0.0 <= manager.success_rate <= 1.0


class TestMLTokenScorer:
    """Tests für ML Token Scorer"""
    
    def test_scorer_initialization(self):
        """Teste Initialisierung"""
        scorer = MLTokenScorer()
        
        assert scorer.profitable_threshold == 65.0
        assert scorer.risky_threshold == 40.0
        assert len(scorer.feature_weights) > 10
    
    def test_calculate_score(self):
        """Teste Score-Berechnung"""
        scorer = MLTokenScorer()
        
        features = TokenFeatures(
            liquidity_usd=100_000,
            holder_count=500,
            token_age_minutes=30,
            social_mentions_10min=50,
            dev_wallet_activity=0.8,
            lp_lock_days=90,
            top_10_holder_percentage=25,
            tax_percentage=5,
            metadata_completeness_score=85,
            volume_24h_usd=500_000,
            price_change_5min=10,
            unique_buyers_10min=100,
            unique_sellers_10min=50,
            large_transactions_10min=10
        )
        
        score = scorer.calculate_score(features)
        
        assert isinstance(score, MLScore)
        assert 0 <= score.score <= 100
        assert 0 <= score.confidence <= 1
        assert score.prediction in ["profitable", "neutral", "risky"]
        assert score.risk_level in ["low", "medium", "high", "extreme"]
    
    def test_get_recommendation(self):
        """Teste Handlungsempfehlung"""
        scorer = MLTokenScorer()
        
        features = TokenFeatures(
            liquidity_usd=200_000,
            holder_count=1000,
            token_age_minutes=60,
            social_mentions_10min=80,
            dev_wallet_activity=0.9,
            lp_lock_days=180,
            top_10_holder_percentage=20,
            tax_percentage=3,
            metadata_completeness_score=95,
            volume_24h_usd=1_000_000,
            price_change_5min=15,
            unique_buyers_10min=200,
            unique_sellers_10min=50,
            large_transactions_10min=20
        )
        
        recommendation = scorer.get_recommendation(features)
        
        assert "action" in recommendation
        assert "confidence" in recommendation
        assert "ml_details" in recommendation
        assert recommendation["action"] in [
            "STRONG_BUY", "BUY", "HOLD", "AVOID", "STRONG_AVOID"
        ]
    
    def test_normalize_features(self):
        """Teste Feature-Normalisierung"""
        scorer = MLTokenScorer()
        
        features = TokenFeatures(
            liquidity_usd=2_000_000,  # Über Max
            holder_count=20_000,  # Über Max
            token_age_minutes=2000,  # Über Max
            social_mentions_10min=200,  # Über Max
            dev_wallet_activity=0.5,
            lp_lock_days=400,  # Über Max
            top_10_holder_percentage=80,
            tax_percentage=15,
            metadata_completeness_score=100,
            volume_24h_usd=10_000_000,  # Über Max
            price_change_5min=-50,
            unique_buyers_10min=1000,  # Über Max
            unique_sellers_10min=1000,  # Über Max
            large_transactions_10min=100  # Über Max
        )
        
        normalized = scorer._normalize_features(features)
        
        # Alle Werte sollten zwischen 0 und 1 sein
        for value in vars(normalized).values():
            if isinstance(value, float):
                assert 0 <= value <= 1.0 or value == 0.5  # price_change hat spezielle Normalisierung


class TestBacktester:
    """Tests für Backtester"""
    
    def test_backtester_initialization(self):
        """Teste Initialisierung"""
        backtester = Backtester(initial_capital=1000.0)
        
        assert backtester.initial_capital == 1000.0
        assert backtester.slippage_percent == 0.5
        assert backtester.fee_percent == 0.3
    
    def test_create_empty_result(self):
        """Teste leeres Ergebnis"""
        backtester = Backtester()
        result = backtester._create_empty_result("Test Strategie")
        
        assert result.strategy_name == "Test Strategie"
        assert result.total_trades == 0
        assert result.win_rate == 0.0
        assert result.initial_capital == backtester.initial_capital
        assert result.final_capital == backtester.initial_capital
    
    def test_historical_token_creation(self):
        """Teste Historical Token Erstellung"""
        now = datetime.now()
        token = HistoricalToken(
            address="TestToken123",
            name="Test Token",
            launch_time=now,
            initial_price=0.001,
            price_history=[(now, 0.001), (now + timedelta(hours=1), 0.002)],
            volume_history=[],
            liquidity_usd=50_000,
            holder_count=100
        )
        
        assert token.address == "TestToken123"
        assert len(token.price_history) == 2
        assert not token.is_scam


class TestMarketRegimeDetector:
    """Tests für Market Regime Detector"""
    
    def test_detector_initialization(self):
        """Teste Initialisierung"""
        detector = MarketRegimeDetector()
        
        assert detector.update_interval == 300
        assert "btc_trend_threshold" in detector.thresholds
    
    def test_fetch_market_data(self):
        """Teste Daten-Abruf"""
        detector = MarketRegimeDetector()
        indicators = detector.fetch_market_data()
        
        assert isinstance(indicators, MarketIndicators)
        assert hasattr(indicators, 'btc_price')
        assert hasattr(indicators, 'volatility_index')
        assert hasattr(indicators, 'fear_greed_index')
    
    def test_detect_regime_bull(self):
        """Teste Bull Market Erkennung"""
        detector = MarketRegimeDetector()
        
        # Simuliere Bull Market Indikatoren
        bull_indicators = MarketIndicators(
            btc_price=45000,
            btc_ema_200=40000,  # Preis über EMA
            btc_trend="up",
            sol_btc_ratio=0.055,
            sol_btc_trend="rising",
            total_market_volume_24h=100_000_000_000,
            volume_change_percent=25,
            volatility_index=50,
            fear_greed_index=75,  # Gier
            altcoin_season_indicator=70  # Altcoin Season
        )
        
        analysis = detector.detect_regime(bull_indicators)
        
        assert isinstance(analysis, RegimeAnalysis)
        assert analysis.regime in [MarketRegime.BULL, MarketRegime.UNKNOWN]
        assert 0 <= analysis.confidence <= 1
    
    def test_detect_regime_bear(self):
        """Teste Bear Market Erkennung"""
        detector = MarketRegimeDetector()
        
        # Simuliere Bear Market Indikatoren
        bear_indicators = MarketIndicators(
            btc_price=35000,
            btc_ema_200=42000,  # Preis unter EMA
            btc_trend="down",
            sol_btc_ratio=0.045,
            sol_btc_trend="falling",
            total_market_volume_24h=50_000_000_000,
            volume_change_percent=-30,
            volatility_index=60,
            fear_greed_index=20,  # Angst
            altcoin_season_indicator=25  # Bitcoin Dominance
        )
        
        analysis = detector.detect_regime(bear_indicators)
        
        assert isinstance(analysis, RegimeAnalysis)
        assert analysis.risk_level in ["high", "medium"]
    
    def test_should_pause_trading(self):
        """Teste Trading-Pause Empfehlung"""
        detector = MarketRegimeDetector()
        
        # Bear Market mit hoher Confidence sollte Pause empfehlen
        bear_analysis = RegimeAnalysis(
            regime=MarketRegime.BEAR,
            confidence=0.85,
            primary_signal="BTC unter 200 EMA",
            secondary_signals=[],
            recommended_action="DEFENSIVE_OR_PAUSE",
            strategy_adjustments={},
            risk_level="high",
            timestamp=datetime.now()
        )
        
        should_pause = detector.should_pause_trading(bear_analysis)
        assert should_pause is True
    
    def test_get_adjusted_strategy(self):
        """Teste Strategie-Anpassung"""
        detector = MarketRegimeDetector()
        
        base_strategy = {
            "gewinnziel": 100,
            "stop_loss": 30,
            "einsatz_pro_trade": 0.1,
            "max_positionen": 5
        }
        
        # Simuliere Bull Market Analyse
        bull_analysis = RegimeAnalysis(
            regime=MarketRegime.BULL,
            confidence=0.75,
            primary_signal="BTC über 200 EMA",
            secondary_signals=[],
            recommended_action="AGGRESSIVE_TRADING",
            strategy_adjustments={
                "gewinnziel_multiplier": 1.5,
                "stop_loss_multiplier": 0.8,
                "position_size_multiplier": 1.3,
                "max_positions_increase": 2
            },
            risk_level="medium",
            timestamp=datetime.now()
        )
        
        adjusted = detector.get_adjusted_strategy(base_strategy, bull_analysis)
        
        assert adjusted["gewinnziel"] == 150  # 100 * 1.5
        assert adjusted["stop_loss"] == 24  # 30 * 0.8
        assert adjusted["einsatz_pro_trade"] == 0.13  # 0.1 * 1.3
        assert adjusted["max_positionen"] == 7  # 5 + 2
        assert adjusted["current_regime"] == "bull"
    
    def test_get_risk_assessment(self):
        """Teste Risiko-Bewertung"""
        detector = MarketRegimeDetector()
        
        analysis = RegimeAnalysis(
            regime=MarketRegime.VOLATILE,
            confidence=0.6,
            primary_signal="Hohe Volatilität",
            secondary_signals=[],
            recommended_action="REDUCE_EXPOSURE",
            strategy_adjustments={},
            risk_level="high",
            timestamp=datetime.now()
        )
        
        assessment = detector.get_risk_assessment(analysis)
        
        assert "overall_risk_score" in assessment
        assert 0 <= assessment["overall_risk_score"] <= 100
        assert "risk_factors" in assessment
        assert assessment["recommendation"] == "REDUCE_EXPOSURE"


def run_all_tests():
    """Führe alle Tests aus"""
    print("\n" + "="*60)
    print("PHASE 4+ UNIT TESTS")
    print("="*60 + "\n")
    
    # Test-Suiten
    test_classes = [
        TestJitoExecutor,
        TestJitoTipManager,
        TestMLTokenScorer,
        TestBacktester,
        TestMarketRegimeDetector
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    passed_tests += 1
                    print(f"  ✅ {method_name}")
                except Exception as e:
                    failed_tests.append((method_name, str(e)))
                    print(f"  ❌ {method_name}: {e}")
    
    # Zusammenfassung
    print("\n" + "="*60)
    print(f"TEST ZUSAMMENFASSUNG")
    print("="*60)
    print(f"Total:  {total_tests}")
    print(f"Bestanden: {passed_tests}")
    print(f"Fehlgeschlagen: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFehlgeschlagene Tests:")
        for name, error in failed_tests:
            print(f"  - {name}: {error}")
    else:
        print("\n🎉 Alle Tests bestanden!")
    
    print("="*60 + "\n")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
