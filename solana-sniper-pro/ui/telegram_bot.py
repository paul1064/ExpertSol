"""
Telegram Bot Integration für Solana Sniper Pro.

Bietet:
- Steuerung des Bots via Telegram
- Benachrichtigungen über Trades und Events
- Status-Abfragen und Performance-Reports
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from enum import Enum

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Mock-Klassen für Testing ohne telegram-Paket
    class Update: pass
    class ContextTypes: 
        class DEFAULT: pass
    class CallbackQueryHandler: pass
    class CommandHandler: pass

from core.logger import get_logger

logger = get_logger()


class BotState(Enum):
    """Status des Trading-Bots."""
    RUNNING = "running"
    PAUSED = "paused"
    EMERGENCY = "emergency"
    STOPPED = "stopped"


class TelegramBot:
    """
    Telegram Bot für Steuerung und Benachrichtigungen.
    
    Befehle:
    - /start - Bot starten
    - /status - Aktuelle Positionen und P&L anzeigen
    - /pause - Trading pausieren
    - /resume - Trading fortsetzen
    - /settings - Aktuelle Einstellungen anzeigen
    - /emergency - Alle Positionen sofort verkaufen
    - /trades - Letzte 10 Trades anzeigen
    - /performance - Performance-Übersicht
    - /help - Hilfe anzeigen
    """
    
    def __init__(
        self,
        token: str,
        allowed_user_ids: Optional[List[int]] = None,
        bot_state_callback: Optional[Callable] = None,
        emergency_callback: Optional[Callable] = None,
        get_positions_callback: Optional[Callable] = None,
        get_trades_callback: Optional[Callable] = None,
        get_performance_callback: Optional[Callable] = None,
        get_settings_callback: Optional[Callable] = None
    ):
        """
        Initialisiert den Telegram Bot.
        
        Args:
            token: Telegram Bot Token von @BotFather
            allowed_user_ids: Liste von Telegram User IDs die den Bot steuern dürfen
            bot_state_callback: Callback für Bot-State-Änderungen (pause/resume)
            emergency_callback: Callback für Emergency-Kill-Switch
            get_positions_callback: Callback zum Abrufen offener Positionen
            get_trades_callback: Callback zum Abrufen der letzten Trades
            get_performance_callback: Callback für Performance-Daten
            get_settings_callback: Callback für aktuelle Einstellungen
        """
        if not TELEGRAM_AVAILABLE:
            logger.warning(
                "python-telegram-bot nicht installiert, Telegram Bot deaktiviert",
                category="TELEGRAM"
            )
            self.application = None
            return
        
        self.token = token
        self.allowed_user_ids = allowed_user_ids or []
        self.bot_state = BotState.STOPPED
        
        # Callbacks
        self.bot_state_callback = bot_state_callback
        self.emergency_callback = emergency_callback
        self.get_positions_callback = get_positions_callback
        self.get_trades_callback = get_trades_callback
        self.get_performance_callback = get_performance_callback
        self.get_settings_callback = get_settings_callback
        
        # Application erstellen
        self.application = Application.builder().token(token).build()
        
        # Handler registrieren
        self._register_handlers()
        
        logger.info("Telegram Bot initialisiert", category="TELEGRAM")
    
    def _register_handlers(self) -> None:
        """Registriert alle Command-Handler."""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("pause", self.cmd_pause))
        self.application.add_handler(CommandHandler("resume", self.cmd_resume))
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))
        self.application.add_handler(CommandHandler("emergency", self.cmd_emergency))
        self.application.add_handler(CommandHandler("trades", self.cmd_trades))
        self.application.add_handler(CommandHandler("performance", self.cmd_performance))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        logger.debug("Command-Handler registriert", category="TELEGRAM")
    
    def _check_authorization(self, user_id: int) -> bool:
        """
        Prüft ob ein User autorisiert ist.
        
        Args:
            user_id: Telegram User ID
        
        Returns:
            True wenn autorisiert, False sonst
        """
        if not self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /start Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        self.bot_state = BotState.RUNNING
        message = (
            "✅ Solana Sniper Pro Bot gestartet!\n\n"
            "Verfügbare Befehle:\n"
            "/status - Aktuelle Positionen\n"
            "/pause - Trading pausieren\n"
            "/resume - Trading fortsetzen\n"
            "/settings - Einstellungen\n"
            "/emergency - ⚠️ NOT-AUS\n"
            "/trades - Letzte Trades\n"
            "/performance - Performance\n"
            "/help - Hilfe"
        )
        await update.message.reply_text(message)
        logger.info(f"Bot gestartet von User {update.effective_user.id}", category="TELEGRAM")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /status Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        try:
            # Callback aufrufen um Positionsdaten zu holen
            if self.get_positions_callback:
                positions = self.get_positions_callback()
                
                if not positions:
                    message = "📊 Keine offenen Positionen"
                else:
                    message = "📊 Offene Positionen:\n\n"
                    for pos in positions:
                        pnl_percent = pos.get('pnl_percent', 0)
                        pnl_color = "🟢" if pnl_percent > 0 else "🔴"
                        message += (
                            f"{pnl_color} {pos.get('token_name', 'Unknown')}\n"
                            f"   Entry: ${pos.get('entry_price', 0):.6f}\n"
                            f"   Current: ${pos.get('current_price', 0):.6f}\n"
                            f"   P&L: {pnl_percent:+.2f}%\n\n"
                        )
            else:
                message = "⚠️ Positions-Callback nicht konfiguriert"
            
            await update.message.reply_text(message)
            logger.debug(f"Status angefragt von User {update.effective_user.id}", category="TELEGRAM")
        
        except Exception as e:
            logger.error(f"Fehler bei /status: {str(e)}", category="TELEGRAM", exc_info=e)
            await update.message.reply_text(f"❌ Fehler: {str(e)}")
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /pause Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        self.bot_state = BotState.PAUSED
        
        if self.bot_state_callback:
            self.bot_state_callback(BotState.PAUSED)
        
        await update.message.reply_text("⏸️ Trading pausiert")
        logger.warning(f"Trading pausiert von User {update.effective_user.id}", category="TELEGRAM")
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /resume Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        self.bot_state = BotState.RUNNING
        
        if self.bot_state_callback:
            self.bot_state_callback(BotState.RUNNING)
        
        await update.message.reply_text("▶️ Trading fortgesetzt")
        logger.info(f"Trading fortgesetzt von User {update.effective_user.id}", category="TELEGRAM")
    
    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /settings Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        try:
            if self.get_settings_callback:
                settings = self.get_settings_callback()
                message = "⚙️ Aktuelle Einstellungen:\n\n"
                for key, value in settings.items():
                    message += f"{key}: {value}\n"
            else:
                message = "⚠️ Settings-Callback nicht konfiguriert"
            
            await update.message.reply_text(message)
            logger.debug(f"Settings angefragt von User {update.effective_user.id}", category="TELEGRAM")
        
        except Exception as e:
            logger.error(f"Fehler bei /settings: {str(e)}", category="TELEGRAM", exc_info=e)
            await update.message.reply_text(f"❌ Fehler: {str(e)}")
    
    async def cmd_emergency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /emergency Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        # Bestätigung erforderlich
        confirm_message = (
            "🚨 ACHTUNG! 🚨\n\n"
            "Dies wird ALLE Positionen sofort verkaufen!\n"
            "Bist du sicher?\n\n"
            "Klicke auf ✅ JETZT VERKAUFEN zur Bestätigung."
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ JETZT VERKAUFEN", callback_data="emergency_confirm")],
            [InlineKeyboardButton("❌ ABBRECHEN", callback_data="emergency_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(confirm_message, reply_markup=reply_markup)
        logger.critical(f"Emergency angefragt von User {update.effective_user.id}", category="TELEGRAM")
    
    async def emergency_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für Emergency-Bestätigung."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "emergency_confirm":
            self.bot_state = BotState.EMERGENCY
            
            if self.emergency_callback:
                try:
                    self.emergency_callback()
                    await query.edit_message_text("🚨 EMERGENCY ACTIVATED! Alle Positionen werden verkauft...")
                    logger.critical("EMERGENCY KILL SWITCH AKTIVIERT!", category="TELEGRAM")
                except Exception as e:
                    await query.edit_message_text(f"❌ Emergency fehlgeschlagen: {str(e)}")
                    logger.error(f"Emergency Callback fehlgeschlagen: {str(e)}", category="TELEGRAM", exc_info=e)
            else:
                await query.edit_message_text("⚠️ Emergency-Callback nicht konfiguriert")
        
        elif query.data == "emergency_cancel":
            await query.edit_message_text("❌ Emergency abgebrochen")
            logger.info("Emergency abgebrochen", category="TELEGRAM")
    
    async def cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /trades Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        try:
            if self.get_trades_callback:
                trades = self.get_trades_callback(limit=10)
                
                if not trades:
                    message = "📝 Keine Trades gefunden"
                else:
                    message = "📝 Letzte Trades:\n\n"
                    for trade in trades:
                        pnl = trade.get('pnl_usd', 0)
                        pnl_color = "🟢" if pnl > 0 else "🔴"
                        message += (
                            f"{pnl_color} {trade.get('token_name', 'Unknown')}\n"
                            f"   P&L: ${pnl:.2f} ({trade.get('pnl_percent', 0):+.2f}%)\n"
                            f"   Exit: {trade.get('exit_reason', 'unknown')}\n\n"
                        )
            else:
                message = "⚠️ Trades-Callback nicht konfiguriert"
            
            await update.message.reply_text(message)
            logger.debug(f"Trades angefragt von User {update.effective_user.id}", category="TELEGRAM")
        
        except Exception as e:
            logger.error(f"Fehler bei /trades: {str(e)}", category="TELEGRAM", exc_info=e)
            await update.message.reply_text(f"❌ Fehler: {str(e)}")
    
    async def cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /performance Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        try:
            if self.get_performance_callback:
                perf = self.get_performance_callback()
                
                message = (
                    "📈 Performance Übersicht:\n\n"
                    f"Total P&L: ${perf.get('total_pnl', 0):.2f}\n"
                    f"Win-Rate: {perf.get('win_rate', 0):.1f}%\n"
                    f"Total Trades: {perf.get('total_trades', 0)}\n"
                    f"Gewinner: {perf.get('winners', 0)}\n"
                    f"Verlierer: {perf.get('losers', 0)}\n"
                    f"Bester Trade: ${perf.get('best_trade', 0):.2f}\n"
                    f"Schlechtester Trade: ${perf.get('worst_trade', 0):.2f}\n"
                )
            else:
                message = "⚠️ Performance-Callback nicht konfiguriert"
            
            await update.message.reply_text(message)
            logger.debug(f"Performance angefragt von User {update.effective_user.id}", category="TELEGRAM")
        
        except Exception as e:
            logger.error(f"Fehler bei /performance: {str(e)}", category="TELEGRAM", exc_info=e)
            await update.message.reply_text(f"❌ Fehler: {str(e)}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler für /help Befehl."""
        if not self._check_authorization(update.effective_user.id):
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        
        help_text = """
🤖 Solana Sniper Pro - Hilfe

📋 BEFEHLE:
/start - Bot starten
/status - Aktuelle Positionen anzeigen
/pause - Trading pausieren
/resume - Trading fortsetzen
/settings - Einstellungen anzeigen
/emergency - ⚠️ ALLE POSITIONEN VERKAUFEN
/trades - Letzte 10 Trades
/performance - Performance-Übersicht
/help - Diese Hilfe

⚙️ FEATURES:
- Automatischer Token-Sniper
- Rug-Pull Schutz
- Multi-RPC Failover
- 3 Trading-Strategien
- Emergency Kill Switch
- Performance Tracking

🔒 SICHERHEIT:
- Private Keys verschlüsselt
- Nur autorisierte User
- Logging aller Aktionen

Bei Fragen: Support kontaktieren
"""
        await update.message.reply_text(help_text)
        logger.debug(f"Hilfe angefragt von User {update.effective_user.id}", category="TELEGRAM")
    
    def send_notification(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Sendet eine Benachrichtigung an alle autorisierten User.
        
        Args:
            message: Die Nachricht
            parse_mode: Parse-Modus (HTML, Markdown, etc.)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.application or not self.allowed_user_ids:
            return False
        
        try:
            # Nachricht an alle autorisierten User senden
            for user_id in self.allowed_user_ids:
                asyncio.run(
                    self.application.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode=parse_mode
                    )
                )
            
            logger.info(f"Benachrichtigung gesendet: {message[:50]}...", category="TELEGRAM")
            return True
        
        except Exception as e:
            logger.error(f"Benachrichtigung fehlgeschlagen: {str(e)}", category="TELEGRAM", exc_info=e)
            return False
    
    def send_trade_notification(
        self,
        token_name: str,
        action: str,
        amount: float,
        price: float,
        pnl_percent: Optional[float] = None
    ) -> bool:
        """
        Sendet eine Trade-Benachrichtigung.
        
        Args:
            token_name: Name des Tokens
            action: Kauf oder Verkauf
            amount: Menge in SOL oder USD
            price: Preis
            pnl_percent: P&L Prozent bei Verkäufen
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if action.lower() == "buy":
            emoji = "✅"
            message = (
                f"{emoji} <b>Neuer Trade</b>\n\n"
                f"Token: {token_name}\n"
                f"Aktion: GEKAUFT\n"
                f"Menge: {amount:.4f} SOL\n"
                f"Preis: ${price:.6f}"
            )
        else:
            emoji = "🎯" if pnl_percent and pnl_percent > 0 else "❌"
            pnl_text = f" ({pnl_percent:+.2f}%)" if pnl_percent else ""
            message = (
                f"{emoji} <b>Trade geschlossen</b>\n\n"
                f"Token: {token_name}\n"
                f"Aktion: VERKAUFT{pnl_text}\n"
                f"Menge: {amount:.4f} SOL\n"
                f"Preis: ${price:.6f}\n"
                f"P&L: ${amount * price:.2f}"
            )
        
        return self.send_notification(message)
    
    def run(self) -> None:
        """Startet den Bot (blockierend)."""
        if not self.application:
            logger.error("Telegram Bot nicht initialisiert", category="TELEGRAM")
            return
        
        # Emergency Callback-Handler registrieren
        self.application.add_handler(
            CallbackQueryHandler(self.emergency_callback_handler, pattern="^emergency_")
        )
        
        logger.info("Telegram Bot gestartet", category="TELEGRAM")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def start_background(self) -> None:
        """Startet den Bot im Hintergrund-Thread."""
        if not self.application:
            return
        
        import threading
        
        def run_bot():
            self.run()
        
        thread = threading.Thread(target=run_bot, daemon=True)
        thread.start()
        logger.info("Telegram Bot im Hintergrund gestartet", category="TELEGRAM")


# Globale TelegramBot-Instanz
_telegram_bot: Optional[TelegramBot] = None


def get_telegram_bot() -> Optional[TelegramBot]:
    """Gibt die globale TelegramBot-Instanz zurück."""
    global _telegram_bot
    return _telegram_bot


def initialize_telegram_bot(
    token: str,
    allowed_user_ids: List[int],
    **callbacks
) -> Optional[TelegramBot]:
    """
    Initialisiert den globalen Telegram Bot.
    
    Args:
        token: Telegram Bot Token
        allowed_user_ids: Autorisierte User IDs
        **callbacks: Callback-Funktionen für Bot-Events
    
    Returns:
        TelegramBot-Instanz oder None wenn nicht verfügbar
    """
    global _telegram_bot
    
    if not TELEGRAM_AVAILABLE:
        logger.warning(
            "python-telegram-bot nicht installiert. Installiere mit: pip install python-telegram-bot",
            category="TELEGRAM"
        )
        return None
    
    _telegram_bot = TelegramBot(
        token=token,
        allowed_user_ids=allowed_user_ids,
        **callbacks
    )
    return _telegram_bot
