"""
Datenbank-Manager für Solana Sniper Pro.

Verwaltet Datenbank-Operationen für Trades, Tokens und Performance.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, func, desc
import os
import json

from .models import Trade, Token, Performance, SettingsHistory, create_database


class DatabaseManager:
    """Manager für alle Datenbank-Operationen."""
    
    def __init__(self, db_url: str = None):
        """
        Initialisiert den DatabaseManager.
        
        Args:
            db_url: Datenbank-URL (optional, default aus Environment)
        """
        self.engine, self.Session = create_database(db_url)
        self.session = self.Session()
    
    # ========== TRADE OPERATIONEN ==========
    
    def add_trade(self, token_address: str, token_name: str, token_symbol: str,
                  buy_price: float, buy_amount_sol: float, amount_tokens: float,
                  strategy: str = 'konservativ') -> Trade:
        """
        Fügt einen neuen Trade hinzu.
        
        Args:
            token_address: Adresse des Tokens
            token_name: Name des Tokens
            token_symbol: Symbol des Tokens
            buy_price: Kaufpreis in SOL
            buy_amount_sol: Gekaufte Menge in SOL
            amount_tokens: Anzahl der Token
            strategy: Verwendete Strategie
            
        Returns:
            Erstellter Trade
        """
        try:
            trade = Trade(
                token_address=token_address,
                token_name=token_name,
                token_symbol=token_symbol,
                buy_price=buy_price,
                buy_amount_sol=buy_amount_sol,
                amount_tokens=amount_tokens,
                strategy=strategy,
                status='open'
            )
            self.session.add(trade)
            self.session.commit()
            self.session.refresh(trade)
            return trade
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Fehler beim Hinzufügen des Trades: {str(e)}")
    
    def close_trade(self, trade_id: int, sell_price: float, sell_amount_sol: float,
                    exit_reason: str, fees_gas: float = 0.0, fees_jito: float = 0.0,
                    fees_slippage: float = 0.0) -> Optional[Trade]:
        """
        Schließt einen Trade mit Verkaufsdaten.
        
        Args:
            trade_id: ID des Trades
            sell_price: Verkaufspreis
            sell_amount_sol: Verkaufserlös in SOL
            exit_reason: Grund für den Verkauf
            fees_gas: Gas-Gebühren
            fees_jito: Jito-Gebühren
            fees_slippage: Slippage-Kosten
            
        Returns:
            Geschlossener Trade oder None
        """
        try:
            trade = self.session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                return None
            
            trade.sell_price = sell_price
            trade.sell_amount_sol = sell_amount_sol
            trade.sell_timestamp = datetime.utcnow()
            trade.exit_reason = exit_reason
            trade.fees_gas = fees_gas
            trade.fees_jito = fees_jito
            trade.fees_slippage = fees_slippage
            trade.status = 'closed'
            
            # P&L berechnen
            pnl_usd = (sell_amount_sol - buy_amount_sol) * 20  # Vereinfacht: SOL = $20
            pnl_percent = ((sell_amount_sol - buy_amount_sol) / buy_amount_sol) * 100
            
            trade.profit_loss_usd = pnl_usd
            trade.profit_loss_percent = pnl_percent
            
            self.session.commit()
            self.session.refresh(trade)
            return trade
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Fehler beim Schließen des Trades: {str(e)}")
    
    def get_open_trades(self) -> List[Trade]:
        """Ruft alle offenen Trades ab."""
        return self.session.query(Trade).filter(Trade.status == 'open').all()
    
    def get_closed_trades(self, limit: int = 100) -> List[Trade]:
        """Ruft geschlossene Trades ab, sortiert nach Zeit."""
        return self.session.query(Trade)\
            .filter(Trade.status == 'closed')\
            .order_by(desc(Trade.sell_timestamp))\
            .limit(limit)\
            .all()
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        """Ruft einen Trade nach ID ab."""
        return self.session.query(Trade).filter(Trade.id == trade_id).first()
    
    def get_trades_by_token(self, token_address: str) -> List[Trade]:
        """Ruft alle Trades für einen Token ab."""
        return self.session.query(Trade)\
            .filter(Trade.token_address == token_address)\
            .order_by(desc(Trade.buy_timestamp))\
            .all()
    
    def update_trade_notes(self, trade_id: int, notes: str) -> bool:
        """Aktualisiert die Notizen eines Trades."""
        try:
            trade = self.session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                return False
            trade.notes = notes
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            return False
    
    # ========== TOKEN OPERATIONEN ==========
    
    def upsert_token(self, address: str, name: str = None, symbol: str = None,
                     liquidity_usd: float = 0.0, holder_count: int = 0,
                     top_10_holder_percent: float = 0.0, **kwargs) -> Token:
        """
        Erstellt oder aktualisiert einen Token-Eintrag.
        
        Args:
            address: Token-Adresse
            name: Token-Name
            symbol: Token-Symbol
            liquidity_usd: Liquidität in USD
            holder_count: Anzahl Holder
            top_10_holder_percent: Top 10 Holder Konzentration
            **kwargs: Weitere Felder
            
        Returns:
            Token-Objekt
        """
        try:
            token = self.session.query(Token).filter(Token.address == address).first()
            
            if token:
                # Update
                for key, value in kwargs.items():
                    if hasattr(token, key):
                        setattr(token, key, value)
                if name:
                    token.name = name
                if symbol:
                    token.symbol = symbol
                if liquidity_usd > 0:
                    token.liquidity_usd = liquidity_usd
                if holder_count > 0:
                    token.holder_count = holder_count
                if top_10_holder_percent > 0:
                    token.top_10_holder_percent = top_10_holder_percent
                token.last_updated = datetime.utcnow()
            else:
                # Create
                token = Token(
                    address=address,
                    name=name,
                    symbol=symbol,
                    liquidity_usd=liquidity_usd,
                    holder_count=holder_count,
                    top_10_holder_percent=top_10_holder_percent,
                    **{k: v for k, v in kwargs.items() if hasattr(Token, k)}
                )
                self.session.add(token)
            
            self.session.commit()
            self.session.refresh(token)
            return token
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Fehler beim Speichern des Tokens: {str(e)}")
    
    def get_token(self, address: str) -> Optional[Token]:
        """Ruft Token-Informationen ab."""
        return self.session.query(Token).filter(Token.address == address).first()
    
    def get_tokens_by_risk_level(self, risk_level: str) -> List[Token]:
        """Ruft Tokens nach Risk-Level ab."""
        return self.session.query(Token)\
            .filter(Token.risk_level == risk_level)\
            .order_by(desc(Token.last_updated))\
            .all()
    
    # ========== PERFORMANCE OPERATIONEN ==========
    
    def record_performance(self, portfolio_value_usd: float, daily_pnl_usd: float,
                           daily_pnl_percent: float, win_rate_percent: float,
                           total_trades: int, winning_trades: int, losing_trades: int,
                           max_drawdown_percent: float = 0.0, sharpe_ratio: float = None,
                           profit_factor: float = 0.0, period: str = 'daily') -> Performance:
        """
        Speichert einen Performance-Snapshot.
        
        Args:
            portfolio_value_usd: Portfolio-Wert in USD
            daily_pnl_usd: Tages-P&L in USD
            daily_pnl_percent: Tages-P&L in %
            win_rate_percent: Win-Rate in %
            total_trades: Gesamtzahl Trades
            winning_trades: Anzahl Gewinner-Trades
            losing_trades: Anzahl Verlierer-Trades
            max_drawdown_percent: Maximaler Drawdown
            sharpe_ratio: Sharpe Ratio
            profit_factor: Profit Factor
            period: Zeitraum (daily, weekly, monthly, total)
            
        Returns:
            Performance-Objekt
        """
        try:
            perf = Performance(
                portfolio_value_usd=portfolio_value_usd,
                daily_pnl_usd=daily_pnl_usd,
                daily_pnl_percent=daily_pnl_percent,
                win_rate_percent=win_rate_percent,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                max_drawdown_percent=max_drawdown_percent,
                sharpe_ratio=sharpe_ratio,
                profit_factor=profit_factor,
                period=period
            )
            self.session.add(perf)
            self.session.commit()
            self.session.refresh(perf)
            return perf
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Fehler beim Speichern der Performance: {str(e)}")
    
    def get_performance_history(self, days: int = 30, period: str = 'daily') -> List[Performance]:
        """
        Ruft Performance-Historie ab.
        
        Args:
            days: Anzahl Tage zurück
            period: Zeitraum-Filter
            
        Returns:
            Liste von Performance-Objekten
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(Performance)\
            .filter(Performance.timestamp >= cutoff_date)\
            .order_by(desc(Performance.timestamp))
        
        if period != 'all':
            query = query.filter(Performance.period == period)
        
        return query.all()
    
    def get_latest_performance(self) -> Optional[Performance]:
        """Ruft den neuesten Performance-Snapshot ab."""
        return self.session.query(Performance)\
            .order_by(desc(Performance.timestamp))\
            .first()
    
    # ========== SETTINGS HISTORY OPERATIONEN ==========
    
    def log_setting_change(self, strategy: str, setting_name: str,
                           old_value: Any, new_value: Any,
                           changed_by: str = 'user') -> SettingsHistory:
        """
        Loggt eine Settings-Änderung.
        
        Args:
            strategy: Strategie-Name
            setting_name: Name der Einstellung
            old_value: Alter Wert
            new_value: Neuer Wert
            changed_by: Wer hat geändert (user, auto, system)
            
        Returns:
            SettingsHistory-Objekt
        """
        try:
            history = SettingsHistory(
                strategy=strategy,
                setting_name=setting_name,
                old_value=str(old_value),
                new_value=str(new_value),
                changed_by=changed_by
            )
            self.session.add(history)
            self.session.commit()
            self.session.refresh(history)
            return history
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Fehler beim Loggen der Setting-Änderung: {str(e)}")
    
    def get_settings_history(self, strategy: str = None, days: int = 7) -> List[SettingsHistory]:
        """
        Ruft Settings-Historie ab.
        
        Args:
            strategy: Filter nach Strategie
            days: Anzahl Tage zurück
            
        Returns:
            Liste von SettingsHistory-Objekten
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(SettingsHistory)\
            .filter(SettingsHistory.timestamp >= cutoff_date)\
            .order_by(desc(SettingsHistory.timestamp))
        
        if strategy:
            query = query.filter(SettingsHistory.strategy == strategy)
        
        return query.all()
    
    # ========== STATISTIKEN ==========
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """
        Berechnet Trade-Statistiken.
        
        Returns:
            Dictionary mit Statistiken
        """
        closed_trades = self.get_closed_trades(limit=1000)
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_profit_percent': 0.0,
                'avg_loss_percent': 0.0,
                'total_pnl_usd': 0.0,
                'profit_factor': 0.0,
                'best_trade_percent': 0.0,
                'worst_trade_percent': 0.0
            }
        
        winning = [t for t in closed_trades if t.profit_loss_percent > 0]
        losing = [t for t in closed_trades if t.profit_loss_percent <= 0]
        
        total_pnl = sum(t.profit_loss_usd for t in closed_trades if t.profit_loss_usd)
        total_wins = sum(t.profit_loss_usd for t in winning if t.profit_loss_usd)
        total_losses = abs(sum(t.profit_loss_usd for t in losing if t.profit_loss_usd))
        
        avg_profit = sum(t.profit_loss_percent for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.profit_loss_percent for t in losing) / len(losing) if losing else 0
        
        best_trade = max((t.profit_loss_percent for t in closed_trades), default=0)
        worst_trade = min((t.profit_loss_percent for t in closed_trades), default=0)
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': (len(winning) / len(closed_trades)) * 100 if closed_trades else 0,
            'avg_profit_percent': avg_profit,
            'avg_loss_percent': avg_loss,
            'total_pnl_usd': total_pnl or 0,
            'profit_factor': profit_factor if profit_factor != float('inf') else 0,
            'best_trade_percent': best_trade,
            'worst_trade_percent': worst_trade
        }
    
    def export_trades_to_csv(self, filename: str = 'trades_export.csv') -> str:
        """
        Exportiert alle Trades als CSV.
        
        Args:
            filename: Dateiname
            
        Returns:
            Pfad zur exportierten Datei
        """
        import csv
        
        trades = self.session.query(Trade).all()
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trades[0].to_dict().keys() if trades else [])
            writer.writeheader()
            for trade in trades:
                writer.writerow(trade.to_dict())
        
        return filepath
    
    def close(self):
        """Schließt die Datenbank-Session."""
        self.session.close()
    
    def __enter__(self):
        """Context Manager Entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit."""
        self.close()


# Beispiel-Nutzung
if __name__ == '__main__':
    # Test
    db = DatabaseManager('sqlite:///data/test_bot.db')
    
    # Trade hinzufügen
    trade = db.add_trade(
        token_address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
        token_name='TestToken',
        token_symbol='TEST',
        buy_price=0.0001,
        buy_amount_sol=0.5,
        amount_tokens=5000,
        strategy='aggressiv'
    )
    print(f"Trade erstellt: {trade}")
    
    # Statistik abrufen
    stats = db.get_trade_statistics()
    print(f"Statistiken: {stats}")
    
    db.close()
