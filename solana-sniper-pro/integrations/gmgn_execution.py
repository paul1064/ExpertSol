"""
GMGN Execution Engine

Replaces the standard execution engine with GMGN.ai-powered trade execution.
Provides ultra-fast trade execution with MEV protection and optimal routing.

Key Features:
- Sub-second trade execution via GMGN API
- Automatic slippage optimization
- MEV protection through GMGN's routing
- Smart money signal integration
- KOL signal auto-following (optional)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import time

from integrations import GMGNClient, TradeSignal, SignalType, RiskLevel
from config.strategies import STRATEGIES
from core.logger import get_logger

logger = get_logger("GMGN_EXECUTION")


class GMGNExecutionEngine:
    """
    High-performance trade execution engine powered by GMGN.ai
    
    Features:
    - Direct GMGN API integration for fastest execution
    - Smart slippage calculation based on volatility
    - Auto-detection of optimal entry/exit points
    - Integration with smart money signals
    - Risk-managed position sizing
    
    Usage:
        engine = GMGNExecutionEngine(api_key="your_key")
        await engine.initialize()
        
        # Execute buy
        result = await engine.execute_buy(
            token_address="token_addr",
            amount_sol=0.5,
            strategy="aggressive"
        )
        
        # Execute sell
        result = await engine.execute_sell(
            token_address="token_addr",
            percentage=100  # Sell 100% of position
        )
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GMGN Execution Engine
        
        Args:
            api_key: GMGN API key (optional, uses env var if not provided)
        """
        self.api_key = api_key
        self.client: Optional[GMGNClient] = None
        self._initialized = False
        
        # Execution statistics
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_volume_sol = 0.0
        
        # Active positions
        self.positions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("GMGN Execution Engine initialized")
    
    async def initialize(self):
        """Initialize the GMGN client."""
        if self._initialized:
            return
        
        self.client = GMGNClient(api_key=self.api_key)
        self._initialized = True
        
        logger.info("✅ GMGN Execution Engine connected to GMGN API")
    
    async def close(self):
        """Close the GMGN client connection."""
        if self.client:
            await self.client.close()
            logger.info("GMGN Execution Engine disconnected")
    
    async def execute_buy(
        self,
        token_address: str,
        amount_sol: float,
        strategy: str = "konservativ",
        max_slippage_bps: int = 50,
        use_smart_signals: bool = True,
        follow_kol: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a buy order via GMGN
        
        Args:
            token_address: Token to buy
            amount_sol: Amount of SOL to spend
            strategy: Trading strategy name
            max_slippage_bps: Maximum slippage in basis points
            use_smart_signals: Check smart money signals before buying
            follow_kol: Auto-follow KOL signals
            
        Returns:
            Execution result with transaction signature
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Pre-trade checks
            if use_smart_signals:
                signal_valid = await self._validate_smart_money_signal(token_address)
                if not signal_valid:
                    logger.warning(f"⚠️ Smart money signal weak for {token_address[:8]}...")
                    # Continue anyway but log warning
            
            # Get token info for validation
            token_info = await self.client.get_token_info(token_address)
            logger.info(f"📊 Token: {token_info.name} ({token_info.symbol})")
            logger.info(f"   Price: ${token_info.price_usd:.8f}")
            logger.info(f"   Liquidity: ${token_info.liquidity_usd:,.2f}")
            logger.info(f"   GMGN Score: {token_info.gmgn_score:.1f}/100")
            
            # Calculate optimal slippage
            optimal_slippage = await self._calculate_optimal_slippage(
                token_address, 
                max_slippage_bps
            )
            
            # Get strategy settings
            strategy_config = STRATEGIES.get(strategy, STRATEGIES["konservativ"])
            
            # Execute the buy
            logger.info(f"🚀 Executing BUY: {amount_sol} SOL for {token_address[:8]}...")
            
            result = await self.client.execute_swap(
                token_address=token_address,
                amount_sol=amount_sol,
                slippage_bps=optimal_slippage,
                is_buy=True
            )
            
            execution_time = time.time() - start_time
            
            if result.get("success"):
                self.total_trades += 1
                self.successful_trades += 1
                self.total_volume_sol += amount_sol
                
                # Store position
                self.positions[token_address] = {
                    "entry_price": token_info.price_usd,
                    "amount_sol": amount_sol,
                    "entry_time": datetime.now(),
                    "strategy": strategy,
                    "tx_signature": result.get("signature"),
                    "status": "open"
                }
                
                logger.info(f"✅ BUY executed successfully in {execution_time:.2f}s")
                logger.info(f"   Signature: {result.get('signature', 'N/A')[:20]}...")
                logger.info(f"   Entry Price: ${token_info.price_usd:.8f}")
                
                return {
                    "success": True,
                    "signature": result.get("signature"),
                    "entry_price": token_info.price_usd,
                    "amount_sol": amount_sol,
                    "execution_time": execution_time,
                    "token_info": token_info
                }
            else:
                self.failed_trades += 1
                logger.error(f"❌ BUY failed: {result.get('error', 'Unknown error')}")
                
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "execution_time": execution_time
                }
                
        except Exception as e:
            self.failed_trades += 1
            logger.error(f"❌ BUY exception: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def execute_sell(
        self,
        token_address: str,
        percentage: float = 100.0,
        strategy: str = "konservativ",
        reason: str = "manual"
    ) -> Dict[str, Any]:
        """
        Execute a sell order via GMGN
        
        Args:
            token_address: Token to sell
            percentage: Percentage of position to sell (0-100)
            strategy: Trading strategy name
            reason: Reason for selling (take_profit/stop_loss/trailing/manual)
            
        Returns:
            Execution result
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Check if we have a position
            if token_address not in self.positions:
                logger.warning(f"No open position for {token_address[:8]}...")
                return {
                    "success": False,
                    "error": "No open position"
                }
            
            position = self.positions[token_address]
            
            # Get current token info
            token_info = await self.client.get_token_info(token_address)
            
            # Calculate P&L
            entry_price = position["entry_price"]
            current_price = token_info.price_usd
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            logger.info(f"💰 Executing SELL: {percentage}% of {token_address[:8]}...")
            logger.info(f"   Entry: ${entry_price:.8f} | Current: ${current_price:.8f}")
            logger.info(f"   P&L: {pnl_percent:+.2f}%")
            
            # Calculate amount to sell based on position
            amount_sol = position["amount_sol"] * (percentage / 100.0)
            
            # Calculate optimal slippage for sell
            optimal_slippage = await self._calculate_optimal_slippage(
                token_address,
                default_bps=50
            )
            
            # Execute the sell
            result = await self.client.execute_swap(
                token_address=token_address,
                amount_sol=amount_sol,
                slippage_bps=optimal_slippage,
                is_buy=False
            )
            
            execution_time = time.time() - start_time
            
            if result.get("success"):
                self.total_trades += 1
                self.successful_trades += 1
                
                # Update or remove position
                if percentage >= 99.9:
                    self.positions[token_address]["status"] = "closed"
                    self.positions[token_address]["exit_time"] = datetime.now()
                    self.positions[token_address]["exit_reason"] = reason
                    self.positions[token_address]["pnl_percent"] = pnl_percent
                else:
                    # Partial sell
                    self.positions[token_address]["amount_sol"] *= (1 - percentage / 100.0)
                
                logger.info(f"✅ SELL executed successfully in {execution_time:.2f}s")
                logger.info(f"   P&L: {pnl_percent:+.2f}%")
                logger.info(f"   Reason: {reason}")
                
                return {
                    "success": True,
                    "signature": result.get("signature"),
                    "pnl_percent": pnl_percent,
                    "exit_price": current_price,
                    "execution_time": execution_time,
                    "reason": reason
                }
            else:
                self.failed_trades += 1
                logger.error(f"❌ SELL failed: {result.get('error', 'Unknown error')}")
                
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error")
                }
                
        except Exception as e:
            self.failed_trades += 1
            logger.error(f"❌ SELL exception: {str(e)}")
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_auto_exit(
        self,
        token_address: str,
        take_profit_levels: List[float],
        stop_loss: float,
        trailing_stop: float
    ) -> Dict[str, Any]:
        """
        Monitor position and auto-exit based on TP/SL levels
        
        Args:
            token_address: Token to monitor
            take_profit_levels: List of [price_level, percentage_to_sell]
            stop_loss: Stop loss price
            trailing_stop: Trailing stop percentage
            
        Returns:
            Exit result when triggered
        """
        if token_address not in self.positions:
            return {"success": False, "error": "No position"}
        
        position = self.positions[token_address]
        
        while position["status"] == "open":
            try:
                token_info = await self.client.get_token_info(token_address)
                current_price = token_info.price_usd
                entry_price = position["entry_price"]
                
                # Check take profit levels
                for tp_price, tp_percentage in take_profit_levels:
                    if current_price >= tp_price:
                        logger.info(f"🎯 Take Profit triggered at ${current_price:.8f}")
                        return await self.execute_sell(
                            token_address,
                            percentage=tp_percentage,
                            reason="take_profit"
                        )
                
                # Check stop loss
                if current_price <= stop_loss:
                    logger.info(f"🛑 Stop Loss triggered at ${current_price:.8f}")
                    return await self.execute_sell(
                        token_address,
                        percentage=100,
                        reason="stop_loss"
                    )
                
                # Check trailing stop (simplified)
                if current_price > entry_price * (1 + trailing_stop / 100):
                    trail_price = current_price * (1 - trailing_stop / 100)
                    if current_price < trail_price:
                        logger.info(f"📉 Trailing Stop triggered at ${current_price:.8f}")
                        return await self.execute_sell(
                            token_address,
                            percentage=100,
                            reason="trailing_stop"
                        )
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring position: {e}")
                await asyncio.sleep(10)
        
        return {"success": False, "error": "Position already closed"}
    
    async def _validate_smart_money_signal(self, token_address: str) -> bool:
        """Check if smart money is buying this token."""
        try:
            # Get recent trades from smart money wallets
            smart_wallets = await self.client.get_smart_money_wallets(limit=10)
            
            for wallet in smart_wallets:
                recent_trades = await self.client.get_wallet_recent_trades(
                    wallet.address,
                    limit=10
                )
                
                # Check if any smart wallet bought this token recently
                for trade in recent_trades:
                    if trade.get("token_address") == token_address:
                        if trade.get("side") == "buy":
                            logger.info(f"💰 Smart money detected: {wallet.label} buying")
                            return True
            
            return True  # Default to True if no data
            
        except Exception as e:
            logger.error(f"Smart money check failed: {e}")
            return True  # Don't block trade on error
    
    async def _calculate_optimal_slippage(
        self,
        token_address: str,
        default_bps: int = 50
    ) -> int:
        """
        Calculate optimal slippage based on token volatility
        
        Args:
            token_address: Token to analyze
            default_bps: Default slippage in basis points
            
        Returns:
            Optimal slippage in basis points
        """
        try:
            token_info = await self.client.get_token_info(token_address)
            
            # Higher volatility = higher slippage needed
            volatility = abs(token_info.price_change_24h)
            
            if volatility > 50:  # Very volatile
                return min(default_bps * 3, 200)  # Cap at 2%
            elif volatility > 20:  # Volatile
                return min(default_bps * 2, 100)  # Cap at 1%
            elif volatility > 10:  # Moderate
                return default_bps
            else:  # Low volatility
                return max(default_bps // 2, 20)  # Min 0.2%
                
        except Exception:
            return default_bps
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Get summary of all active positions."""
        active = [p for p in self.positions.values() if p["status"] == "open"]
        
        total_value_sol = sum(p["amount_sol"] for p in active)
        
        return {
            "total_positions": len(active),
            "total_value_sol": total_value_sol,
            "positions": active,
            "stats": {
                "total_trades": self.total_trades,
                "successful": self.successful_trades,
                "failed": self.failed_trades,
                "success_rate": (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
                "total_volume_sol": self.total_volume_sol
            }
        }
    
    async def emergency_close_all(self) -> List[Dict[str, Any]]:
        """
        Emergency close all positions
        
        Returns:
            List of close results
        """
        results = []
        
        for token_address in list(self.positions.keys()):
            if self.positions[token_address]["status"] == "open":
                result = await self.execute_sell(
                    token_address,
                    percentage=100,
                    reason="emergency"
                )
                results.append(result)
        
        logger.warning(f"🚨 Emergency close: {len(results)} positions closed")
        
        return results


# Singleton instance
_execution_engine: Optional[GMGNExecutionEngine] = None


def get_gmgn_engine(api_key: Optional[str] = None) -> GMGNExecutionEngine:
    """Get or create GMGN execution engine instance."""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = GMGNExecutionEngine(api_key=api_key)
    return _execution_engine


if __name__ == "__main__":
    async def main():
        engine = get_gmgn_engine()
        await engine.initialize()
        
        print("🚀 GMGN Execution Engine Ready\n")
        
        # Show stats
        stats = engine.get_positions_summary()
        print(f"Total Trades: {stats['stats']['total_trades']}")
        print(f"Success Rate: {stats['stats']['success_rate']:.1f}%")
        
        await engine.close()
    
    asyncio.run(main())
