"""
GMGN.ai API Client Integration

Professional integration with GMGN.ai platform for:
- Smart Money Tracking
- Token Research & Analysis
- KOL Buy Signals
- Wallet Analysis
- Market Data
- Trade Execution via GMGN API

Author: Solana Sniper Pro Team
Version: 1.0.0
"""

import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import hmac
import time
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals from GMGN."""
    BUY = "buy"
    SELL = "sell"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"
    HOLD = "hold"


class RiskLevel(Enum):
    """Risk levels for tokens."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class TokenInfo:
    """Token information from GMGN."""
    address: str
    name: str
    symbol: str
    price_usd: float
    price_change_24h: float
    volume_24h: float
    liquidity_usd: float
    market_cap: float
    holder_count: int
    creation_date: Optional[datetime] = None
    security_score: float = 0.0
    gmgn_score: float = 0.0


@dataclass
class SmartMoneyWallet:
    """Smart money wallet information."""
    address: str
    label: str
    win_rate: float
    total_pnl: float
    total_trades: int
    avg_hold_time: float  # in hours
    recent_trades: List[Dict] = field(default_factory=list)
    top_tokens: List[str] = field(default_factory=list)


@dataclass
class KOLSignal:
    """KOL (Key Opinion Leader) buy signal."""
    kol_name: str
    kol_address: str
    token_address: str
    token_symbol: str
    action: SignalType
    amount_usd: float
    timestamp: datetime
    confidence: float
    followers_count: int


@dataclass
class TradeSignal:
    """Trading signal from GMGN analysis."""
    token_address: str
    signal_type: SignalType
    confidence: float  # 0-100
    entry_price: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    reason: str
    risk_level: RiskLevel
    timestamp: datetime
    expiry: Optional[datetime] = None


@dataclass
class WalletAnalysis:
    """Comprehensive wallet analysis."""
    address: str
    total_value_usd: float
    total_pnl: float
    win_rate: float
    total_trades: int
    profitable_trades: int
    losing_trades: int
    avg_profit: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_hold_time: float  # hours
    favorite_tokens: List[str]
    recent_activity: List[Dict]
    risk_score: float  # 0-100, lower is better
    is_smart_money: bool
    labels: List[str]


