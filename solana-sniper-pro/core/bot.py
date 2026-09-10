"""
Solana Sniper Pro - Haupt-Bot-Logik

Integriert alle Komponenten:
- Wallet Management
- RPC Client mit Failover
- Sicherheitschecks
- Trading-Strategien
- Emergency Kill Switch
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import signal
import sys

from security.wallet_manager import SecureKeyManager, WalletBalanceChecker
from core.solana_client import SolanaRPCClient
from security.rug_pull_checker import RugPullChecker, TokenAnalyzer
from config.strategies import StrategyManager, TradingStrategy

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Datenklasse für eine offene Trading-Position."""
    
    token_address: str
    token_name: str
    buy_price: float
    amount: float
    buy_timestamp: datetime
    strategy: str
    stop_loss_price: float
    take_profit_price: float
    current_price: float = 0.0
    is_sold: bool = False
    sell_timestamp: Optional[datetime] = None
    sell_reason: Optional[str] = None


@dataclass
class BotState:
    """Aktueller Status des Bots."""
    
    is_running: bool = False
    is_trading_active: bool = True
    emergency_mode: bool = False
    last_heartbeat: datetime = field(default_factory=datetime.now)
    open_positions: List[Position] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0


class EmergencyKillSwitch:
    """
    Emergency Kill Switch für sofortiges Stoppen aller Aktivitäten.
    """
    
    def __init__(self, bot_instance):
        """
        Initialisiert den Kill Switch.
        
        Args:
            bot_instance: Referenz zur Bot-Instanz
        """
        self.bot = bot_instance
        self.logger = logging.getLogger(__name__)
        self.is_activated = False
    
    def activate(self, reason: str = "Manual") -> bool:
        """
        Aktiviert den Emergency Kill Switch.
        
        Args:
            reason: Grund für die Aktivierung
            
        Returns:
            True wenn erfolgreich aktiviert
        """
        if self.is_activated:
            self.logger.warning("Kill Switch bereits aktiviert")
            return False
        
        self.is_activated = True
        self.bot.state.emergency_mode = True
        self.bot.state.is_trading_active = False
        
        self.logger.critical(f"🚨 EMERGENCY KILL SWITCH AKTIVIERT - Grund: {reason}")
        
        # Führe Notfallmaßnahmen aus
        try:
            # 1. Alle offenen Orders canceln
            self._cancel_all_orders()
            
            # 2. Alle Positionen verkaufen
            self._sell_all_positions()
            
            # 3. Trading für 24h sperren
            self._pause_trading(hours=24)
            
            # 4. Benachrichtigung senden
            self._send_notification(f"🚨 EMERGENCY: Alle Positionen geschlossen - {reason}")
            
            # 5. Log-Eintrag
            self._log_emergency_activation(reason)
            
            self.logger.info("Emergency Kill Switch Maßnahmen durchgeführt")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler bei Emergency-Maßnahmen: {str(e)}")
            return False
    
    def _cancel_all_orders(self) -> None:
        """Cancelt alle offenen Orders."""
        self.logger.info("Cancelle alle offenen Orders...")
        # Implementierung hängt vom DEX ab (Raydium, Jupiter, etc.)
        # TODO: Implementiere Order-Canceling
    
    def _sell_all_positions(self) -> None:
        """Verkauft alle offenen Positionen zu Market-Preisen."""
        self.logger.info(f"Verkaufe {len(self.bot.state.open_positions)} Positionen...")
        
        for position in self.bot.state.open_positions:
            if not position.is_sold:
                try:
                    # Simulierter Verkauf
                    self.logger.info(f"Verkaufe {position.token_name} @ Market")
                    position.is_sold = True
                    position.sell_timestamp = datetime.now()
                    position.sell_reason = "emergency_kill_switch"
                    
                except Exception as e:
                    self.logger.error(
                        f"Fehler beim Verkaufen von {position.token_address}: {str(e)}"
                    )
        
        self.bot.state.open_positions.clear()
    
    def _pause_trading(self, hours: int = 24) -> None:
        """
        Sperrt Trading für eine bestimmte Zeit.
        
        Args:
            hours: Anzahl Stunden für die Sperrung
        """
        self.logger.info(f"Trading für {hours} Stunden gesperrt")
        # Implementierung über Bot-State oder Config
    
    def _send_notification(self, message: str) -> None:
        """
        Sendet Benachrichtigung an User.
        
        Args:
            message: Nachrichtentext
        """
        # Implementierung via Telegram/Discord
        self.logger.info(f"Notification: {message}")
    
    def _log_emergency_activation(self, reason: str) -> None:
        """
        Loggt die Aktivierung des Kill Switches.
        
        Args:
            reason: Grund für die Aktivierung
        """
        logger.critical(
            f"EMERGENCY_KILL_SWITCH|{datetime.now()}|{reason}"
        )


