"""
Tests für Phase 3 Features.

Testet Datenbank, Performance Tracker, Trade Journal und Priority Fee Calculator.
"""

import pytest
import os
import sys
from datetime import datetime, timedelta

# Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models import Trade, Token, Performance, create_database
from data.database import DatabaseManager
from analytics.performance_tracker import PerformanceTracker
from analytics.trade_journal import TradeJournal
from core.transaction_builder import PriorityFeeCalculator


class TestDatabaseModels:
    """Testet Datenbank-Modelle."""
    
    def test_trade_creation(self):
        """Testet Trade-Erstellung."""
        trade = Trade(
            token_address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            token_name='TestToken',
            token_symbol='TEST',
            buy_price=0.0001,
            buy_amount_sol=0.5,
            amount_tokens=5000,
            strategy='aggressiv'
        )
        
        assert trade.token_name == 'TestToken'
        assert trade.buy_amount_sol == 0.5
        assert trade.status == 'open'
        assert trade.strategy == 'aggressiv'
    
    def test_trade_to_dict(self):
        """Testet Trade-zu-Dict-Konvertierung."""
        trade = Trade(
            token_address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            token_name='TestToken',
            buy_price=0.0001,
            buy_amount_sol=0.5,
            amount_tokens=5000
        )
        
        trade_dict = trade.to_dict()
        
        assert 'token_address' in trade_dict
        assert 'buy_price' in trade_dict
        assert trade_dict['token_name'] == 'TestToken'
    
    def test_token_creation(self):
        """Testet Token-Erstellung."""
        token = Token(
            address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            name='TestToken',
            symbol='TEST',
            liquidity_usd=50000,
            holder_count=100,
            risk_level='medium'
        )
        
        assert token.name == 'TestToken'
        assert token.liquidity_usd == 50000
        assert token.risk_level == 'medium'
    
    def test_performance_creation(self):
        """Testet Performance-Erstellung."""
        perf = Performance(
            portfolio_value_usd=1000,
            daily_pnl_usd=50,
            daily_pnl_percent=5.0,
            win_rate_percent=60.0,
            total_trades=10
        )
        
        assert perf.portfolio_value_usd == 1000
        assert perf.daily_pnl_percent == 5.0
        assert perf.win_rate_percent == 60.0


class TestDatabaseManager:
    """Testet DatabaseManager."""
    
    @pytest.fixture
    def db(self):
        """Erstellt Test-Datenbank."""
        db_mgr = DatabaseManager('sqlite:///data/test_phase3.db')
        yield db_mgr
        # Cleanup
        db_mgr.session.close()
        try:
            os.remove('data/test_phase3.db')
        except:
            pass
    
    def test_add_trade(self, db):
        """Testet Trade-Hinzufügen."""
        trade = db.add_trade(
            token_address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            token_name='TestToken',
            token_symbol='TEST',
            buy_price=0.0001,
            buy_amount_sol=0.5,
            amount_tokens=5000,
            strategy='konservativ'
        )
        
        assert trade.id is not None
        assert trade.token_name == 'TestToken'
        assert trade.status == 'open'
    
    def test_get_open_trades(self, db):
        """Testet Abrufen offener Trades."""
        # Trade hinzufügen
        db.add_trade(
            token_address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            token_name='TestToken',
            token_symbol='TEST',
            buy_price=0.0001,
            buy_amount_sol=0.5,
            amount_tokens=5000
        )
        
        open_trades = db.get_open_trades()
        
        assert len(open_trades) > 0
        assert open_trades[0].token_name == 'TestToken'
    
    def test_close_trade(self, db):
        """Testet Trade-Schließen."""
        # Trade hinzufügen
        trade = db.add_trade(
            token_address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            token_name='TestToken',
            token_symbol='TEST',
            buy_price=0.0001,
            buy_amount_sol=0.5,
            amount_tokens=5000
        )
        
        # Trade schließen
        closed_trade = db.close_trade(
            trade_id=trade.id,
            sell_price=0.0002,
            sell_amount_sol=1.0,
            exit_reason='take_profit'
        )
        
        assert closed_trade.status == 'closed'
        assert closed_trade.exit_reason == 'take_profit'
        assert closed_trade.profit_loss_percent > 0
    
    def test_get_trade_statistics(self, db):
        """Testet Trade-Statistiken."""
        stats = db.get_trade_statistics()
        
        assert 'total_trades' in stats
        assert 'win_rate' in stats
        assert 'profit_factor' in stats
    
    def test_upsert_token(self, db):
        """Testet Token-Erstellen/Aktualisieren."""
        token = db.upsert_token(
            address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            name='TestToken',
            symbol='TEST',
            liquidity_usd=50000,
            holder_count=100
        )
        
        assert token.name == 'TestToken'
        assert token.liquidity_usd == 50000
        
        # Update
        token = db.upsert_token(
            address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
            liquidity_usd=75000
        )
        
        assert token.liquidity_usd == 75000
    
    def test_record_performance(self, db):
        """Testet Performance-Aufzeichnung."""
        perf = db.record_performance(
            portfolio_value_usd=1000,
            daily_pnl_usd=50,
            daily_pnl_percent=5.0,
            win_rate_percent=60.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4
        )
        
        assert perf.portfolio_value_usd == 1000
        assert perf.daily_pnl_percent == 5.0
    
    def test_log_setting_change(self, db):
        """Testet Settings-History."""
        history = db.log_setting_change(
            strategy='konservativ',
            setting_name='gewinnziel',
            old_value='100',
            new_value='120',
            changed_by='user'
        )
        
        assert history.setting_name == 'gewinnziel'
        assert history.new_value == '120'