class GMGNClient:
    """
    Professional GMGN.ai API Client
    
    Provides access to:
    - Real-time market data
    - Smart money tracking
    - KOL signals
    - Wallet analysis
    - Token research
    - Trade execution
    
    Usage:
        client = GMGNClient(api_key="your_key")
        signals = await client.get_signals("token_address")
        analysis = await client.analyze_wallet("wallet_address")
    """
    
    # GMGN API Endpoints
    BASE_URL = "https://api.gmgn.ai"
    TRADE_API_URL = "https://trade-api.gmgn.ai"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GMGN Client
        
        Args:
            api_key: GMGN API key. If None, loads from SOLANA_GMGN_API_KEY env var
        """
        self.api_key = api_key or os.getenv("SOLANA_GMGN_API_KEY")
        
        if not self.api_key:
            logger.warning("No GMGN API key provided. Some features may be limited.")
        
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
                "User-Agent": "SolanaSniperPro/1.0"
            }
        )
        
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._request_count = 0
        self._last_request_time = 0
        
        logger.info("GMGN Client initialized successfully")
    
    async def close(self):
        """Close the HTTP session."""
        await self.session.aclose()
        logger.info("GMGN Client session closed")
    
    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key from endpoint and params."""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()
    
    def _is_cache_valid(self, key: str, ttl_seconds: int = 300) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[key]
    
    def _set_cache(self, key: str, data: Any, ttl_seconds: int = 300):
        """Store data in cache."""
        self._cache[key] = data
        self._cache_expiry[key] = datetime.now()
    
    async def _rate_limit(self):
        """Implement rate limiting (100 requests per minute)."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        # GMGN allows ~100 req/min, we'll be conservative at 80
        min_interval = 0.75
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
        self._request_count += 1
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """
        Make authenticated request to GMGN API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            use_cache: Whether to use caching
            cache_ttl: Cache time-to-live in seconds
            
        Returns:
            API response as dictionary
            
        Raises:
            GMGNAPIError: If API request fails
        """
        # Check cache
        if use_cache and method == "GET":
            cache_key = self._get_cache_key(endpoint, params or {})
            if self._is_cache_valid(cache_key, cache_ttl):
                logger.debug(f"Cache hit for {endpoint}")
                return self._cache[cache_key]
        
        # Rate limiting
        await self._rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = await self.session.request(
                method=method,
                url=url,
                params=params,
                json=data
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Cache successful GET requests
            if use_cache and method == "GET":
                self._set_cache(cache_key, result, cache_ttl)
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
            raise GMGNAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request Error: {str(e)}")
            raise GMGNAPIError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise GMGNAPIError(f"Unexpected error: {str(e)}")
    
    # ==================== TOKEN ANALYSIS ====================
    
    async def get_token_info(self, token_address: str) -> TokenInfo:
        """
        Get comprehensive token information
        
        Args:
            token_address: Solana token mint address
            
        Returns:
            TokenInfo object with token details
        """
        endpoint = "/v1/token/info"
        params = {"address": token_address}
        
        response = await self._request("GET", endpoint, params=params)
        
        data = response.get("data", {})
        
        return TokenInfo(
            address=data.get("address", token_address),
            name=data.get("name", "Unknown"),
            symbol=data.get("symbol", "UNKNOWN"),
            price_usd=float(data.get("price", 0)),
            price_change_24h=float(data.get("price_change_24h", 0)),
            volume_24h=float(data.get("volume_24h", 0)),
            liquidity_usd=float(data.get("liquidity", 0)),
            market_cap=float(data.get("market_cap", 0)),
            holder_count=int(data.get("holder_count", 0)),
            security_score=float(data.get("security_score", 0)),
            gmgn_score=float(data.get("gmgn_score", 0))
        )
    
    async def get_token_security(self, token_address: str) -> Dict[str, Any]:
        """
        Get token security analysis
        
        Args:
            token_address: Token mint address
            
        Returns:
            Security analysis including rug-pull risks, honeypot check, etc.
        """
        endpoint = "/v1/token/security"
        params = {"address": token_address}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=600)
        
        return response.get("data", {})
    
    async def get_token_holders(self, token_address: str, limit: int = 100) -> List[Dict]:
        """
        Get token holder distribution
        
        Args:
            token_address: Token mint address
            limit: Number of holders to retrieve
            
        Returns:
            List of holder information
        """
        endpoint = "/v1/token/holders"
        params = {"address": token_address, "limit": limit}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=300)
        
        return response.get("data", {}).get("holders", [])
    
    # ==================== SMART MONEY TRACKING ====================
    
    async def get_smart_money_wallets(self, limit: int = 50) -> List[SmartMoneyWallet]:
        """
        Get list of top smart money wallets
        
        Args:
            limit: Number of wallets to retrieve
            
        Returns:
            List of SmartMoneyWallet objects
        """
        endpoint = "/v1/smart-money/top"
        params = {"limit": limit}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=3600)
        
        wallets = []
        for data in response.get("data", []):
            wallet = SmartMoneyWallet(
                address=data.get("address", ""),
                label=data.get("label", "Unknown"),
                win_rate=float(data.get("win_rate", 0)),
                total_pnl=float(data.get("total_pnl", 0)),
                total_trades=int(data.get("total_trades", 0)),
                avg_hold_time=float(data.get("avg_hold_time", 0)),
                recent_trades=data.get("recent_trades", []),
                top_tokens=data.get("top_tokens", [])
            )
            wallets.append(wallet)
        
        return wallets
    
    async def track_wallet(self, wallet_address: str) -> WalletAnalysis:
        """
        Analyze a specific wallet
        
        Args:
            wallet_address: Solana wallet address to analyze
            
        Returns:
            Comprehensive WalletAnalysis
        """
        endpoint = "/v1/wallet/analyze"
        params = {"address": wallet_address}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=600)
        data = response.get("data", {})
        
        return WalletAnalysis(
            address=wallet_address,
            total_value_usd=float(data.get("total_value", 0)),
            total_pnl=float(data.get("total_pnl", 0)),
            win_rate=float(data.get("win_rate", 0)),
            total_trades=int(data.get("total_trades", 0)),
            profitable_trades=int(data.get("profitable_trades", 0)),
            losing_trades=int(data.get("losing_trades", 0)),
            avg_profit=float(data.get("avg_profit", 0)),
            avg_loss=float(data.get("avg_loss", 0)),
            largest_win=float(data.get("largest_win", 0)),
            largest_loss=float(data.get("largest_loss", 0)),
            avg_hold_time=float(data.get("avg_hold_time", 0)),
            favorite_tokens=data.get("favorite_tokens", []),
            recent_activity=data.get("recent_activity", []),
            risk_score=float(data.get("risk_score", 0)),
            is_smart_money=data.get("is_smart_money", False),
            labels=data.get("labels", [])
        )
    
    async def get_wallet_recent_trades(
        self, 
        wallet_address: str, 
        limit: int = 20
    ) -> List[Dict]:
        """
        Get recent trades for a wallet
        
        Args:
            wallet_address: Wallet to track
            limit: Number of trades to retrieve
            
        Returns:
            List of recent trade records
        """
        endpoint = "/v1/wallet/trades"
        params = {"address": wallet_address, "limit": limit}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=120)
        
        return response.get("data", {}).get("trades", [])
    
    # ==================== KOL SIGNALS ====================
    
    async def get_kol_signals(self, limit: int = 20) -> List[KOLSignal]:
        """
        Get latest KOL buy/sell signals
        
        Args:
            limit: Number of signals to retrieve
            
        Returns:
            List of KOLSignal objects
        """
        endpoint = "/v1/kol/signals"
        params = {"limit": limit}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=60)
        
        signals = []
        for data in response.get("data", []):
            signal = KOLSignal(
                kol_name=data.get("kol_name", "Unknown"),
                kol_address=data.get("kol_address", ""),
                token_address=data.get("token_address", ""),
                token_symbol=data.get("token_symbol", ""),
                action=SignalType(data.get("action", "buy")),
                amount_usd=float(data.get("amount_usd", 0)),
                timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else datetime.now(),
                confidence=float(data.get("confidence", 0)),
                followers_count=int(data.get("followers_count", 0))
            )
            signals.append(signal)
        
        return signals
    
    async def get_kol_by_name(self, kol_name: str) -> Dict[str, Any]:
        """
        Get information about a specific KOL
        
        Args:
            kol_name: Name or handle of the KOL
            
        Returns:
            KOL profile information
        """
        endpoint = "/v1/kol/profile"
        params = {"name": kol_name}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=1800)
        
        return response.get("data", {})
    
    # ==================== TRADING SIGNALS ====================
    
    async def get_signals(self, token_address: Optional[str] = None, limit: int = 50) -> List[TradeSignal]:
        """
        Get AI-generated trading signals
        
        Args:
            token_address: Optional specific token to get signals for
            limit: Maximum number of signals
            
        Returns:
            List of TradeSignal objects
        """
        endpoint = "/v1/signals"
        params = {"limit": limit}
        if token_address:
            params["token"] = token_address
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=120)
        
        signals = []
        for data in response.get("data", []):
            signal = TradeSignal(
                token_address=data.get("token_address", ""),
                signal_type=SignalType(data.get("signal_type", "hold")),
                confidence=float(data.get("confidence", 0)),
                entry_price=float(data.get("entry_price")) if data.get("entry_price") else None,
                target_price=float(data.get("target_price")) if data.get("target_price") else None,
                stop_loss=float(data.get("stop_loss")) if data.get("stop_loss") else None,
                reason=data.get("reason", ""),
                risk_level=RiskLevel(data.get("risk_level", "medium")),
                timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else datetime.now(),
                expiry=datetime.fromisoformat(data.get("expiry")) if data.get("expiry") else None
            )
            signals.append(signal)
        
        return signals
    
    async def get_trending_tokens(self, limit: int = 20) -> List[TokenInfo]:
        """
        Get currently trending tokens on GMGN
        
        Args:
            limit: Number of tokens to retrieve
            
        Returns:
            List of trending TokenInfo objects
        """
        endpoint = "/v1/trending"
        params = {"limit": limit}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=120)
        
        tokens = []
        for data in response.get("data", []):
            token = TokenInfo(
                address=data.get("address", ""),
                name=data.get("name", "Unknown"),
                symbol=data.get("symbol", "UNK"),
                price_usd=float(data.get("price", 0)),
                price_change_24h=float(data.get("price_change_24h", 0)),
                volume_24h=float(data.get("volume_24h", 0)),
                liquidity_usd=float(data.get("liquidity", 0)),
                market_cap=float(data.get("market_cap", 0)),
                holder_count=int(data.get("holder_count", 0)),
                gmgn_score=float(data.get("gmgn_score", 0))
            )
            tokens.append(token)
        
        return tokens
    
    # ==================== TRADE EXECUTION ====================
    
    async def execute_swap(
        self,
        token_address: str,
        amount_sol: float,
        slippage_bps: int = 50,
        priority_fee: float = 0.00001,
        is_buy: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a swap trade via GMGN
        
        Args:
            token_address: Token to trade
            amount_sol: Amount of SOL to trade
            slippage_bps: Slippage tolerance in basis points (50 = 0.5%)
            priority_fee: Priority fee in SOL
            is_buy: True for buy, False for sell
            
        Returns:
            Transaction result with signature
        """
        if not self.api_key:
            raise GMGNAPIError("API key required for trade execution")
        
        endpoint = "/v1/trade/swap"
        
        payload = {
            "token_address": token_address,
            "amount": str(amount_sol),
            "slippage_bps": slippage_bps,
            "priority_fee": str(priority_fee),
            "side": "buy" if is_buy else "sell",
            "timestamp": int(time.time())
        }
        
        # Add signature for authentication
        signature = self._sign_payload(payload)
        payload["signature"] = signature
        payload["api_key"] = self.api_key
        
        response = await self._request("POST", endpoint, data=payload, use_cache=False)
        
        logger.info(f"Trade executed: {'BUY' if is_buy else 'SELL'} {amount_sol} SOL for {token_address}")
        
        return response.get("data", {})
    
    async def execute_market_order(
        self,
        token_address: str,
        amount_tokens: float,
        side: str = "sell",
        fast_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a market order (faster than regular swap)
        
        Args:
            token_address: Token to trade
            amount_tokens: Amount of tokens to trade
            side: "buy" or "sell"
            fast_mode: Use optimized routing for speed
            
        Returns:
            Transaction result
        """
        if not self.api_key:
            raise GMGNAPIError("API key required for trade execution")
        
        endpoint = "/v1/trade/market"
        
        payload = {
            "token_address": token_address,
            "amount": str(amount_tokens),
            "side": side,
            "fast_mode": fast_mode,
            "timestamp": int(time.time())
        }
        
        signature = self._sign_payload(payload)
        payload["signature"] = signature
        payload["api_key"] = self.api_key
        
        response = await self._request("POST", endpoint, data=payload, use_cache=False)
        
        return response.get("data", {})
    
    def _sign_payload(self, payload: Dict) -> str:
        """
        Sign payload with API key for authentication
        
        Args:
            payload: Request payload
            
        Returns:
            HMAC-SHA256 signature
        """
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.api_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    # ==================== MARKET DATA ====================
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """
        Get overall market overview
        
        Returns:
            Market statistics and trends
        """
        endpoint = "/v1/market/overview"
        
        response = await self._request("GET", endpoint, cache_ttl=300)
        
        return response.get("data", {})
    
    async def get_new_pairs(self, limit: int = 50) -> List[Dict]:
        """
        Get newly created trading pairs
        
        Args:
            limit: Number of pairs to retrieve
            
        Returns:
            List of new pair information
        """
        endpoint = "/v1/market/new-pairs"
        params = {"limit": limit}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=60)
        
        return response.get("data", [])
    
    async def search_tokens(self, query: str, limit: int = 10) -> List[TokenInfo]:
        """
        Search for tokens by name or symbol
        
        Args:
            query: Search query
            limit: Results limit
            
        Returns:
            List of matching tokens
        """
        endpoint = "/v1/search/tokens"
        params = {"q": query, "limit": limit}
        
        response = await self._request("GET", endpoint, params=params, cache_ttl=300)
        
        tokens = []
        for data in response.get("data", []):
            token = TokenInfo(
                address=data.get("address", ""),
                name=data.get("name", "Unknown"),
                symbol=data.get("symbol", "UNK"),
                price_usd=float(data.get("price", 0)),
                price_change_24h=float(data.get("price_change_24h", 0)),
                volume_24h=float(data.get("volume_24h", 0)),
                liquidity_usd=float(data.get("liquidity", 0)),
                market_cap=float(data.get("market_cap", 0)),
                holder_count=int(data.get("holder_count", 0))
            )
            tokens.append(token)
        
        return tokens


class GMGNAPIError(Exception):
    """Custom exception for GMGN API errors."""
    pass


# Convenience function for quick initialization
def create_gmgn_client(api_key: Optional[str] = None) -> GMGNClient:
    """
    Create a GMGN client instance
    
    Args:
        api_key: Optional API key (otherwise uses env var)
        
    Returns:
        GMGNClient instance
    """
    return GMGNClient(api_key=api_key)


if __name__ == "__main__":
    # Example usage
    async def main():
        client = create_gmgn_client()
        
        try:
            # Get trending tokens
            print("🔥 Trending Tokens:")
            trending = await client.get_trending_tokens(limit=5)
            for token in trending:
                print(f"  {token.symbol}: ${token.price_usd:.8f} ({token.price_change_24h:+.2f}%)")
            
            # Get KOL signals
            print("\n📢 Latest KOL Signals:")
            signals = await client.get_kol_signals(limit=5)
            for signal in signals:
                print(f"  {signal.kol_name}: {signal.action.value} {signal.token_symbol} (${signal.amount_usd:.2f})")
            
            # Get smart money wallets
            print("\n💰 Top Smart Money Wallets:")
            wallets = await client.get_smart_money_wallets(limit=5)
            for wallet in wallets:
                print(f"  {wallet.label}: {wallet.win_rate:.1f}% WR, ${wallet.total_pnl:,.2f} PnL")
            
        finally:
            await client.close()
    
    asyncio.run(main())
