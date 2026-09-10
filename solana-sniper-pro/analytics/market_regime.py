"""
Market Regime Detection
Erkennt Marktphasen (Bull, Bear, Sideways) und passt Strategien automatisch an
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class MarketRegime(Enum):
    """Marktphasen"""
    BULL = "bull"  # Aufwärtstrend
    BEAR = "bear"  # Abwärtstrend
    SIDEWAYS = "sideways"  # Seitwärtsbewegung
    VOLATILE = "volatile"  # Hohe Volatilität
    UNKNOWN = "unknown"  # Unklar


@dataclass
class MarketIndicators:
    """Aktuelle Markt-Indikatoren"""
    btc_price: float
    btc_ema_200: float
    btc_trend: str  # "up", "down", "neutral"
    sol_btc_ratio: float
    sol_btc_trend: str  # "rising", "falling", "stable"
    total_market_volume_24h: float
    volume_change_percent: float
    volatility_index: float  # 0-100, höher = volatiler
    fear_greed_index: Optional[int]  # 0-100
    altcoin_season_indicator: float  # 0-100


@dataclass
class RegimeAnalysis:
    """Ergebnis der Marktphasen-Analyse"""
    regime: MarketRegime
    confidence: float  # 0-1
    primary_signal: str
    secondary_signals: List[str]
    recommended_action: str
    strategy_adjustments: Dict[str, Any]
    risk_level: str  # "low", "medium", "high"
    timestamp: datetime


class MarketRegimeDetector:
    """
    Detector für Marktphasen
    
    Analysiert multiple Indikatoren um die aktuelle Marktphase
    zu erkennen und empfiehlt Strategie-Anpassungen.
    
    Attributes:
        data_source: API/Quelle für Marktdaten
        update_interval: Wie oft Daten aktualisiert werden (Sekunden)
    """
    
    def __init__(
        self,
        data_source: Optional[str] = None,
        update_interval: int = 300  # 5 Minuten
    ):
        """
        Initialisiere Market Regime Detector
        
        Args:
            data_source: API-Endpoint für Marktdaten (optional)
            update_interval: Update-Intervall in Sekunden
        """
        self.logger = logging.getLogger(__name__)
        self.data_source = data_source or "https://api.coingecko.com/api/v3"
        self.update_interval = update_interval
        self.last_update: Optional[datetime] = None
        self.cached_indicators: Optional[MarketIndicators] = None
        
        # Thresholds für Regime-Erkennung
        self.thresholds = {
            "btc_trend_threshold": 0.02,  # 2% für Trend-Erkennung
            "volatility_high": 70,  # Volatilität > 70 = hoch
            "volume_increase_threshold": 0.20,  # 20% Volumen-Anstieg
            "altcoin_season_threshold": 60,  # > 60 = Altcoin Season
        }
        
    def fetch_market_data(self) -> MarketIndicators:
        """
        Hole aktuelle Marktdaten von APIs
        
        Returns:
            MarketIndicators mit aktuellen Daten
            
        Note: In der Praxis würden hier echte API-Calls gemacht.
              Für Demo-Zwecke werden simulierte Daten zurückgegeben.
        """
        try:
            # In der Praxis: Echte API-Calls zu CoinGecko, Binance, etc.
            # Beispiel:
            # btc_data = requests.get(f"{self.data_source}/bitcoin").json()
            # sol_data = requests.get(f"{self.data_source}/solana").json()
            
            # Simulierte Daten für Demo (ersetzen durch echte Calls)
            indicators = MarketIndicators(
                btc_price=43500.0,
                btc_ema_200=42000.0,
                btc_trend="up",
                sol_btc_ratio=0.052,
                sol_btc_trend="rising",
                total_market_volume_24h=85_000_000_000,
                volume_change_percent=15.5,
                volatility_index=45.0,
                fear_greed_index=65,
                altcoin_season_indicator=55.0
            )
            
            self.cached_indicators = indicators
            self.last_update = datetime.now()
            
            self.logger.info(f"Marktdaten aktualisiert: BTC ${indicators.btc_price}")
            return indicators
            
        except Exception as e:
            self.logger.error(f"Fehler beim Holen der Marktdaten: {e}")
            
            # Return cached data if available
            if self.cached_indicators:
                return self.cached_indicators
            
            # Return conservative defaults
            return MarketIndicators(
                btc_price=0.0,
                btc_ema_200=0.0,
                btc_trend="neutral",
                sol_btc_ratio=0.0,
                sol_btc_trend="stable",
                total_market_volume_24h=0.0,
                volume_change_percent=0.0,
                volatility_index=50.0,
                fear_greed_index=50,
                altcoin_season_indicator=50.0
            )
    
    def detect_regime(self, indicators: Optional[MarketIndicators] = None) -> RegimeAnalysis:
        """
        Erkenne aktuelle Marktphase basierend auf Indikatoren
        
        Args:
            indicators: Markt-Indikatoren (optional, wird geholt wenn nicht angegeben)
            
        Returns:
            RegimeAnalysis mit erkannter Phase und Empfehlungen
        """
        if not indicators:
            indicators = self.fetch_market_data()
        
        # Sammle Signale
        signals = []
        signal_weights = []
        
        # 1. BTC über/unter 200 EMA
        if indicators.btc_price > indicators.btc_ema_200 * 1.02:
            signals.append(("bull", "BTC über 200 EMA", 0.25))
        elif indicators.btc_price < indicators.btc_ema_200 * 0.98:
            signals.append(("bear", "BTC unter 200 EMA", 0.25))
        else:
            signals.append(("sideways", "BTC nahe 200 EMA", 0.15))
        
        # 2. BTC Trend
        if indicators.btc_trend == "up":
            signals.append(("bull", "BTC Aufwärtstrend", 0.20))
        elif indicators.btc_trend == "down":
            signals.append(("bear", "BTC Abwärtstrend", 0.20))
        else:
            signals.append(("sideways", "BTC seitwärts", 0.10))
        
        # 3. SOL/BTC Ratio (Altcoin Strength)
        if indicators.sol_btc_trend == "rising":
            signals.append(("bull", "SOL/BTC steigend (Altcoin Strength)", 0.15))
        elif indicators.sol_btc_trend == "falling":
            signals.append(("bear", "SOL/BTC fallend", 0.15))
        else:
            signals.append(("sideways", "SOL/BTC stabil", 0.10))
        
        # 4. Volumen-Analyse
        if indicators.volume_change_percent > 20:
            signals.append(("bull", "Hohe Volumenzunahme", 0.15))
        elif indicators.volume_change_percent < -20:
            signals.append(("bear", "Volumenrückgang", 0.15))
        
        # 5. Volatilität
        if indicators.volatility_index > 70:
            signals.append(("volatile", "Sehr hohe Volatilität", 0.20))
        elif indicators.volatility_index < 30:
            signals.append(("sideways", "Niedrige Volatilität", 0.10))
        
        # 6. Fear & Greed Index
        if indicators.fear_greed_index and indicators.fear_greed_index > 70:
            signals.append(("bull", "Extreme Gier (Contrarian: vorsichtig)", 0.10))
        elif indicators.fear_greed_index and indicators.fear_greed_index < 30:
            signals.append(("bear", "Extreme Angst (Contrarian: Chance)", 0.10))
        
        # 7. Altcoin Season
        if indicators.altcoin_season_indicator > 60:
            signals.append(("bull", "Altcoin Season Indikator", 0.15))
        elif indicators.altcoin_season_indicator < 40:
            signals.append(("bear", "Bitcoin Dominance stark", 0.15))
        
        # Berechne gewichtete Stimmen
        regime_scores = {
            "bull": 0.0,
            "bear": 0.0,
            "sideways": 0.0,
            "volatile": 0.0
        }
        
        total_weight = 0.0
        for regime_type, signal_desc, weight in signals:
            regime_scores[regime_type] += weight
            total_weight += weight
        
        # Normalisiere Scores
        if total_weight > 0:
            for regime_type in regime_scores:
                regime_scores[regime_type] /= total_weight
        
        # Bestimme dominante Phase
        dominant_regime = max(regime_scores.items(), key=lambda x: x[1])
        regime_type = dominant_regime[0]
        confidence = dominant_regime[1]
        
        # Mappe zu Enum
        regime_map = {
            "bull": MarketRegime.BULL,
            "bear": MarketRegime.BEAR,
            "sideways": MarketRegime.SIDEWAYS,
            "volatile": MarketRegime.VOLATILE
        }
        detected_regime = regime_map.get(regime_type, MarketRegime.UNKNOWN)
        
        # Generiere Empfehlungen
        recommendations = self._generate_recommendations(detected_regime, indicators)
        
        # Extrahiere Signale für Output
        primary_signal = signals[0][1] if signals else "Keine Signale"
        secondary_signals = [s[1] for s in signals[1:]]
        
        analysis = RegimeAnalysis(
            regime=detected_regime,
            confidence=round(confidence, 2),
            primary_signal=primary_signal,
            secondary_signals=secondary_signals[:5],  # Max 5
            recommended_action=recommendations["action"],
            strategy_adjustments=recommendations["adjustments"],
            risk_level=recommendations["risk_level"],
            timestamp=datetime.now()
        )
        
        self.logger.info(
            f"Marktphase erkannt: {detected_regime.value} "
            f"(Confidence: {confidence:.0%})"
        )
        
        return analysis
    
    def _generate_recommendations(
        self,
        regime: MarketRegime,
        indicators: MarketIndicators
    ) -> Dict[str, Any]:
        """
        Generiere Handlungsempfehlungen basierend auf Marktphase
        
        Args:
            regime: Erkannte Marktphase
            indicators: Aktuelle Indikatoren
            
        Returns:
            Dictionary mit Empfehlungen und Anpassungen
        """
        if regime == MarketRegime.BULL:
            return {
                "action": "AGGRESSIVE_TRADING",
                "risk_level": "medium",
                "adjustments": {
                    "strategy": "aggressiv",
                    "gewinnziel_multiplier": 1.5,  # Höhere TP Ziele
                    "stop_loss_multiplier": 0.8,   # Weiterer SL
                    "position_size_multiplier": 1.3,  # Größere Positionen
                    "max_positions_increase": 2,   # Mehr gleichzeitige Positionen
                    "trailing_stop_looser": True,  # Trailing Stop lockern
                    "nachkauf_enabled": True
                }
            }
        
        elif regime == MarketRegime.BEAR:
            return {
                "action": "DEFENSIVE_OR_PAUSE",
                "risk_level": "high",
                "adjustments": {
                    "strategy": "konservativ",
                    "gewinnziel_multiplier": 0.7,  # Niedrigere TP (schneller mitnehmen)
                    "stop_loss_multiplier": 1.2,   # Engerer SL
                    "position_size_multiplier": 0.5,  # Kleinere Positionen
                    "max_positions_decrease": -2,  # Weniger gleichzeitige Positionen
                    "trading_pause_recommended": True,
                    "only_high_confidence_trades": True,
                    "min_ml_score": 75  # Nur sehr gute Setups
                }
            }
        
        elif regime == MarketRegime.SIDEWAYS:
            return {
                "action": "MEAN_REVERSION_STRATEGY",
                "risk_level": "low",
                "adjustments": {
                    "strategy": "konservativ",
                    "gewinnziel_multiplier": 0.8,  # Schnellere TP
                    "stop_loss_multiplier": 1.0,   # Normaler SL
                    "position_size_multiplier": 1.0,  # Normale Größe
                    "scalping_mode": True,  # Schnellere Trades
                    "range_trading": True,
                    "take_profit_in_steps": True  # Stufenweise Gewinne mitnehmen
                }
            }
        
        elif regime == MarketRegime.VOLATILE:
            return {
                "action": "REDUCE_EXPOSURE",
                "risk_level": "high",
                "adjustments": {
                    "strategy": "konservativ",
                    "position_size_multiplier": 0.3,  # Sehr kleine Positionen
                    "stop_loss_multiplier": 1.5,  # Sehr enger SL
                    "avoid_new_entries": True,
                    "close_open_positions": "partial",  # Teilweise schließen
                    "increase_slippage_tolerance": True,  # Höhere Slippage erwarten
                    "use_limit_orders_only": True  # Keine Market Orders
                }
            }
        
        else:  # UNKNOWN
            return {
                "action": "WAIT_FOR_CLARITY",
                "risk_level": "medium",
                "adjustments": {
                    "strategy": "konservativ",
                    "position_size_multiplier": 0.5,
                    "reduce_frequency": True,
                    "wait_for_confirmation": True
                }
            }
    
    def get_adjusted_strategy(
        self,
        base_strategy: Dict[str, Any],
        regime_analysis: Optional[RegimeAnalysis] = None
    ) -> Dict[str, Any]:
        """
        Passe Strategie basierend auf Marktphase an
        
        Args:
            base_strategy: Basis-Strategie-Konfiguration
            regime_analysis: Aktuelle Regime-Analyse (optional)
            
        Returns:
            Angepasste Strategie-Konfiguration
        """
        if not regime_analysis:
            regime_analysis = self.detect_regime()
        
        adjustments = regime_analysis.strategy_adjustments
        
        # Kopiere Basis-Strategie
        adjusted = base_strategy.copy()
        
        # Wende Multiplikatoren an
        if "gewinnziel_multiplier" in adjustments:
            adjusted["gewinnziel"] = int(
                base_strategy.get("gewinnziel", 100) * adjustments["gewinnziel_multiplier"]
            )
        
        if "stop_loss_multiplier" in adjustments:
            adjusted["stop_loss"] = int(
                base_strategy.get("stop_loss", 30) * adjustments["stop_loss_multiplier"]
            )
        
        if "position_size_multiplier" in adjustments:
            adjusted["einsatz_pro_trade"] = round(
                base_strategy.get("einsatz_pro_trade", 0.1) * adjustments["position_size_multiplier"],
                2
            )
        
        if "max_positions_increase" in adjustments:
            adjusted["max_positionen"] = (
                base_strategy.get("max_positionen", 5) + adjustments["max_positions_increase"]
            )
        elif "max_positions_decrease" in adjustments:
            adjusted["max_positionen"] = max(
                1,
                base_strategy.get("max_positionen", 5) + adjustments["max_positions_decrease"]
            )
        
        # Füge Regime-spezifische Settings hinzu
        adjusted["current_regime"] = regime_analysis.regime.value
        adjusted["regime_confidence"] = regime_analysis.confidence
        adjusted["recommended_action"] = regime_analysis.recommended_action
        
        self.logger.info(
            f"Strategie angepasst für {regime_analysis.regime.value}: "
            f"TP={adjusted['gewinnziel']}%, SL={adjusted['stop_loss']}%"
        )
        
        return adjusted
    
    def should_pause_trading(self, regime_analysis: Optional[RegimeAnalysis] = None) -> bool:
        """
        Prüfe ob Trading pausiert werden sollte
        
        Args:
            regime_analysis: Aktuelle Regime-Analyse (optional)
            
        Returns:
            True wenn Trading pausiert werden sollte
        """
        if not regime_analysis:
            regime_analysis = self.detect_regime()
        
        # Pause in folgenden Fällen:
        # 1. Bear Market mit hoher Confidence
        if (regime_analysis.regime == MarketRegime.BEAR and 
            regime_analysis.confidence > 0.7):
            return True
        
        # 2. Extreme Volatilität
        if regime_analysis.regime == MarketRegime.VOLATILE:
            return True
        
        # 3. Risk Level ist "high" und Empfehlung ist defensiv
        if (regime_analysis.risk_level == "high" and 
            "PAUSE" in regime_analysis.recommended_action):
            return True
        
        return False
    
    def get_risk_assessment(self, regime_analysis: Optional[RegimeAnalysis] = None) -> Dict[str, Any]:
        """
        Gib detaillierte Risiko-Bewertung
        
        Args:
            regime_analysis: Aktuelle Regime-Analyse (optional)
            
        Returns:
            Dictionary mit Risiko-Bewertung
        """
        if not regime_analysis:
            regime_analysis = self.detect_regime()
        
        risk_factors = []
        risk_score = 0  # 0-100, höher = riskanter
        
        # Faktor 1: Marktphase
        if regime_analysis.regime == MarketRegime.BEAR:
            risk_factors.append("Bear Market")
            risk_score += 30
        elif regime_analysis.regime == MarketRegime.VOLATILE:
            risk_factors.append("Hohe Volatilität")
            risk_score += 25
        
        # Faktor 2: Confidence (niedrige Confidence = riskant)
        if regime_analysis.confidence < 0.5:
            risk_factors.append("Niedrige Signal-Confidence")
            risk_score += 15
        
        # Faktor 3: Risk Level
        if regime_analysis.risk_level == "high":
            risk_factors.append("Hohes Risiko-Level")
            risk_score += 20
        
        # Faktor 4: Extreme Empfehlungen
        if "AVOID" in regime_analysis.recommended_action:
            risk_factors.append("Vermeide neue Trades")
            risk_score += 15
        
        assessment = {
            "overall_risk_score": min(100, risk_score),
            "risk_level": regime_analysis.risk_level,
            "risk_factors": risk_factors,
            "recommendation": regime_analysis.recommended_action,
            "should_reduce_position_size": risk_score > 40,
            "should_use_stricter_stops": risk_score > 30,
            "timestamp": regime_analysis.timestamp.isoformat()
        }
        
        self.logger.info(
            f"Risiko-Bewertung: Score {risk_score}/100, "
            f"Faktoren: {', '.join(risk_factors) if risk_factors else 'Keine'}"
        )
        
        return assessment
