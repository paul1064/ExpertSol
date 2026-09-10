"""
Backtesting Tool für historische Trading-Simulation
Testet Strategien mit historischen Daten ohne reales Risiko
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import os


class BacktestResult:
    """Ergebnis eines Backtests"""
    
    def __init__(
        self,
        strategy_name: str,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        total_profit_usd: float,
        total_loss_usd: float,
        win_rate: float,
        profit_factor: float,
        max_drawdown: float,
        sharpe_ratio: float,
        avg_trade_duration_minutes: float,
        best_trade_percent: float,
        worst_trade_percent: float,
        initial_capital: float,
        final_capital: float,
        total_return_percent: float,
        trade_details: List[Dict[str, Any]]
    ):
        self.strategy_name = strategy_name
        self.total_trades = total_trades
        self.winning_trades = winning_trades
        self.losing_trades = losing_trades
        self.total_profit_usd = total_profit_usd
        self.total_loss_usd = total_loss_usd
        self.win_rate = win_rate
        self.profit_factor = profit_factor
        self.max_drawdown = max_drawdown
        self.sharpe_ratio = sharpe_ratio
        self.avg_trade_duration_minutes = avg_trade_duration_minutes
        self.best_trade_percent = best_trade_percent
        self.worst_trade_percent = worst_trade_percent
        self.initial_capital = initial_capital
        self.final_capital = final_capital
        self.total_return_percent = total_return_percent
        self.trade_details = trade_details
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiere zu Dictionary"""
        return asdict(self)
    
    def summary(self) -> str:
        """Gib Zusammenfassung als String"""
        return (
            f"\n{'='*60}\n"
            f"BACKTEST ERGEBNIS: {self.strategy_name}\n"
            f"{'='*60}\n"
            f"Total Trades:        {self.total_trades}\n"
            f"Win-Rate:            {self.win_rate:.2f}%\n"
            f"Profit Factor:       {self.profit_factor:.2f}\n"
            f"Sharpe Ratio:        {self.sharpe_ratio:.2f}\n"
            f"Max Drawdown:        {self.max_drawdown:.2f}%\n"
            f"Total Return:        {self.total_return_percent:.2f}%\n"
            f"Initial Capital:     ${self.initial_capital:,.2f}\n"
            f"Final Capital:       ${self.final_capital:,.2f}\n"
            f"Bester Trade:        +{self.best_trade_percent:.2f}%\n"
            f"Schlechtester Trade: {self.worst_trade_percent:.2f}%\n"
            f"Durchschn. Dauer:    {self.avg_trade_duration_minutes:.1f} Min\n"
            f"{'='*60}"
        )


@dataclass
class HistoricalToken:
    """Historische Token-Daten für Backtesting"""
    address: str
    name: str
    launch_time: datetime
    initial_price: float
    price_history: List[Tuple[datetime, float]]  # [(time, price), ...]
    volume_history: List[Tuple[datetime, float]]
    liquidity_usd: float
    holder_count: int
    is_scam: bool = False
    rug_pull_time: Optional[datetime] = None


