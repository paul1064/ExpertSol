"""
Performance Tracker für Solana Sniper Pro.

Berechnet und trackt Performance-Metriken wie P&L, Win-Rate, Sharpe Ratio, etc.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import numpy as np
from collections import defaultdict

from data.database import DatabaseManager
from data.models import Performance


class PerformanceTracker:
    """Tracker für Trading-Performance."""
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        Initialisiert den PerformanceTracker.
        
        Args:
            db_manager: Datenbank-Manager (optional)
        """
        self.db = db_manager or DatabaseManager()
    
    def calculate_total_pnl(self) -> Dict[str, float]:
        """
        Berechnet Gesamt-P&L.
        
        Returns:
            Dictionary mit P&L in USD und Prozent
        """
        stats = self.db.get_trade_statistics()
        
        return {
            'total_pnl_usd': stats['total_pnl_usd'],
            'total_pnl_percent': self._calculate_total_pnl_percent(),
            'winning_trades_pnl': self._calculate_winning_pnl(),
            'losing_trades_pnl': self._calculate_losing_pnl()
        }
    
    def _calculate_total_pnl_percent(self) -> float:
        """Berechnet Gesamt-P&L in Prozent."""
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        if not closed_trades:
            return 0.0
        
        total_invested = sum(t.buy_amount_sol for t in closed_trades)
        total_returned = sum(t.sell_amount_sol for t in closed_trades if t.sell_amount_sol)
        
        if total_invested == 0:
            return 0.0
        
        return ((total_returned - total_invested) / total_invested) * 100
    
    def _calculate_winning_pnl(self) -> float:
        """Berechnet P&L aller Gewinner-Trades."""
        closed_trades = self.db.get_closed_trades(limit=1000)
        winning = [t for t in closed_trades if t.profit_loss_usd and t.profit_loss_usd > 0]
        return sum(t.profit_loss_usd for t in winning)
    
    def _calculate_losing_pnl(self) -> float:
        """Berechnet P&L aller Verlierer-Trades."""
        closed_trades = self.db.get_closed_trades(limit=1000)
        losing = [t for t in closed_trades if t.profit_loss_usd and t.profit_loss_usd < 0]
        return sum(t.profit_loss_usd for t in losing)
    
    def calculate_win_rate(self, period_days: int = None) -> float:
        """
        Berechnet Win-Rate.
        
        Args:
            period_days: Zeitraum in Tagen (None = alle Trades)
            
        Returns:
            Win-Rate in Prozent
        """
        stats = self.db.get_trade_statistics()
        return stats['win_rate']
    
    def calculate_profit_factor(self) -> float:
        """
        Berechnet Profit Factor (Summe Gewinne / Summe Verluste).
        
        Returns:
            Profit Factor
        """
        stats = self.db.get_trade_statistics()
        return stats['profit_factor']
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> Optional[float]:
        """
        Berechnet Sharpe Ratio (risiko-adjustierte Rendite).
        
        Args:
            risk_free_rate: Risikofreier Zins (default 2%)
            
        Returns:
            Sharpe Ratio oder None bei unzureichenden Daten
        """
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        if len(closed_trades) < 2:
            return None
        
        # Hole P&L Prozente
        returns = [t.profit_loss_percent for t in closed_trades if t.profit_loss_percent]
        
        if not returns:
            return None
        
        # Durchschnittliche Rendite
        avg_return = np.mean(returns)
        
        # Standardabweichung
        std_return = np.std(returns)
        
        if std_return == 0:
            return None
        
        # Sharpe Ratio = (Rendite - risikofreier Zins) / Standardabweichung
        sharpe = (avg_return - risk_free_rate) / std_return
        
        return round(sharpe, 2)
    
    def calculate_max_drawdown(self) -> float:
        """
        Berechnet maximalen Drawdown (größter Peak-to-Trough Verlust).
        
        Returns:
            Maximaler Drawdown in Prozent
        """
        performance_history = self.db.get_performance_history(days=90)
        
        if len(performance_history) < 2:
            # Fallback: Berechne aus Trades
            return self._calculate_drawdown_from_trades()
        
        # Aus Performance-Historie
        peak = 0
        max_drawdown = 0
        
        for perf in performance_history:
            if perf.portfolio_value_usd > peak:
                peak = perf.portfolio_value_usd
            
            drawdown = (peak - perf.portfolio_value_usd) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return round(max_drawdown, 2)
    
    def _calculate_drawdown_from_trades(self) -> float:
        """Berechnet Drawdown aus Trades (Fallback)."""
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        if not closed_trades:
            return 0.0
        
        # Sortiere nach Zeit
        sorted_trades = sorted(closed_trades, key=lambda t: t.sell_timestamp or t.buy_timestamp)
        
        peak = 0
        current_value = 0
        max_drawdown = 0
        
        for trade in sorted_trades:
            if trade.profit_loss_usd:
                current_value += trade.profit_loss_usd
                
                if current_value > peak:
                    peak = current_value
                
                if peak > 0:
                    drawdown = (peak - current_value) / peak * 100
                    max_drawdown = max(max_drawdown, drawdown)
        
        return round(max_drawdown, 2)
    
    def get_average_holding_time(self) -> timedelta:
        """
        Berechnet durchschnittliche Haltedauer.
        
        Returns:
            Durchschnittliche Haltedauer als timedelta
        """
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        holding_times = []
        for trade in closed_trades:
            if trade.buy_timestamp and trade.sell_timestamp:
                duration = trade.sell_timestamp - trade.buy_timestamp
                holding_times.append(duration.total_seconds())
        
        if not holding_times:
            return timedelta(0)
        
        avg_seconds = sum(holding_times) / len(holding_times)
        return timedelta(seconds=avg_seconds)
    
    def get_best_and_worst_trades(self) -> Dict[str, Any]:
        """
        Findet besten und schlechtesten Trade.
        
        Returns:
            Dictionary mit bestem und schlechtestem Trade
        """
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        if not closed_trades:
            return {'best': None, 'worst': None}
        
        best = max(closed_trades, key=lambda t: t.profit_loss_percent or 0)
        worst = min(closed_trades, key=lambda t: t.profit_loss_percent or 0)
        
        return {
            'best': best.to_dict() if best else None,
            'worst': worst.to_dict() if worst else None
        }
    
    def get_performance_by_hour(self) -> Dict[int, Dict[str, float]]:
        """
        Analysiert Performance nach Stunde des Tages.
        
        Returns:
            Dictionary mit Performance pro Stunde (0-23)
        """
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        hourly_stats = defaultdict(lambda: {'trades': 0, 'pnl': 0.0, 'wins': 0, 'losses': 0})
        
        for trade in closed_trades:
            if trade.sell_timestamp and trade.profit_loss_percent is not None:
                hour = trade.sell_timestamp.hour
                hourly_stats[hour]['trades'] += 1
                hourly_stats[hour]['pnl'] += trade.profit_loss_percent or 0
                
                if trade.profit_loss_percent > 0:
                    hourly_stats[hour]['wins'] += 1
                else:
                    hourly_stats[hour]['losses'] += 1
        
        # Berechne Durchschnittswerte
        result = {}
        for hour, stats in hourly_stats.items():
            trades = stats['trades']
            result[hour] = {
                'trades': trades,
                'avg_pnl_percent': stats['pnl'] / trades if trades > 0 else 0,
                'win_rate': (stats['wins'] / trades * 100) if trades > 0 else 0,
                'total_pnl': stats['pnl']
            }
        
        return result
    
    def get_performance_by_day_of_week(self) -> Dict[int, Dict[str, float]]:
        """
        Analysiert Performance nach Wochentag.
        
        Returns:
            Dictionary mit Performance pro Wochentag (0=Montag, 6=Sonntag)
        """
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        daily_stats = defaultdict(lambda: {'trades': 0, 'pnl': 0.0, 'wins': 0, 'losses': 0})
        
        for trade in closed_trades:
            if trade.sell_timestamp and trade.profit_loss_percent is not None:
                day = trade.sell_timestamp.weekday()
                daily_stats[day]['trades'] += 1
                daily_stats[day]['pnl'] += trade.profit_loss_percent or 0
                
                if trade.profit_loss_percent > 0:
                    daily_stats[day]['wins'] += 1
                else:
                    daily_stats[day]['losses'] += 1
        
        # Berechne Durchschnittswerte
        result = {}
        for day, stats in daily_stats.items():
            trades = stats['trades']
            result[day] = {
                'trades': trades,
                'avg_pnl_percent': stats['pnl'] / trades if trades > 0 else 0,
                'win_rate': (stats['wins'] / trades * 100) if trades > 0 else 0,
                'total_pnl': stats['pnl']
            }
        
        return result
    
    def generate_equity_curve(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Generiert Equity-Kurve (Portfolio-Wert über Zeit).
        
        Args:
            days: Anzahl Tage zurück
            
        Returns:
            Liste von Punkten mit Timestamp und Wert
        """
        performance_history = self.db.get_performance_history(days=days)
        
        if not performance_history:
            # Fallback: Erstelle aus Trades
            return self._generate_equity_from_trades(days)
        
        return [
            {
                'timestamp': perf.timestamp.isoformat(),
                'value_usd': perf.portfolio_value_usd,
                'pnl_usd': perf.daily_pnl_usd,
                'pnl_percent': perf.daily_pnl_percent
            }
            for perf in performance_history
        ]
    
    def _generate_equity_from_trades(self, days: int) -> List[Dict[str, Any]]:
        """Generiert Equity-Kurve aus Trades (Fallback)."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        closed_trades = self.db.get_closed_trades(limit=1000)
        
        # Filtere nach Zeitraum
        filtered_trades = [
            t for t in closed_trades
            if t.sell_timestamp and t.sell_timestamp >= cutoff_date
        ]
        
        if not filtered_trades:
            return []
        
        # Sortiere nach Zeit
        sorted_trades = sorted(filtered_trades, key=lambda t: t.sell_timestamp)
        
        equity_curve = []
        cumulative_pnl = 0
        
        for trade in sorted_trades:
            if trade.profit_loss_usd:
                cumulative_pnl += trade.profit_loss_usd
                equity_curve.append({
                    'timestamp': trade.sell_timestamp.isoformat(),
                    'value_usd': cumulative_pnl,
                    'pnl_usd': trade.profit_loss_usd,
                    'pnl_percent': trade.profit_loss_percent or 0
                })
        
        return equity_curve
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """
        Erstellt umfassenden Performance-Report.
        
        Returns:
            Dictionary mit allen Performance-Metriken
        """
        stats = self.db.get_trade_statistics()
        
        return {
            'summary': {
                'total_trades': stats['total_trades'],
                'winning_trades': stats['winning_trades'],
                'losing_trades': stats['losing_trades'],
                'win_rate_percent': stats['win_rate'],
                'total_pnl_usd': stats['total_pnl_usd'],
                'profit_factor': stats['profit_factor']
            },
            'risk_metrics': {
                'sharpe_ratio': self.calculate_sharpe_ratio(),
                'max_drawdown_percent': self.calculate_max_drawdown(),
                'avg_profit_percent': stats['avg_profit_percent'],
                'avg_loss_percent': stats['avg_loss_percent'],
                'best_trade_percent': stats['best_trade_percent'],
                'worst_trade_percent': stats['worst_trade_percent']
            },
            'timing': {
                'avg_holding_time': str(self.get_average_holding_time()),
                'best_hour': self._get_best_hour(),
                'best_day': self._get_best_day()
            },
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _get_best_hour(self) -> int:
        """Findet die Stunde mit der besten Performance."""
        hourly = self.get_performance_by_hour()
        if not hourly:
            return 0
        
        best_hour = max(hourly.keys(), key=lambda h: hourly[h]['avg_pnl_percent'])
        return best_hour
    
    def _get_best_day(self) -> int:
        """Findet den Wochentag mit der besten Performance."""
        daily = self.get_performance_by_day_of_week()
        if not daily:
            return 0
        
        best_day = max(daily.keys(), key=lambda d: daily[d]['avg_pnl_percent'])
        return best_day
    
    def record_snapshot(self, portfolio_value_usd: float) -> Performance:
        """
        Erstellt aktuellen Performance-Snapshot.
        
        Args:
            portfolio_value_usd: Aktueller Portfolio-Wert
            
        Returns:
            Performance-Objekt
        """
        stats = self.db.get_trade_statistics()
        
        # Tägliche Änderung berechnen
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        # Performance speichern
        perf = self.db.record_performance(
            portfolio_value_usd=portfolio_value_usd,
            daily_pnl_usd=stats['total_pnl_usd'],  # Vereinfacht
            daily_pnl_percent=self._calculate_total_pnl_percent(),
            win_rate_percent=stats['win_rate'],
            total_trades=stats['total_trades'],
            winning_trades=stats['winning_trades'],
            losing_trades=stats['losing_trades'],
            max_drawdown_percent=self.calculate_max_drawdown(),
            sharpe_ratio=self.calculate_sharpe_ratio(),
            profit_factor=stats['profit_factor']
        )
        
        return perf


# Beispiel-Nutzung
if __name__ == '__main__':
    tracker = PerformanceTracker()
    
    # Report generieren
    report = tracker.get_comprehensive_report()
    print("Performance Report:")
    print(f"  Total Trades: {report['summary']['total_trades']}")
    print(f"  Win Rate: {report['summary']['win_rate_percent']:.2f}%")
    print(f"  Total P&L: ${report['summary']['total_pnl_usd']:.2f}")
    print(f"  Sharpe Ratio: {report['risk_metrics']['sharpe_ratio']}")
    print(f"  Max Drawdown: {report['risk_metrics']['max_drawdown_percent']:.2f}%")
