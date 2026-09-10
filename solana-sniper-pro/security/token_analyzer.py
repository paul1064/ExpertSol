"""
Erweiterte Token-Analyse für Solana Sniper Pro.

Bietet:
- Social Sentiment Scanner
- Dev Wallet Tracker
- Smart Money Tracker
- Token-Metadata Validator
- Pair Age & Launch Detection
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from core.logger import get_logger

logger = get_logger()


class PairAgeCategory(Enum):
    """Kategorien für Token-Alter."""
    ULTRA_EARLY = "ultra_early"  # < 5 Minuten
    EARLY = "early"  # 5-30 Minuten
    ESTABLISHED = "established"  # > 30 Minuten


@dataclass
class TokenScore:
    """Token-Bewertung mit verschiedenen Scores."""
    address: str
    legitimacy_score: float  # 0-100%
    social_score: float  # 0-100%
    holder_score: float  # 0-100%
    dev_score: float  # 0-100%
    smart_money_score: float  # 0-100%
    overall_score: float  # 0-100%
    risk_level: str  # low, medium, high, critical
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert in Dictionary."""
        return {
            "address": self.address,
            "legitimacy_score": self.legitimacy_score,
            "social_score": self.social_score,
            "holder_score": self.holder_score,
            "dev_score": self.dev_score,
            "smart_money_score": self.smart_money_score,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp.isoformat()
        }


class SocialSentimentScanner:
    """
    Scannt Social Media nach Token-Erwähnungen.
    
    Features:
    - Twitter API Integration
    - Telegram Gruppen-Monitoring
    - Score-System für Sentiment
    """
    
    def __init__(
        self,
        twitter_api_key: Optional[str] = None,
        twitter_api_secret: Optional[str] = None
    ):
        """Initialisiert den Social Sentiment Scanner."""
        self.twitter_api_key = twitter_api_key
        self.twitter_api_secret = twitter_api_secret
        self.mention_cache: Dict[str, List[Dict]] = {}
        
        logger.info("SocialSentimentScanner initialisiert", category="SECURITY")
    
    def scan_twitter_mentions(
        self,
        token_symbol: str,
        token_name: str,
        minutes: int = 10
    ) -> Dict[str, Any]:
        """
        Scannt Twitter nach Token-Erwähnungen.
        
        Args:
            token_symbol: Token Symbol (z.B. "PEPE")
            token_name: Token Name
            minutes: Zeitraum in Minuten
        
        Returns:
            Dictionary mit Mention-Statistiken
        """
        if not REQUESTS_AVAILABLE or not self.twitter_api_key:
            logger.debug("Twitter API nicht verfügbar", category="SECURITY")
            return {"mentions": 0, "score": 0}
        
        try:
            # TODO: Implementiere echte Twitter API v2 Integration
            # Für jetzt Mock-Daten
            mentions = 0
            influencer_mentions = 0
            trending = False
            
            score = (
                mentions * 10 +
                influencer_mentions * 20 +
                (30 if trending else 0)
            )
            
            result = {
                "mentions": mentions,
                "influencer_mentions": influencer_mentions,
                "trending": trending,
                "score": min(score, 100),
                "timeframe_minutes": minutes
            }
            
            logger.debug(f"Twitter Scan für {token_symbol}: {mentions} Mentions", category="SECURITY")
            return result
        
        except Exception as e:
            logger.error(f"Twitter Scan fehlgeschlagen: {str(e)}", category="SECURITY", exc_info=e)
            return {"mentions": 0, "score": 0}
    
    def calculate_social_score(
        self,
        token_symbol: str,
        token_name: str
    ) -> float:
        """
        Berechnet einen Social-Sentiment-Score.
        
        Args:
            token_symbol: Token Symbol
            token_name: Token Name
        
        Returns:
            Score von 0-100
        """
        twitter_data = self.scan_twitter_mentions(token_symbol, token_name)
        return twitter_data.get("score", 0)