class Backtester:
    """
    Backtesting Engine für Trading-Strategien
    
    Simuliert Trades mit historischen Daten um Strategien
    zu testen ohne reales Risiko.
    
    Attributes:
        initial_capital: Startkapital in USD
        data_source: Quelle für historische Daten
    """
    
    def __init__(
        self,
        initial_capital: float = 1000.0,
        data_source: Optional[str] = None
    ):
        """
        Initialisiere Backtester
        
        Args:
            initial_capital: Startkapital in USD (default: 1000)
            data_source: Pfad/API für historische Daten (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.initial_capital = initial_capital
        self.data_source = data_source or "data/historical_tokens.json"
        
        # Lade historische Daten
        self.historical_tokens: List[HistoricalToken] = []
        self._load_historical_data()
        
        # Trading-Konfiguration
        self.slippage_percent = 0.5  # 0.5% Slippage simulieren
        self.fee_percent = 0.3  # 0.3% Trading Fees (Raydium/Jupiter)
        
    def _load_historical_data(self):
        """Lade historische Token-Daten"""
        if os.path.exists(self.data_source):
            try:
                with open(self.data_source, 'r') as f:
                    data = json.load(f)
                
                for token_data in data:
                    token = HistoricalToken(
                        address=token_data["address"],
                        name=token_data["name"],
                        launch_time=datetime.fromisoformat(token_data["launch_time"]),
                        initial_price=token_data["initial_price"],
                        price_history=[
                            (datetime.fromisoformat(t), p)
                            for t, p in token_data["price_history"]
                        ],
                        volume_history=[
                            (datetime.fromisoformat(t), v)
                            for t, v in token_data.get("volume_history", [])
                        ],
                        liquidity_usd=token_data.get("liquidity_usd", 0),
                        holder_count=token_data.get("holder_count", 0),
                        is_scam=token_data.get("is_scam", False),
                        rug_pull_time=(
                            datetime.fromisoformat(token_data["rug_pull_time"])
                            if token_data.get("rug_pull_time") else None
                        )
                    )
                    self.historical_tokens.append(token)
                
                self.logger.info(f"{len(self.historical_tokens)} historische Tokens geladen")
                
            except Exception as e:
                self.logger.error(f"Fehler beim Laden historischer Daten: {e}")
        else:
            self.logger.warning(f"Keine historischen Daten gefunden: {self.data_source}")
    
    def run_backtest(
        self,
        strategy_config: Dict[str, Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tokens_filter: Optional[List[str]] = None
    ) -> BacktestResult:
        """
        Führe Backtest für eine Strategie durch
        
        Args:
            strategy_config: Strategie-Konfiguration (aus config/strategies.py)
            start_date: Startdatum für Backtest (optional)
            end_date: Enddatum für Backtest (optional)
            tokens_filter: Liste von Token-Adressen zum Testen (optional)
            
        Returns:
            BacktestResult mit detaillierten Ergebnissen
        """
        self.logger.info(f"Starte Backtest für Strategie: {strategy_config.get('name', 'Unknown')}")
        
        # Filtere Tokens nach Datum
        filtered_tokens = self._filter_tokens_by_date(
            start_date, end_date, tokens_filter
        )
        
        if not filtered_tokens:
            self.logger.warning("Keine Tokens für Backtest gefunden")
            return self._create_empty_result(strategy_config.get('name', 'Unknown'))
        
        # Simuliere Trades
        trades = []
        capital = self.initial_capital
        peak_capital = self.initial_capital
        max_drawdown = 0.0
        
        for token in filtered_tokens:
            # Prüfe ob Token den Strategie-Kriterien entspricht
            if not self._matches_strategy_criteria(token, strategy_config):
                continue
            
            # Simuliere Entry
            entry_price = self._get_entry_price(token)
            position_size_usd = min(
                capital * (strategy_config.get('einsatz_pro_trade', 0.1)),
                capital
            )
            
            if position_size_usd < 1:  # Minimum Position
                continue
            
            # Kauf mit Slippage und Fees
            entry_price_with_slippage = entry_price * (1 + self.slippage_percent / 100)
            position_size_tokens = position_size_usd / entry_price_with_slippage
            buy_fee = position_size_usd * (self.fee_percent / 100)
            
            # Simuliere Exit basierend auf Strategie
            exit_result = self._simulate_exit(
                token=token,
                entry_price=entry_price_with_slippage,
                position_size_tokens=position_size_tokens,
                strategy_config=strategy_config
            )
            
            if exit_result:
                exit_price = exit_result["exit_price"]
                exit_time = exit_result["exit_time"]
                exit_reason = exit_result["reason"]
                
                # Verkauf mit Slippage und Fees
                exit_price_with_slippage = exit_price * (1 - self.slippage_percent / 100)
                revenue = position_size_tokens * exit_price_with_slippage
                sell_fee = revenue * (self.fee_percent / 100)
                net_revenue = revenue - sell_fee
                
                # Berechne P&L
                profit_loss = net_revenue - position_size_usd
                profit_loss_percent = ((net_revenue - position_size_usd) / position_size_usd) * 100
                
                # Update Kapital
                capital += profit_loss
                peak_capital = max(peak_capital, capital)
                
                # Update Max Drawdown
                current_drawdown = ((peak_capital - capital) / peak_capital) * 100
                max_drawdown = max(max_drawdown, current_drawdown)
                
                # Speichere Trade
                trade = {
                    "token_address": token.address,
                    "token_name": token.name,
                    "entry_time": token.launch_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price_with_slippage,
                    "exit_price": exit_price_with_slippage,
                    "position_size_usd": position_size_usd,
                    "profit_loss_usd": profit_loss,
                    "profit_loss_percent": profit_loss_percent,
                    "exit_reason": exit_reason,
                    "duration_minutes": (exit_time - token.launch_time).total_seconds() / 60
                }
                trades.append(trade)
        
        # Berechne Ergebnis-Statistiken
        result = self._calculate_results(
            strategy_name=strategy_config.get('name', 'Unknown'),
            trades=trades,
            initial_capital=self.initial_capital,
            final_capital=capital,
            max_drawdown=max_drawdown
        )
        
        self.logger.info(result.summary())
        return result
    
    def _filter_tokens_by_date(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        tokens_filter: Optional[List[str]]
    ) -> List[HistoricalToken]:
        """Filtere Tokens nach Datum und Adresse"""
        filtered = self.historical_tokens
        
        if start_date:
            filtered = [t for t in filtered if t.launch_time >= start_date]
        
        if end_date:
            filtered = [t for t in filtered if t.launch_time <= end_date]
        
        if tokens_filter:
            filtered = [t for t in filtered if t.address in tokens_filter]
        
        # Filtere Scams wenn nicht explizit gewünscht
        filtered = [t for t in filtered if not t.is_scam]
        
        return filtered
    
    def _matches_strategy_criteria(
        self,
        token: HistoricalToken,
        strategy_config: Dict[str, Any]
    ) -> bool:
        """Prüfe ob Token Strategie-Kriterien erfüllt"""
        # Beispiel-Kriterien (kann erweitert werden)
        min_liquidity = strategy_config.get('min_liquidity', 0)
        max_holder_concentration = strategy_config.get('max_holder_concentration', 100)
        
        if token.liquidity_usd < min_liquidity:
            return False
        
        # Hier könnten weitere Kriterien geprüft werden
        # (aus security/token_analyzer.py integriert werden)
        
        return True
    
    def _get_entry_price(self, token: HistoricalToken) -> float:
        """Hole Entry-Preis (Launch-Preis oder erster verfügbarer)"""
        if token.price_history:
            return token.price_history[0][1]
        return token.initial_price
    
    def _simulate_exit(
        self,
        token: HistoricalToken,
        entry_price: float,
        position_size_tokens: float,
        strategy_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Simuliere Exit basierend auf Strategie-Parametern
        
        Args:
            token: Historischer Token
            entry_price: Einstiegspreis
            position_size_tokens: Positionsgröße in Tokens
            strategy_config: Strategie-Konfiguration
            
        Returns:
            Exit-Ergebnis oder None wenn kein Exit
        """
        take_profit_percent = strategy_config.get('gewinnziel', 100)
        stop_loss_percent = strategy_config.get('stop_loss', 30)
        trailing_stop_percent = strategy_config.get('trailing_stop', 25)
        
        highest_price = entry_price
        trailing_stop_active = False
        trailing_stop_price = 0.0
        
        for price_time, price in token.price_history:
            # Update Highest Price für Trailing Stop
            if price > highest_price:
                highest_price = price
                
                # Aktiviere Trailing Stop wenn im Profit
                if highest_price > entry_price * (1 + trailing_stop_percent / 100):
                    trailing_stop_active = True
                    trailing_stop_price = highest_price * (1 - trailing_stop_percent / 100)
            
            # Prüfe Take Profit
            if price >= entry_price * (1 + take_profit_percent / 100):
                return {
                    "exit_price": price,
                    "exit_time": price_time,
                    "reason": "take_profit"
                }
            
            # Prüfe Stop Loss
            if price <= entry_price * (1 - stop_loss_percent / 100):
                return {
                    "exit_price": price,
                    "exit_time": price_time,
                    "reason": "stop_loss"
                }
            
            # Prüfe Trailing Stop
            if trailing_stop_active and price <= trailing_stop_price:
                return {
                    "exit_price": price,
                    "exit_time": price_time,
                    "reason": "trailing_stop"
                }
        
        # Kein Exit ausgelöst, verkaufe am Ende der Daten
        if token.price_history:
            last_price = token.price_history[-1][1]
            last_time = token.price_history[-1][0]
            return {
                "exit_price": last_price,
                "exit_time": last_time,
                "reason": "end_of_data"
            }
        
        return None
    
    def _calculate_results(
        self,
        strategy_name: str,
        trades: List[Dict[str, Any]],
        initial_capital: float,
        final_capital: float,
        max_drawdown: float
    ) -> BacktestResult:
        """Berechne detaillierte Ergebnis-Statistiken"""
        total_trades = len(trades)
        
        if total_trades == 0:
            return self._create_empty_result(strategy_name)
        
        winning_trades = [t for t in trades if t["profit_loss_usd"] > 0]
        losing_trades = [t for t in trades if t["profit_loss_usd"] <= 0]
        
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)
        win_rate = (num_winning / total_trades) * 100 if total_trades > 0 else 0
        
        total_profit = sum(t["profit_loss_usd"] for t in winning_trades)
        total_loss = abs(sum(t["profit_loss_usd"] for t in losing_trades))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Sharpe Ratio (vereinfacht, annualisiert)
        returns = [t["profit_loss_percent"] for t in trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if len(returns) > 1 else 1
        sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0  # Annualisiert
        
        # Durchschnittliche Haltedauer
        avg_duration = sum(t["duration_minutes"] for t in trades) / total_trades
        
        # Bester und schlechtester Trade
        best_trade = max(t["profit_loss_percent"] for t in trades) if trades else 0
        worst_trade = min(t["profit_loss_percent"] for t in trades) if trades else 0
        
        # Total Return
        total_return_percent = ((final_capital - initial_capital) / initial_capital) * 100
        
        return BacktestResult(
            strategy_name=strategy_name,
            total_trades=total_trades,
            winning_trades=num_winning,
            losing_trades=num_losing,
            total_profit_usd=total_profit,
            total_loss_usd=total_loss,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            avg_trade_duration_minutes=avg_duration,
            best_trade_percent=best_trade,
            worst_trade_percent=worst_trade,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return_percent=total_return_percent,
            trade_details=trades
        )
    
    def _create_empty_result(self, strategy_name: str) -> BacktestResult:
        """Erstelle leeres Ergebnis wenn keine Trades"""
        return BacktestResult(
            strategy_name=strategy_name,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_profit_usd=0.0,
            total_loss_usd=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            avg_trade_duration_minutes=0.0,
            best_trade_percent=0.0,
            worst_trade_percent=0.0,
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return_percent=0.0,
            trade_details=[]
        )
    
    def compare_strategies(
        self,
        strategies: List[Dict[str, Any]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Vergleiche mehrere Strategien im gleichen Zeitraum
        
        Args:
            strategies: Liste von Strategie-Konfigurationen
            start_date: Startdatum
            end_date: Enddatum
            
        Returns:
            Vergleichs-Ergebnisse als Dictionary
        """
        results = {}
        
        for strategy in strategies:
            strategy_name = strategy.get('name', 'Unknown')
            self.logger.info(f"Teste Strategie: {strategy_name}")
            
            result = self.run_backtest(
                strategy_config=strategy,
                start_date=start_date,
                end_date=end_date
            )
            
            results[strategy_name] = result.to_dict()
        
        # Finde beste Strategie
        best_strategy = max(results.items(), key=lambda x: x[1]["total_return_percent"])
        
        comparison = {
            "strategies": results,
            "best_strategy": best_strategy[0],
            "best_return": best_strategy[1]["total_return_percent"],
            "comparison_date": datetime.now().isoformat()
        }
        
        self.logger.info(
            f"Beste Strategie: {best_strategy[0]} "
            f"mit {best_strategy[1]['total_return_percent']:.2f}% Return"
        )
        
        return comparison
    
    def export_results(self, result: BacktestResult, filepath: str):
        """
        Exportiere Backtest-Ergebnisse als JSON
        
        Args:
            result: Backtest-Ergebnis
            filepath: Zielpfad für die Datei
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            export_data = {
                "summary": result.to_dict(),
                "generated_at": datetime.now().isoformat(),
                "trade_details": result.trade_details
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Backtest-Ergebnisse exportiert nach {filepath}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Exportieren: {e}")
