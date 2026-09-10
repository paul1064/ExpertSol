"""
Datenbank-Modelle für Solana Sniper Pro.

Definiert SQLAlchemy-Modelle für Trades, Tokens, Performance und Settings.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os

Base = declarative_base()


class Trade(Base):
    """Modell für einen einzelnen Trade."""
    
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_address = Column(String(100), nullable=False, index=True)
    token_name = Column(String(100))
    token_symbol = Column(String(20))
    
    # Kauf-Daten
    buy_price = Column(Float, nullable=False)
    buy_amount_sol = Column(Float, nullable=False)
    amount_tokens = Column(Float, nullable=False)
    buy_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Verkaufs-Daten
    sell_price = Column(Float, nullable=True)
    sell_amount_sol = Column(Float, nullable=True)
    sell_timestamp = Column(DateTime, nullable=True)
    
    # Profit/Loss
    profit_loss_usd = Column(Float, nullable=True)
    profit_loss_percent = Column(Float, nullable=True)
    
    # Gebühren
    fees_gas = Column(Float, default=0.0)
    fees_jito = Column(Float, default=0.0)
    fees_slippage = Column(Float, default=0.0)
    
    # Strategie & Exit
    strategy = Column(String(50), default='konservativ')
    exit_reason = Column(String(50))  # take_profit, stop_loss, trailing, manual, emergency
    
    # Status
    status = Column(String(20), default='open', index=True)  # open, closed, cancelled
    
    # Notizen
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Trade(id={self.id}, token={self.token_name}, status={self.status}, pnl={self.profit_loss_percent}%)>"
    
    def to_dict(self) -> dict:
        """Konvertiert Trade zu Dictionary."""
        return {
            'id': self.id,
            'token_address': self.token_address,
            'token_name': self.token_name,
            'token_symbol': self.token_symbol,
            'buy_price': self.buy_price,
            'buy_amount_sol': self.buy_amount_sol,
            'amount_tokens': self.amount_tokens,
            'buy_timestamp': self.buy_timestamp.isoformat() if self.buy_timestamp else None,
            'sell_price': self.sell_price,
            'sell_amount_sol': self.sell_amount_sol,
            'sell_timestamp': self.sell_timestamp.isoformat() if self.sell_timestamp else None,
            'profit_loss_usd': self.profit_loss_usd,
            'profit_loss_percent': self.profit_loss_percent,
            'fees_gas': self.fees_gas,
            'fees_jito': self.fees_jito,
            'fees_slippage': self.fees_slippage,
            'strategy': self.strategy,
            'exit_reason': self.exit_reason,
            'status': self.status,
            'notes': self.notes
        }


class Token(Base):
    """Modell für Token-Informationen und Analyse-Daten."""
    
    __tablename__ = 'tokens'
    
    address = Column(String(100), primary_key=True)
    name = Column(String(100))
    symbol = Column(String(20))
    
    # Liquidity & Holder
    liquidity_usd = Column(Float, default=0.0)
    holder_count = Column(Integer, default=0)
    top_10_holder_percent = Column(Float, default=0.0)
    
    # Zeitstempel
    creation_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Scores
    ml_score = Column(Float, nullable=True)  # 0-100
    legitimacy_score = Column(Float, nullable=True)  # 0-100
    risk_level = Column(String(20), default='unknown')  # low, medium, high, critical
    
    # Security Checks
    is_honeypot = Column(Boolean, default=False)
    mint_authority_null = Column(Boolean, default=False)
    lp_lock_days = Column(Integer, default=0)
    tax_buy_percent = Column(Float, default=0.0)
    tax_sell_percent = Column(Float, default=0.0)
    
    # Metadata
    metadata_uri = Column(String(500), nullable=True)
    has_logo = Column(Boolean, default=False)
    has_website = Column(Boolean, default=False)
    has_socials = Column(Boolean, default=False)
    
    # Pair Info
    pair_address = Column(String(100), nullable=True)
    pair_age_minutes = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Token(address={self.address[:8]}..., name={self.name}, risk={self.risk_level})>"
    
    def to_dict(self) -> dict:
        """Konvertiert Token zu Dictionary."""
        return {
            'address': self.address,
            'name': self.name,
            'symbol': self.symbol,
            'liquidity_usd': self.liquidity_usd,
            'holder_count': self.holder_count,
            'top_10_holder_percent': self.top_10_holder_percent,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'ml_score': self.ml_score,
            'legitimacy_score': self.legitimacy_score,
            'risk_level': self.risk_level,
            'is_honeypot': self.is_honeypot,
            'mint_authority_null': self.mint_authority_null,
            'lp_lock_days': self.lp_lock_days,
            'tax_buy_percent': self.tax_buy_percent,
            'tax_sell_percent': self.tax_sell_percent,
            'has_logo': self.has_logo,
            'has_website': self.has_website,
            'has_socials': self.has_socials,
            'pair_age_minutes': self.pair_age_minutes
        }


class Performance(Base):
    """Modell für Performance-Snapshots."""
    
    __tablename__ = 'performance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Portfolio-Werte
    portfolio_value_usd = Column(Float, default=0.0)
    daily_pnl_usd = Column(Float, default=0.0)
    daily_pnl_percent = Column(Float, default=0.0)
    
    # Statistik
    win_rate_percent = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Risk Metrics
    max_drawdown_percent = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)
    profit_factor = Column(Float, default=0.0)
    
    # Zeitraum
    period = Column(String(20), default='daily')  # daily, weekly, monthly, total
    
    def __repr__(self):
        return f"<Performance(timestamp={self.timestamp}, pnl={self.daily_pnl_percent}%, win_rate={self.win_rate_percent}%)>"
    
    def to_dict(self) -> dict:
        """Konvertiert Performance zu Dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'portfolio_value_usd': self.portfolio_value_usd,
            'daily_pnl_usd': self.daily_pnl_usd,
            'daily_pnl_percent': self.daily_pnl_percent,
            'win_rate_percent': self.win_rate_percent,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'max_drawdown_percent': self.max_drawdown_percent,
            'sharpe_ratio': self.sharpe_ratio,
            'profit_factor': self.profit_factor,
            'period': self.period
        }