class DevWalletTracker:
    """
    Trackt Dev-Wallet-Aktivitäten.
    
    Features:
    - Identifiziert Dev-Wallet (erste Creator-Wallet)
    - Überwacht Verkäufe
    - Benachrichtigung bei großen Verkäufen
    """
    
    def __init__(self, solana_client=None):
        """Initialisiert den Dev Wallet Tracker."""
        self.solana_client = solana_client
        self.dev_wallets: Dict[str, str] = {}  # token_address -> dev_wallet
        self.tracked_wallets: set = set()
        
        logger.info("DevWalletTracker initialisiert", category="SECURITY")
    
    def identify_dev_wallet(self, token_address: str) -> Optional[str]:
        """
        Identifiziert die Dev-Wallet eines Tokens.
        
        Args:
            token_address: Adresse des Tokens
        
        Returns:
            Dev-Wallet-Adresse oder None
        """
        # TODO: Implementiere echte Solana RPC Abfrage
        # Für jetzt Mock-Daten
        dev_wallet = f"mock_dev_wallet_{token_address[:8]}"
        self.dev_wallets[token_address] = dev_wallet
        self.tracked_wallets.add(dev_wallet)
        
        logger.debug(f"Dev-Wallet identifiziert für {token_address}: {dev_wallet}", category="SECURITY")
        return dev_wallet
    
    def check_dev_sell_activity(
        self,
        token_address: str,
        sell_amount_usd: float,
        total_liquidity_usd: float
    ) -> Tuple[bool, str]:
        """
        Prüft ob Dev große Mengen verkauft.
        
        Args:
            token_address: Adresse des Tokens
            sell_amount_usd: Verkaufte Menge in USD
            total_liquidity_usd: Gesamte Liquidität in USD
        
        Returns:
            (is_warning, message)
        """
        if total_liquidity_usd == 0:
            return False, ""
        
        sell_percentage = (sell_amount_usd / total_liquidity_usd) * 100
        
        if sell_percentage > 5:
            warning = f"⚠️ Dev verkauft {sell_percentage:.1f}% der Liquidität!"
            logger.warning(warning, category="SECURITY")
            return True, warning
        
        return False, ""


class SmartMoneyTracker:
    """
    Trackt Smart Money Wallets.
    
    Features:
    - Whitelist von erfolgreichen Wallets
    - Tracking von Käufen/Verkäufen
    - Win-Rate Berechnung
    """
    
    def __init__(self):
        """Initialisiert den Smart Money Tracker."""
        # Beispiel Smart Money Wallets (müsste mit echten Daten gefüllt werden)
        self.smart_money_wallets: Dict[str, Dict] = {
            "wallet1": {"win_rate": 75.5, "total_trades": 150, "pnl_usd": 125000},
            "wallet2": {"win_rate": 68.2, "total_trades": 89, "pnl_usd": 87000},
        }
        
        logger.info("SmartMoneyTracker initialisiert", category="SECURITY")
    
    def add_smart_wallet(self, wallet_address: str, win_rate: float, total_trades: int) -> None:
        """Fügt eine Smart Money Wallet hinzu."""
        self.smart_money_wallets[wallet_address] = {
            "win_rate": win_rate,
            "total_trades": total_trades,
            "pnl_usd": 0
        }
        logger.debug(f"Smart Wallet hinzugefügt: {wallet_address}", category="SECURITY")
    
    def is_smart_money(self, wallet_address: str) -> bool:
        """Prüft ob eine Wallet als Smart Money gilt."""
        return wallet_address in self.smart_money_wallets
    
    def get_smart_money_score(self, wallet_address: str) -> float:
        """
        Berechnet einen Score basierend auf Smart Money Aktivität.
        
        Args:
            wallet_address: Zu prüfende Wallet
        
        Returns:
            Score von 0-100
        """
        if wallet_address not in self.smart_money_wallets:
            return 0
        
        wallet_data = self.smart_money_wallets[wallet_address]
        win_rate = wallet_data.get("win_rate", 0)
        total_trades = wallet_data.get("total_trades", 0)
        
        # Score basiert auf Win-Rate und Erfahrung
        base_score = win_rate
        experience_bonus = min(total_trades / 10, 20)  # Max 20 Bonus-Punkte
        
        return min(base_score + experience_bonus, 100)


class TokenMetadataValidator:
    """
    Validiert Token-Metadaten.
    
    Features:
    - Prüft Logo, Beschreibung, Website, Social-Links
    - Berechnet Legitimacy-Score
    - Filtert Low-Quality Tokens
    """
    
    def __init__(self):
        """Initialisiert den Metadata Validator."""
        logger.info("TokenMetadataValidator initialisiert", category="SECURITY")
    
    def validate_metadata(self, metadata_uri: str) -> Dict[str, Any]:
        """
        Validiert Token-Metadaten von einer URI.
        
        Args:
            metadata_uri: URI zu den Metadaten
        
        Returns:
            Dictionary mit Validierungsergebnissen
        """
        if not REQUESTS_AVAILABLE:
            return {"valid": False, "score": 0, "reason": "requests nicht verfügbar"}
        
        try:
            response = requests.get(metadata_uri, timeout=5)
            if response.status_code != 200:
                return {"valid": False, "score": 0, "reason": "HTTP Error"}
            
            metadata = response.json()
            
            # Prüfe erforderliche Felder
            has_logo = bool(metadata.get("image"))
            has_description = bool(metadata.get("description")) and len(metadata.get("description", "")) > 20
            has_website = "website" in metadata or "external_url" in metadata
            has_twitter = bool(metadata.get("twitter"))
            has_telegram = bool(metadata.get("telegram"))
            
            # Score berechnen
            score = 0
            if has_logo: score += 25
            if has_description: score += 25
            if has_website: score += 20
            if has_twitter: score += 15
            if has_telegram: score += 15
            
            result = {
                "valid": True,
                "score": score,
                "has_logo": has_logo,
                "has_description": has_description,
                "has_website": has_website,
                "has_twitter": has_twitter,
                "has_telegram": has_telegram,
                "metadata": metadata
            }
            
            logger.debug(f"Metadata-Score: {score}/100", category="SECURITY")
            return result
        
        except Exception as e:
            logger.error(f"Metadata-Validierung fehlgeschlagen: {str(e)}", category="SECURITY", exc_info=e)
            return {"valid": False, "score": 0, "reason": str(e)}
    
    def calculate_legitimacy_score(self, token_address: str, metadata_uri: str) -> float:
        """
        Berechnet einen Legitimacy-Score für einen Token.
        
        Args:
            token_address: Adresse des Tokens
            metadata_uri: URI zu den Metadaten
        
        Returns:
            Score von 0-100
        """
        validation = self.validate_metadata(metadata_uri)
        return validation.get("score", 0)


