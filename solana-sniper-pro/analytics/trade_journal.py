"""
Trade Journal für Solana Sniper Pro.

Automatische Dokumentation aller Trades mit Export-Funktionen.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import csv
import json
import os

from data.database import DatabaseManager


class TradeJournal:
    """Journal für automatische Trade-Dokumentation."""
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        Initialisiert das TradeJournal.
        
        Args:
            db_manager: Datenbank-Manager (optional)
        """
        self.db = db_manager or DatabaseManager()
    
    def log_trade(self, token_name: str, token_address: str, 
                  buy_price: float, sell_price: Optional[float],
                  amount: float, buy_timestamp: datetime, 
                  sell_timestamp: Optional[datetime],
                  profit_loss_usd: float, profit_loss_percent: float,
                  fees_gas: float, fees_jito: float, fees_slippage: float,
                  strategy: str, exit_reason: str, notes: str = "") -> Dict[str, Any]:
        """
        Loggt einen kompletten Trade.
        
        Args:
            token_name: Name des Tokens
            token_address: Adresse des Tokens
            buy_price: Kaufpreis
            sell_price: Verkaufspreis (None wenn noch offen)
            amount: Menge der Token
            buy_timestamp: Kaufzeitpunkt
            sell_timestamp: Verkaufszeitpunkt (None wenn noch offen)
            profit_loss_usd: P&L in USD
            profit_loss_percent: P&L in Prozent
            fees_gas: Gas-Gebühren
            fees_jito: Jito-Gebühren
            fees_slippage: Slippage-Kosten
            strategy: Verwendete Strategie
            exit_reason: Grund für Exit (take_profit, stop_loss, etc.)
            notes: Zusätzliche Notizen
            
        Returns:
            Dictionary mit Trade-Daten
        """
        trade_record = {
            'token_name': token_name,
            'token_address': token_address,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'amount': amount,
            'buy_timestamp': buy_timestamp.isoformat() if buy_timestamp else None,
            'sell_timestamp': sell_timestamp.isoformat() if sell_timestamp else None,
            'profit_loss_usd': profit_loss_usd,
            'profit_loss_percent': profit_loss_percent,
            'fees_gas': fees_gas,
            'fees_jito': fees_jito,
            'fees_slippage': fees_slippage,
            'strategy': strategy,
            'exit_reason': exit_reason,
            'notes': notes,
            'total_fees': fees_gas + fees_jito + fees_slippage,
            'logged_at': datetime.utcnow().isoformat()
        }
        
        return trade_record
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ruft die letzten Trades ab.
        
        Args:
            limit: Anzahl der Trades
            
        Returns:
            Liste von Trade-Dictionaries
        """
        closed_trades = self.db.get_closed_trades(limit=limit)
        return [trade.to_dict() for trade in closed_trades]
    
    def get_trades_by_strategy(self, strategy: str) -> List[Dict[str, Any]]:
        """
        Ruft Trades nach Strategie ab.
        
        Args:
            strategy: Strategie-Name (konservativ, aggressiv, jackpot)
            
        Returns:
            Liste von Trade-Dictionaries
        """
        all_trades = self.db.get_closed_trades(limit=1000)
        filtered = [t for t in all_trades if t.strategy == strategy]
        return [t.to_dict() for t in filtered]
    
    def get_trades_by_exit_reason(self, exit_reason: str) -> List[Dict[str, Any]]:
        """
        Ruft Trades nach Exit-Grund ab.
        
        Args:
            exit_reason: Exit-Grund (take_profit, stop_loss, trailing, manual, emergency)
            
        Returns:
            Liste von Trade-Dictionaries
        """
        all_trades = self.db.get_closed_trades(limit=1000)
        filtered = [t for t in all_trades if t.exit_reason == exit_reason]
        return [t.to_dict() for t in filtered]
    
    def export_to_csv(self, filename: str = 'trade_journal.csv', 
                      include_open: bool = False) -> str:
        """
        Exportiert alle Trades als CSV.
        
        Args:
            filename: Dateiname
            include_open: Auch offene Trades einschließen
            
        Returns:
            Pfad zur exportierten Datei
        """
        if include_open:
            trades = self.db.session.query(
                self.db.session.bind.tables['trades']
            ).all()
        else:
            trades = self.db.get_closed_trades(limit=1000)
        
        filepath = os.path.join('data', filename)
        
        # CSV-Header
        fieldnames = [
            'id', 'token_address', 'token_name', 'token_symbol',
            'buy_price', 'buy_amount_sol', 'amount_tokens',
            'buy_timestamp', 'sell_price', 'sell_amount_sol', 'sell_timestamp',
            'profit_loss_usd', 'profit_loss_percent',
            'fees_gas', 'fees_jito', 'fees_slippage', 'total_fees',
            'strategy', 'exit_reason', 'status', 'notes'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for trade in trades:
                row = {
                    'id': trade.id,
                    'token_address': trade.token_address,
                    'token_name': trade.token_name,
                    'token_symbol': getattr(trade, 'token_symbol', ''),
                    'buy_price': trade.buy_price,
                    'buy_amount_sol': trade.buy_amount_sol,
                    'amount_tokens': trade.amount_tokens,
                    'buy_timestamp': trade.buy_timestamp.isoformat() if trade.buy_timestamp else '',
                    'sell_price': trade.sell_price or '',
                    'sell_amount_sol': trade.sell_amount_sol or '',
                    'sell_timestamp': trade.sell_timestamp.isoformat() if trade.sell_timestamp else '',
                    'profit_loss_usd': trade.profit_loss_usd or '',
                    'profit_loss_percent': trade.profit_loss_percent or '',
                    'fees_gas': trade.fees_gas or 0,
                    'fees_jito': trade.fees_jito or 0,
                    'fees_slippage': trade.fees_slippage or 0,
                    'total_fees': (trade.fees_gas or 0) + (trade.fees_jito or 0) + (trade.fees_slippage or 0),
                    'strategy': trade.strategy,
                    'exit_reason': trade.exit_reason or '',
                    'status': trade.status,
                    'notes': trade.notes or ''
                }
                writer.writerow(row)
        
        return filepath
    
    def export_to_excel(self, filename: str = 'trade_journal.xlsx') -> str:
        """
        Exportiert alle Trades als Excel-Datei.
        
        Args:
            filename: Dateiname
            
        Returns:
            Pfad zur exportierten Datei
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas muss installiert sein: pip install pandas openpyxl")
        
        trades = self.db.get_closed_trades(limit=1000)
        
        # In DataFrame konvertieren
        data = [trade.to_dict() for trade in trades]
        df = pd.DataFrame(data)
        
        filepath = os.path.join('data', filename)
        df.to_excel(filepath, index=False, sheet_name='Trades')
        
        return filepath
    
    def export_to_json(self, filename: str = 'trade_journal.json') -> str:
        """
        Exportiert alle Trades als JSON.
        
        Args:
            filename: Dateiname
            
        Returns:
            Pfad zur exportierten Datei
        """
        trades = self.db.get_closed_trades(limit=1000)
        
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([trade.to_dict() for trade in trades], f, indent=2, default=str)
        
        return filepath
    
    def generate_summary_report(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Generiert Zusammenfassungs-Bericht.
        
        Args:
            period_days: Zeitraum in Tagen
            
        Returns:
            Dictionary mit Zusammenfassung
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        all_trades = self.db.get_closed_trades(limit=1000)
        
        # Filtere nach Zeitraum
        filtered_trades = [
            t for t in all_trades
            if t.sell_timestamp and t.sell_timestamp >= cutoff_date
        ]
        
        if not filtered_trades:
            return {
                'period_days': period_days,
                'total_trades': 0,
                'message': 'Keine Trades im angegebenen Zeitraum'
            }
        
        # Statistiken berechnen
        winning = [t for t in filtered_trades if t.profit_loss_percent and t.profit_loss_percent > 0]
        losing = [t for t in filtered_trades if t.profit_loss_percent and t.profit_loss_percent <= 0]
        
        total_pnl = sum(t.profit_loss_usd for t in filtered_trades if t.profit_loss_usd)
        total_fees = sum(
            (t.fees_gas or 0) + (t.fees_jito or 0) + (t.fees_slippage or 0)
            for t in filtered_trades
        )
        
        avg_win = sum(t.profit_loss_percent for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.profit_loss_percent for t in losing) / len(losing) if losing else 0
        
        best_trade = max(filtered_trades, key=lambda t: t.profit_loss_percent or 0)
        worst_trade = min(filtered_trades, key=lambda t: t.profit_loss_percent or 0)
        
        # Nach Strategie gruppieren
        by_strategy = {}
        for strategy in ['konservativ', 'aggressiv', 'jackpot']:
            strat_trades = [t for t in filtered_trades if t.strategy == strategy]
            if strat_trades:
                strat_wins = [t for t in strat_trades if t.profit_loss_percent and t.profit_loss_percent > 0]
                by_strategy[strategy] = {
                    'trades': len(strat_trades),
                    'wins': len(strat_wins),
                    'win_rate': len(strat_wins) / len(strat_trades) * 100 if strat_trades else 0,
                    'total_pnl': sum(t.profit_loss_usd for t in strat_trades if t.profit_loss_usd)
                }
        
        # Nach Exit-Grund gruppieren
        by_exit_reason = {}
        for reason in ['take_profit', 'stop_loss', 'trailing', 'manual', 'emergency']:
            reason_trades = [t for t in filtered_trades if t.exit_reason == reason]
            if reason_trades:
                by_exit_reason[reason] = {
                    'count': len(reason_trades),
                    'avg_pnl_percent': sum(t.profit_loss_percent for t in reason_trades if t.profit_loss_percent) / len(reason_trades)
                }
        
        return {
            'period_days': period_days,
            'total_trades': len(filtered_trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(filtered_trades) * 100 if filtered_trades else 0,
            'total_pnl_usd': total_pnl,
            'total_fees_usd': total_fees,
            'avg_win_percent': avg_win,
            'avg_loss_percent': avg_loss,
            'best_trade': {
                'token': best_trade.token_name,
                'pnl_percent': best_trade.profit_loss_percent,
                'exit_reason': best_trade.exit_reason
            },
            'worst_trade': {
                'token': worst_trade.token_name,
                'pnl_percent': worst_trade.profit_loss_percent,
                'exit_reason': worst_trade.exit_reason
            },
            'by_strategy': by_strategy,
            'by_exit_reason': by_exit_reason,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def add_note_to_trade(self, trade_id: int, note: str) -> bool:
        """
        Fügt Notiz zu einem Trade hinzu.
        
        Args:
            trade_id: ID des Trades
            note: Notiz-Text
            
        Returns:
            True bei Erfolg
        """
        return self.db.update_trade_notes(trade_id, note)
    
    def get_trade_details(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """
        Ruft Details eines spezifischen Trades ab.
        
        Args:
            trade_id: ID des Trades
            
        Returns:
            Dictionary mit Trade-Details oder None
        """
        trade = self.db.get_trade_by_id(trade_id)
        return trade.to_dict() if trade else None
    
    def analyze_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Analysiert Performance jeder Strategie.
        
        Returns:
            Dictionary mit Performance pro Strategie
        """
        all_trades = self.db.get_closed_trades(limit=1000)
        
        result = {}
        for strategy in ['konservativ', 'aggressiv', 'jackpot']:
            strat_trades = [t for t in all_trades if t.strategy == strategy]
            
            if not strat_trades:
                continue
            
            winning = [t for t in strat_trades if t.profit_loss_percent and t.profit_loss_percent > 0]
            losing = [t for t in strat_trades if t.profit_loss_percent and t.profit_loss_percent <= 0]
            
            total_pnl = sum(t.profit_loss_usd for t in strat_trades if t.profit_loss_usd)
            avg_hold_time = self._calculate_avg_hold_time(strat_trades)
            
            result[strategy] = {
                'total_trades': len(strat_trades),
                'winning_trades': len(winning),
                'losing_trades': len(losing),
                'win_rate': len(winning) / len(strat_trades) * 100 if strat_trades else 0,
                'total_pnl_usd': total_pnl,
                'avg_win_percent': sum(t.profit_loss_percent for t in winning) / len(winning) if winning else 0,
                'avg_loss_percent': sum(t.profit_loss_percent for t in losing) / len(losing) if losing else 0,
                'avg_holding_time_minutes': avg_hold_time,
                'best_trade_percent': max((t.profit_loss_percent for t in strat_trades), default=0),
                'worst_trade_percent': min((t.profit_loss_percent for t in strat_trades), default=0)
            }
        
        return result
    
    def _calculate_avg_hold_time(self, trades: List) -> float:
        """Berechnet durchschnittliche Haltedauer in Minuten."""
        hold_times = []
        for trade in trades:
            if trade.buy_timestamp and trade.sell_timestamp:
                duration = (trade.sell_timestamp - trade.buy_timestamp).total_seconds() / 60
                hold_times.append(duration)
        
        return sum(hold_times) / len(hold_times) if hold_times else 0


# Beispiel-Nutzung
if __name__ == '__main__':
    journal = TradeJournal()
    
    # Summary Report
    summary = journal.generate_summary_report(period_days=7)
    print("Trade Journal Summary (7 Tage):")
    print(f"  Total Trades: {summary.get('total_trades', 0)}")
    print(f"  Win Rate: {summary.get('win_rate', 0):.2f}%")
    print(f"  Total P&L: ${summary.get('total_pnl_usd', 0):.2f}")
    
    # Strategie-Analyse
    strategy_perf = journal.analyze_strategy_performance()
    print("\nStrategie-Performance:")
    for strategy, perf in strategy_perf.items():
        print(f"  {strategy}: {perf['total_trades']} Trades, {perf['win_rate']:.1f}% Win-Rate")
