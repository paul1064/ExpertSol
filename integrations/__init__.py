"""
GMGN.ai Integration Module

This module provides seamless integration between Solana Sniper Pro
and GMGN.ai platform for enhanced trading capabilities.

Features:
- Smart Money Tracking with real-time alerts
- KOL Signal monitoring and auto-trading
- Token research and analysis
- Wallet profiling
- Fast trade execution via GMGN API
"""

from .gmgn_client import (
    GMGNClient,
    GMGNAPIError,
    create_gmgn_client,
    TokenInfo,
    SmartMoneyWallet,
    KOLSignal,
    TradeSignal,
    WalletAnalysis,
    SignalType,
    RiskLevel,
)
from .gmgn_skills import (
    GMGNSkillManager,
    Skill,
    SkillCategory,
    get_skill_manager,
    initialize_skill_manager,
)
from .gmgn_execution import (
    GMGNExecutionEngine,
    get_gmgn_engine,
)

__all__ = [
    # Client
    "GMGNClient",
    "GMGNAPIError",
    "create_gmgn_client",
    "TokenInfo",
    "SmartMoneyWallet",
    "KOLSignal",
    "TradeSignal",
    "WalletAnalysis",
    "SignalType",
    "RiskLevel",
    # Skills
    "GMGNSkillManager",
    "Skill",
    "SkillCategory",
    "get_skill_manager",
    "initialize_skill_manager",
    # Execution
    "GMGNExecutionEngine",
    "get_gmgn_engine",
]

__version__ = "1.0.0"