class PairAgeDetector:
    """
    Erkennt das Alter eines Trading-Pairs.
    
    Features:
- Holt Pair-Creation-Date von Raydium/Pump.fun
- Kategorisiert nach Alter
- Passt Strategie-Empfehlungen an
    """
    
    def __init__(self, solana_client=None):
        """Initialisiert den Pair Age Detector."""
        self.solana_client = solana_client
        self.pair_cache: Dict[str, datetime] = {}
        
        logger.info("PairAgeDetector initialisiert", category="SECURITY")
    
    def get_pair_creation_date(self, token_address: str, pool_address: str) -> Optional[datetime]:
        """
        Holt das Erstellungsdatum eines Pools.
        
        Args:
            token_address: Adresse des Tokens
            pool_address: Adresse des Liquidity-Pools
        
        Returns:
            Erstellungsdatum oder None
        """
        # TODO: Implementiere echte Solana RPC Abfrage
        # Für jetzt Mock-Daten
        creation_date = datetime.utcnow() - timedelta(minutes=15)
        self.pair_cache[token_address] = creation_date
        
        logger.debug(f"Pair erstellt am: {creation_date}", category="SECURITY")
        return creation_date
    
    def categorize_pair_age(self, token_address: str) -> PairAgeCategory:
        """
        Kategorisiert ein Pair nach Alter.
        
        Args:
            token_address: Adresse des Tokens
        
        Returns:
            PairAgeCategory
        """
        creation_date = self.pair_cache.get(token_address)
        
        if not creation_date:
            # Default zu established wenn unbekannt
            return PairAgeCategory.ESTABLISHED
        
        age_minutes = (datetime.utcnow() - creation_date).total_seconds() / 60
        
        if age_minutes < 5:
            return PairAgeCategory.ULTRA_EARLY
        elif age_minutes < 30:
            return PairAgeCategory.EARLY
        else:
            return PairAgeCategory.ESTABLISHED
    
    def get_age_category_strategies(self, category: PairAgeCategory) -> Dict[str, Any]:
        """
        Gibt Strategie-Empfehlungen basierend auf dem Alter.
        
        Args:
            category: PairAgeCategory
        
        Returns:
            Dictionary mit Strategie-Empfehlungen
        """
        strategies = {
            PairAgeCategory.ULTRA_EARLY: {
                "recommended_strategy": "jackpot",
                "stop_loss": 35,
                "take_profit": 500,
                "position_size_percent": 30,
                "warning": "Extrem hohes Risiko!"
            },
            PairAgeCategory.EARLY: {
                "recommended_strategy": "aggressiv",
                "stop_loss": 40,
                "take_profit": 250,
                "position_size_percent": 50,
                "warning": "Hohes Risiko"
            },
            PairAgeCategory.ESTABLISHED: {
                "recommended_strategy": "konservativ",
                "stop_loss": 30,
                "take_profit": 100,
                "position_size_percent": 70,
                "warning": "Moderates Risiko"
            }
        }
        
        return strategies.get(category, strategies[PairAgeCategory.ESTABLISHED])