class SolanaSniperBot:
    """
    Haupt-Bot-Klasse für Solana Sniper Pro.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialisiert den Solana Sniper Bot.
        
        Args:
            config: Konfigurations-Dictionary (optional)
        """
        self.config = config or {}
        self.state = BotState()
        self.logger = logging.getLogger(__name__)
        
        # Initialisiere Komponenten
        self.key_manager = SecureKeyManager()
        self.rpc_client = SolanaRPCClient()
        self.strategy_manager = StrategyManager()
        self.emergency_switch = EmergencyKillSwitch(self)
        
        # Balance Checker (wird nach RPC-Init verfügbar sein)
        self.balance_checker = None
        
        # Signal-Handler für graceful shutdown
        self._setup_signal_handlers()
        
        self.logger.info("Solana Sniper Bot initialisiert")
    
    def _setup_signal_handlers(self) -> None:
        """Setup Signal-Handler für graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame) -> None:
        """
        Handler für Shutdown-Signale.
        
        Args:
            signum: Signal-Nummer
            frame: Current stack frame
        """
        self.logger.info(f"Shutdown-Signal empfangen ({signum})")
        self.shutdown()
    
    async def initialize(self) -> bool:
        """
        Initialisiert alle Bot-Komponenten.
        
        Returns:
            True wenn erfolgreich
        """
        try:
            self.logger.info("Initialisiere Bot-Komponenten...")
            
            # 1. Lade Private Key
            private_key = self.key_manager.load_private_key_from_env()
            if not private_key:
                self.logger.error("Private Key nicht gefunden!")
                return False
            
            # 2. Erstelle Keypair
            keypair = self.key_manager.load_keypair_from_base58(private_key)
            self.wallet_address = self.key_manager.get_wallet_address(keypair)
            self.logger.info(f"Wallet-Adresse: {self.wallet_address}")
            
            # 3. Verifiziere Keypair
            if not self.key_manager.verify_keypair(keypair):
                self.logger.error("Keypair-Verifikation fehlgeschlagen!")
                return False
            
            # 4. Prüfe Balance
            self.balance_checker = WalletBalanceChecker(self.rpc_client)
            balance_result = self.balance_checker.check_balance(
                self.wallet_address,
                min_balance=self.config.get("min_balance", 0.1)
            )
            
            if not balance_result.get("meets_minimum", False):
                self.logger.warning(
                    f"Wallet-Balance zu niedrig: "
                    f"{balance_result.get('balance_sol', 0):.4f} SOL"
                )
            
            # 5. Starte Health-Check Loop
            asyncio.create_task(self.rpc_client.health_check_loop())
            
            self.logger.info("Bot erfolgreich initialisiert")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler bei Initialisierung: {str(e)}")
            return False
    
    async def start(self) -> None:
        """
        Startet den Bot.
        """
        if self.state.is_running:
            self.logger.warning("Bot läuft bereits")
            return
        
        self.state.is_running = True
        self.state.is_trading_active = True
        self.logger.info("🚀 Solana Sniper Bot gestartet")
        
        # Main Loop
        await self._main_loop()
    
    async def _main_loop(self) -> None:
        """
        Hauptschleife des Bots.
        Überwacht neue Tokens und führt Trades durch.
        """
        self.logger.info("Main Loop gestartet")
        
        while self.state.is_running:
            try:
                # Heartbeat aktualisieren
                self.state.last_heartbeat = datetime.now()
                
                # Prüfen ob Trading aktiv ist
                if not self.state.is_trading_active:
                    await asyncio.sleep(5)
                    continue
                
                # Prüfen ob Emergency Mode aktiv ist
                if self.state.emergency_mode:
                    self.logger.warning("Emergency Mode aktiv - Trading pausiert")
                    await asyncio.sleep(60)
                    continue
                
                # Neue Token scannen (Placeholder)
                # await self._scan_for_new_tokens()
                
                # Offene Positionen überwachen
                await self._monitor_positions()
                
                # Daily P&L resetten um Mitternacht
                self._check_daily_reset()
                
                await asyncio.sleep(1)  # Kurze Pause
                
            except Exception as e:
                self.logger.error(f"Fehler in Main Loop: {str(e)}")
                await asyncio.sleep(5)
    
    async def _monitor_positions(self) -> None:
        """
        Überwacht offene Positionen und führt Stop-Loss/Take-Profit durch.
        """
        for position in self.state.open_positions:
            if position.is_sold:
                continue
            
            try:
                # Hole aktuellen Preis (Placeholder)
                # current_price = await self._get_token_price(position.token_address)
                # position.current_price = current_price
                
                # Prüfe Stop-Loss
                if position.current_price <= position.stop_loss_price:
                    await self._sell_position(position, "stop_loss")
                    continue
                
                # Prüfe Take-Profit
                if position.current_price >= position.take_profit_price:
                    await self._sell_position(position, "take_profit")
                    continue
                
                # Prüfe Trailing-Stop (wenn implementiert)
                # await self._check_trailing_stop(position)
                
            except Exception as e:
                self.logger.error(
                    f"Fehler beim Überwachen von {position.token_address}: {str(e)}"
                )
    
    async def _sell_position(
        self,
        position: Position,
        reason: str
    ) -> None:
        """
        Verkauft eine Position.
        
        Args:
            position: Zu verkaufende Position
            reason: Verkaufsgrund
        """
        try:
            self.logger.info(
                f"Verkaufe {position.token_name} - Grund: {reason}"
            )
            
            # TODO: Implementiere echten Verkauf
            position.is_sold = True
            position.sell_timestamp = datetime.now()
            position.sell_reason = reason
            
            # Update Stats
            self.state.total_trades += 1
            
            # Berechne P&L
            pnl = (position.current_price - position.buy_price) * position.amount
            if pnl > 0:
                self.state.wins += 1
                self.state.daily_pnl += pnl
            else:
                self.state.losses += 1
                self.state.daily_pnl -= abs(pnl)
            
            self.logger.info(
                f"Trade abgeschlossen: P&L = ${pnl:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Fehler beim Verkaufen: {str(e)}")
    
    def _check_daily_reset(self) -> None:
        """
        Setzt Daily P&L um Mitternacht zurück.
        """
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            self.logger.info("Setze Daily P&L zurück")
            self.state.daily_pnl = 0.0
    
    async def execute_buy(
        self,
        token_address: str,
        amount_sol: float,
        strategy_name: str = "konservativ"
    ) -> Optional[Position]:
        """
        Führt einen Kauf durch.
        
        Args:
            token_address: Adresse des Tokens
            amount_sol: Betrag in SOL
            strategy_name: Name der Strategie
            
        Returns:
            Position Objekt oder None bei Fehler
        """
        try:
            # 1. Sicherheitschecks durchführen
            rug_checker = RugPullChecker(self.rpc_client)
            security_results = await rug_checker.perform_all_checks(token_address)
            
            if security_results["recommendation"] == "block":
                self.logger.warning(
                    f"Token blockiert aufgrund von Sicherheitschecks: {token_address}"
                )
                return None
            
            # 2. Strategie laden
            strategy = self.strategy_manager.get_strategy(strategy_name)
            
            # 3. Maximalpositionen prüfen
            if len(self.state.open_positions) >= strategy.max_positionen:
                self.logger.warning("Maximale Anzahl offener Positionen erreicht")
                return None
            
            # 4. Tagesverlustgrenze prüfen
            if abs(self.state.daily_pnl) >= strategy.tagesverlustgrenze:
                self.logger.warning("Tagesverlustgrenze erreicht")
                return None
            
            # 5. Kauf durchführen (Placeholder)
            self.logger.info(
                f"Kaufe {token_address} für {amount_sol} SOL "
                f"(Strategie: {strategy_name})"
            )
            
            # TODO: Implementiere echten Kauf
            
            # 6. Position erstellen
            position = Position(
                token_address=token_address,
                token_name="Unknown",  # TODO: Fetch from metadata
                buy_price=0.0,  # TODO: Set actual buy price
                amount=0.0,  # TODO: Set actual amount
                buy_timestamp=datetime.now(),
                strategy=strategy_name,
                stop_loss_price=0.0,  # TODO: Calculate based on strategy
                take_profit_price=0.0  # TODO: Calculate based on strategy
            )
            
            self.state.open_positions.append(position)
            self.logger.info(f"Position eröffnet: {token_address}")
            
            return position
            
        except Exception as e:
            self.logger.error(f"Fehler beim Kauf: {str(e)}")
            return None
    
    def pause_trading(self) -> None:
        """Pausiert das Trading."""
        self.state.is_trading_active = False
        self.logger.info("Trading pausiert")
    
    def resume_trading(self) -> None:
        """Setzt das Trading fort."""
        if not self.state.emergency_mode:
            self.state.is_trading_active = True
            self.logger.info("Trading fortgesetzt")
        else:
            self.logger.warning("Cannot resume - Emergency Mode active")
    
    def shutdown(self) -> None:
        """
        Fährt den Bot sicher herunter.
        """
        self.logger.info("Fahre Bot herunter...")
        self.state.is_running = False
        
        # Offene Positionen speichern (TODO)
        # Datenbank schließen (TODO)
        
        self.logger.info("Bot heruntergefahren")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Gibt aktuellen Bot-Status zurück.
        
        Returns:
            Status-Dictionary
        """
        return {
            "is_running": self.state.is_running,
            "is_trading_active": self.state.is_trading_active,
            "emergency_mode": self.state.emergency_mode,
            "open_positions": len(self.state.open_positions),
            "daily_pnl": self.state.daily_pnl,
            "total_trades": self.state.total_trades,
            "win_rate": (
                self.state.wins / self.state.total_trades * 100
                if self.state.total_trades > 0 else 0
            ),
            "wallet_address": self.wallet_address if hasattr(self, 'wallet_address') else None,
            "rpc_status": self.rpc_client.get_status()
        }


# Beispiel-Nutzung
if __name__ == "__main__":
    import os
    
    # Setup Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Bot erstellen (nur wenn als Hauptmodul ausgeführt)
    if __name__ == "__main__":
        bot = SolanaSniperBot()
        
        # Async Main
        async def main():
            # Initialisieren
            if await bot.initialize():
                # Bot starten
                await bot.start()
        
        # Run
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nBot gestoppt")