class TestPerformanceTracker:
    """Testet PerformanceTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Erstellt PerformanceTracker."""
        return PerformanceTracker()
    
    def test_calculate_win_rate(self, tracker):
        """Testet Win-Rate-Berechnung."""
        win_rate = tracker.calculate_win_rate()
        
        assert isinstance(win_rate, float)
        assert 0 <= win_rate <= 100
    
    def test_calculate_profit_factor(self, tracker):
        """Testet Profit-Factor-Berechnung."""
        pf = tracker.calculate_profit_factor()
        
        assert isinstance(pf, float)
        assert pf >= 0
    
    def test_calculate_sharpe_ratio(self, tracker):
        """Testet Sharpe-Ratio-Berechnung."""
        sharpe = tracker.calculate_sharpe_ratio()
        
        # Kann None sein bei zu wenig Daten
        if sharpe is not None:
            assert isinstance(sharpe, float)
    
    def test_get_best_and_worst_trades(self, tracker):
        """Testet Beste/Schlechteste Trades."""
        result = tracker.get_best_and_worst_trades()
        
        assert 'best' in result
        assert 'worst' in result
    
    def test_get_performance_by_hour(self, tracker):
        """Testet Performance nach Stunde."""
        hourly = tracker.get_performance_by_hour()
        
        assert isinstance(hourly, dict)
    
    def test_get_performance_by_day_of_week(self, tracker):
        """Testet Performance nach Wochentag."""
        daily = tracker.get_performance_by_day_of_week()
        
        assert isinstance(daily, dict)
    
    def test_generate_equity_curve(self, tracker):
        """Testet Equity-Kurve."""
        curve = tracker.generate_equity_curve(days=30)
        
        assert isinstance(curve, list)
    
    def test_get_comprehensive_report(self, tracker):
        """Testet umfassenden Report."""
        report = tracker.get_comprehensive_report()
        
        assert 'summary' in report
        assert 'risk_metrics' in report
        assert 'timing' in report