class TokenAnalyzer:
    """
    Hauptklasse für Token-Analyse.
    
    Kombiniert alle Analyse-Komponenten zu einem Gesamt-Score.
    """
    
    def __init__(self, solana_client=None, config: Optional[Dict] = None):
        """
        Initialisiert den Token Analyzer.
        
        Args:
            solana_client: Solana RPC Client
            config: Konfigurations-Dictionary
        """
        self.solana_client = solana_client
        self.config = config or {}
        
        self.sentiment_scanner = SocialSentimentScanner(
            twitter_api_key=self.config.get("twitter_api_key"),
            twitter_api_secret=self.config.get("twitter_api_secret")
        )
        
        self.dev_tracker = DevWalletTracker(solana_client)
        self.smart_money_tracker = SmartMoneyTracker()
        self.metadata_validator = TokenMetadataValidator()
        self.pair_age_detector = PairAgeDetector(solana_client)
        
        # Smart Money Wallets laden
        self._load_smart_money_wallets()
        
        logger.info("TokenAnalyzer initialisiert", category="SECURITY")
    
    def _load_smart_money_wallets(self) -> None:
        """Lädt Smart Money Wallets aus Config."""
        smart_wallets = self.config.get("smart_money_wallets", [])
        for wallet in smart_wallets:
            self.smart_money_tracker.add_smart_wallet(
                wallet["address"],
                wallet.get("win_rate", 50),
                wallet.get("total_trades", 0)
            )
    
    def analyze_token(
        self,
        token_address: str,
        token_name: str,
        token_symbol: str,
        metadata_uri: Optional[str] = None,
        pool_address: Optional[str] = None
    ) -> TokenScore:
        """
        Führt eine komplette Token-Analyse durch.
        
        Args:
            token_address: Adresse des Tokens
            token_name: Name des Tokens
            token_symbol: Symbol des Tokens
            metadata_uri: URI zu den Metadaten
            pool_address: Adresse des Liquidity-Pools
        
        Returns:
            TokenScore-Objekt
        """
        logger.info(f"Analysiere Token: {token_symbol} ({token_address})", category="SECURITY")
        
        # Einzelne Scores berechnen
        legitimacy_score = 0
        if metadata_uri:
            legitimacy_score = self.metadata_validator.calculate_legitimacy_score(
                token_address, metadata_uri
            )
        
        social_score = self.sentiment_scanner.calculate_social_score(token_symbol, token_name)
        
        # Holder Score (Mock - wird von rug_pull_checker berechnet)
        holder_score = 70  # Default Wert
        
        # Dev Score
        dev_wallet = self.dev_tracker.identify_dev_wallet(token_address)
        dev_score = 50  # Default, wird bei Aktivität angepasst
        
        # Smart Money Score
        smart_money_score = 0  # Default
        
        # Overall Score berechnen (gewichtet)
        weights = {
            "legitimacy": 0.30,
            "social": 0.20,
            "holder": 0.20,
            "dev": 0.15,
            "smart_money": 0.15
        }
        
        overall_score = (
            legitimacy_score * weights["legitimacy"] +
            social_score * weights["social"] +
            holder_score * weights["holder"] +
            dev_score * weights["dev"] +
            smart_money_score * weights["smart_money"]
        )
        
        # Risk Level bestimmen
        if overall_score >= 80:
            risk_level = "low"
        elif overall_score >= 60:
            risk_level = "medium"
        elif overall_score >= 40:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        score = TokenScore(
            address=token_address,
            legitimacy_score=legitimacy_score,
            social_score=social_score,
            holder_score=holder_score,
            dev_score=dev_score,
            smart_money_score=smart_money_score,
            overall_score=overall_score,
            risk_level=risk_level
        )
        
        logger.info(
            f"Token-Score: {overall_score:.1f}/100 (Risiko: {risk_level})",
            category="SECURITY"
        )
        
        return score
    
    def should_trade_token(self, token_score: TokenScore, min_score: float = 50) -> Tuple[bool, str]:
        """
        Entscheidet ob ein Token gehandelt werden sollte.
        
        Args:
            token_score: TokenScore-Objekt
            min_score: Minimaler Score für Trade
        
        Returns:
            (should_trade, reason)
        """
        if token_score.overall_score < min_score:
            return False, f"Score zu niedrig: {token_score.overall_score:.1f} < {min_score}"
        
        if token_score.risk_level == "critical":
            return False, "Kritisches Risiko"
        
        return True, f"Score: {token_score.overall_score:.1f}, Risiko: {token_score.risk_level}"


# Globale TokenAnalyzer-Instanz
_token_analyzer: Optional[TokenAnalyzer] = None


def get_token_analyzer() -> Optional[TokenAnalyzer]:
    """Gibt die globale TokenAnalyzer-Instanz zurück."""
    global _token_analyzer
    return _token_analyzer


def initialize_token_analyzer(
    solana_client=None,
    config: Optional[Dict] = None
) -> TokenAnalyzer:
    """
    Initialisiert den globalen TokenAnalyzer.
    
    Args:
        solana_client: Solana RPC Client
        config: Konfigurations-Dictionary
    
    Returns:
        TokenAnalyzer-Instanz
    """
    global _token_analyzer
    _token_analyzer = TokenAnalyzer(solana_client=solana_client, config=config)
    return _token_analyzer