class SettingsHistory(Base):
    """Modell für Settings-Änderungen (Audit Trail)."""
    
    __tablename__ = 'settings_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    strategy = Column(String(50), nullable=False)
    setting_name = Column(String(100), nullable=False)
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=False)
    
    changed_by = Column(String(50), default='user')  # user, auto, system
    
    def __repr__(self):
        return f"<SettingsHistory(setting={self.setting_name}, old={self.old_value}, new={self.new_value})>"
    
    def to_dict(self) -> dict:
        """Konvertiert SettingsHistory zu Dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'strategy': self.strategy,
            'setting_name': self.setting_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'changed_by': self.changed_by
        }


def create_database(db_url: str = None) -> tuple:
    """
    Erstellt Datenbank-Engine und Session.
    
    Args:
        db_url: Datenbank-URL (z.B. sqlite:///data/bot.db)
        
    Returns:
        Tuple aus (engine, Session)
    """
    if db_url is None:
        db_url = os.getenv('DATABASE_URL', 'sqlite:///data/bot.db')
    
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    
    return engine, Session


# Beispiel-Nutzung:
if __name__ == '__main__':
    # Test-Datenbank erstellen
    engine, Session = create_database('sqlite:///data/test_bot.db')
    session = Session()
    
    # Beispiel-Trade erstellen
    trade = Trade(
        token_address='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
        token_name='POPCOIN',
        token_symbol='POP',
        buy_price=0.0001,
        buy_amount_sol=0.5,
        amount_tokens=5000,
        strategy='aggressiv',
        status='open'
    )
    
    session.add(trade)
    session.commit()
    
    print(f"Trade erstellt: {trade}")
    print(f"Trade als Dict: {trade.to_dict()}")
    
    session.close()