class TestTradeJournal:
    """Testet TradeJournal."""
    
    @pytest.fixture
    def journal(self):
        """Erstellt TradeJournal."""
        return TradeJournal()
    
    def test_get_recent_trades(self, journal):
        """Testet Abrufen letzter Trades."""
        trades = journal.get_recent_trades(limit=10)
        
        assert isinstance(trades, list)
    
    def test_get_trades_by_strategy(self, journal):
        """Testet Strategie-Filter."""
        for strategy in ['konservativ', 'aggressiv', 'jackpot']:
            trades = journal.get_trades_by_strategy(strategy)
            assert isinstance(trades, list)
    
    def test_get_trades_by_exit_reason(self, journal):
        """Testet Exit-Reason-Filter."""
        for reason in ['take_profit', 'stop_loss', 'trailing']:
            trades = journal.get_trades_by_exit_reason(reason)
            assert isinstance(trades, list)
    
    def test_generate_summary_report(self, journal):
        """Testet Summary-Report."""
        report = journal.generate_summary_report(period_days=30)
        
        assert 'period_days' in report
        assert 'total_trades' in report
    
    def test_analyze_strategy_performance(self, journal):
        """Testet Strategie-Analyse."""
        analysis = journal.analyze_strategy_performance()
        
        assert isinstance(analysis, dict)


class TestPriorityFeeCalculator:
    """Testet PriorityFeeCalculator."""
    
    @pytest.fixture
    def calculator(self):
        """Erstellt PriorityFeeCalculator."""
        return PriorityFeeCalculator()
    
    @pytest.mark.asyncio
    async def test_get_recommended_fee(self, calculator):
        """Testet empfohlene Fee-Berechnung."""
        for priority in ['low', 'medium', 'high', 'ultra']:
            fee = await calculator.get_recommended_fee(priority)
            
            assert isinstance(fee, (int, float))
            assert fee > 0
    
    @pytest.mark.asyncio
    async def test_get_fee_tiers(self, calculator):
        """Testet Fee-Tiers."""
        tiers = await calculator.get_fee_tiers()
        
        assert 'low' in tiers
        assert 'medium' in tiers
        assert 'high' in tiers
        assert 'ultra' in tiers
        
        # Fees sollten aufsteigend sein
        assert tiers['low'] <= tiers['medium'] <= tiers['high'] <= tiers['ultra']
    
    def test_get_fee_for_transaction_type(self, calculator):
        """Testet Fee für Transaktionstyp."""
        for tx_type in ['transfer', 'swap', 'nft_purchase', 'token_launch']:
            fee = calculator.get_fee_for_transaction_type(tx_type)
            
            assert isinstance(fee, (int, float))
            assert fee > 0
    
    def test_estimate_confirmation_time(self, calculator):
        """Testet Bestätigungszeit-Schätzung."""
        for fee_multiplier in [0.5, 1.0, 2.0, 3.0]:
            fee = 5000 * fee_multiplier
            time_est = calculator.estimate_confirmation_time(fee)
            
            assert time_est in ['immediate', '< 5s', '< 30s', '> 30s']
    
    def test_calculate_total_fee(self, calculator):
        """Testet Gesamtgebühr-Berechnung."""
        priority_fee = 5000
        compute_units = 200000
        
        total = calculator.calculate_total_fee(priority_fee, compute_units)
        
        # Basis-Fee (5000) + Priority Fee (5000 * 200000)
        expected = 5000 + (5000 * 200000)
        assert total == expected
    
    def test_lamports_to_sol(self, calculator):
        """Testet Lamports-zu-SOL-Konvertierung."""
        lamports = 1_000_000_000
        sol = calculator.lamports_to_sol(lamports)
        
        assert sol == 1.0
    
    def test_sol_to_lamports(self, calculator):
        """Testet SOL-zu-Lamports-Konvertierung."""
        sol = 1.0
        lamports = calculator.sol_to_lamports(sol)
        
        assert lamports == 1_000_000_000
    
    @pytest.mark.asyncio
    async def test_get_network_congestion_level(self, calculator):
        """Testet Netzwerk-Kongestion."""
        congestion = await calculator.get_network_congestion_level()
        
        assert 'level' in congestion
        assert 'base_fee' in congestion
        assert 'recommendation' in congestion
        
        assert congestion['level'] in ['low', 'medium', 'high', 'extreme']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
