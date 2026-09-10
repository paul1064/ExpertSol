"""
Machine Learning Token Scorer
Bewertet Tokens basierend auf historischen Daten und ML-Modellen
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os


@dataclass
class TokenFeatures:
    """Features für ML-Modell"""
    liquidity_usd: float
    holder_count: int
    token_age_minutes: float
    social_mentions_10min: int
    dev_wallet_activity: float  # 0-1 Scale
    lp_lock_days: int
    top_10_holder_percentage: float
    tax_percentage: float
    metadata_completeness_score: float  # 0-100
    volume_24h_usd: float
    price_change_5min: float
    unique_buyers_10min: int
    unique_sellers_10min: int
    large_transactions_10min: int


@dataclass
class MLScore:
    """ML-Score Ergebnis"""
    score: float  # 0-100
    confidence: float  # 0-1
    prediction: str  # "profitable", "neutral", "risky"
    expected_roi: float  # Erwartete ROI in %
    risk_level: str  # "low", "medium", "high", "extreme"
    similar_tokens_performance: float  # Durchschnittliche Performance ähnlicher Tokens
    key_factors: List[str]  # Wichtigste Einflussfaktoren


class MLTokenScorer:
    """
    Machine Learning Token Scorer
    
    Bewertet Tokens basierend auf multiplen Features
    und historischen Erfolgs Mustern.
    
    Attributes:
        model_path: Pfad zum trainierten ML-Modell
        historical_data_path: Pfad zu historischen Daten
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        historical_data_path: Optional[str] = None
    ):
        """
        Initialisiere ML Scorer
        
        Args:
            model_path: Pfad zum gespeicherten Modell (optional)
            historical_data_path: Pfad zu Trainingsdaten (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path or "data/ml_model.json"
        self.historical_data_path = historical_data_path or "data/historical_trades.json"
        
        # Feature Weights (werden durch Training optimiert)
        self.feature_weights = self._load_or_initialize_weights()
        
        # Historische Daten für Vergleich
        self.historical_data: List[Dict[str, Any]] = []
        self._load_historical_data()
        
        # Success Thresholds
        self.profitable_threshold = 65.0  # Score > 65 = profitabel erwartet
        self.risky_threshold = 40.0  # Score < 40 = riskant
        
    def _load_or_initialize_weights(self) -> Dict[str, float]:
        """
        Lade Feature-Weights oder initialisiere mit Defaults
        
        Returns:
            Dictionary mit Feature-Namen und Gewichten
        """
        default_weights = {
            "liquidity_usd": 0.15,
            "holder_count": 0.10,
            "token_age_minutes": 0.08,
            "social_mentions_10min": 0.12,
            "dev_wallet_activity": 0.10,
            "lp_lock_days": 0.15,
            "top_10_holder_percentage": -0.12,  # Negativ: hohe Konzentration = schlecht
            "tax_percentage": -0.08,  # Negativ: hohe Taxes = schlecht
            "metadata_completeness_score": 0.07,
            "volume_24h_usd": 0.10,
            "price_change_5min": 0.05,
            "unique_buyers_10min": 0.08,
            "unique_sellers_10min": -0.05,  # Negativ: viele Verkäufer = schlecht
            "large_transactions_10min": 0.07
        }
        
        # Versuch, gespeicherte Weights zu laden
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'r') as f:
                    saved_data = json.load(f)
                    weights = saved_data.get("feature_weights", default_weights)
                    self.logger.info(f"ML-Modell geladen von {self.model_path}")
                    return weights
            except Exception as e:
                self.logger.warning(f"Fehler beim Laden des Modells: {e}. Verwende Default-Weights.")
        
        self.logger.info("Verwende initialisierte Default-Feature-Weights")
        return default_weights
    
    def _load_historical_data(self):
        """Lade historische Trade-Daten für Analyse"""
        if os.path.exists(self.historical_data_path):
            try:
                with open(self.historical_data_path, 'r') as f:
                    self.historical_data = json.load(f)
                self.logger.info(f"{len(self.historical_data)} historische Trades geladen")
            except Exception as e:
                self.logger.warning(f"Fehler beim Laden historischer Daten: {e}")
        else:
            self.logger.info("Keine historischen Daten gefunden. Starte mit leerem Datensatz.")
    
    def calculate_score(self, features: TokenFeatures) -> MLScore:
        """
        Berechne ML-Score für einen Token
        
        Args:
            features: Token-Features für die Bewertung
            
        Returns:
            MLScore Objekt mit Score und Analyse
        """
        # Normalisiere Features auf 0-1 Scale
        normalized_features = self._normalize_features(features)
        
        # Berechne gewichteten Score
        raw_score = 0.0
        for feature_name, weight in self.feature_weights.items():
            feature_value = getattr(normalized_features, feature_name, 0.0)
            raw_score += feature_value * weight
        
        # Skaliere auf 0-100
        score = max(0, min(100, raw_score * 100))
        
        # Bestimme Prediction
        if score >= self.profitable_threshold:
            prediction = "profitable"
        elif score >= self.risky_threshold:
            prediction = "neutral"
        else:
            prediction = "risky"
        
        # Berechne Confidence basierend auf Datenqualität
        confidence = self._calculate_confidence(features)
        
        # Schätze erwartete ROI
        expected_roi = self._estimate_expected_roi(score, features)
        
        # Bestimme Risk Level
        risk_level = self._determine_risk_level(score, features)
        
        # Finde ähnliche Tokens und deren Performance
        similar_performance = self._find_similar_tokens_performance(features)
        
        # Identifiziere Key Factors
        key_factors = self._identify_key_factors(normalized_features)
        
        ml_score = MLScore(
            score=round(score, 2),
            confidence=round(confidence, 2),
            prediction=prediction,
            expected_roi=round(expected_roi, 2),
            risk_level=risk_level,
            similar_tokens_performance=round(similar_performance, 2),
            key_factors=key_factors
        )
        
        self.logger.info(
            f"ML-Score berechnet: {ml_score.score}/100 "
            f"({ml_score.prediction}, Confidence: {ml_score.confidence:.0%})"
        )
        
        return ml_score
    
    def _normalize_features(self, features: TokenFeatures) -> TokenFeatures:
        """
        Normalisiere Features auf 0-1 Scale
        
        Args:
            features: Rohe Features
            
        Returns:
            Normalisierte Features
        """
        # Min-Max Normalization mit sinnvollen Grenzen
        normalized = TokenFeatures(
            liquidity_usd=min(1.0, features.liquidity_usd / 1_000_000),  # Max 1M
            holder_count=min(1.0, features.holder_count / 10_000),  # Max 10k
            token_age_minutes=min(1.0, features.token_age_minutes / 1440),  # Max 1 Tag
            social_mentions_10min=min(1.0, features.social_mentions_10min / 100),  # Max 100
            dev_wallet_activity=features.dev_wallet_activity,  # Bereits 0-1
            lp_lock_days=min(1.0, features.lp_lock_days / 365),  # Max 1 Jahr
            top_10_holder_percentage=features.top_10_holder_percentage / 100,  # Prozent zu 0-1
            tax_percentage=features.tax_percentage / 100,  # Prozent zu 0-1
            metadata_completeness_score=features.metadata_completeness_score / 100,
            volume_24h_usd=min(1.0, features.volume_24h_usd / 5_000_000),  # Max 5M
            price_change_5min=(features.price_change_5min + 100) / 200,  # -100% bis +100% zu 0-1
            unique_buyers_10min=min(1.0, features.unique_buyers_10min / 500),  # Max 500
            unique_sellers_10min=min(1.0, features.unique_sellers_10min / 500),
            large_transactions_10min=min(1.0, features.large_transactions_10min / 50)  # Max 50
        )
        
        return normalized
    
    def _calculate_confidence(self, features: TokenFeatures) -> float:
        """
        Berechne Confidence-Score basierend auf Datenverfügbarkeit
        
        Args:
            features: Token-Features
            
        Returns:
            Confidence zwischen 0 und 1
        """
        confidence_factors = []
        
        # Mehr Daten = höhere Confidence
        if features.holder_count > 100:
            confidence_factors.append(0.9)
        elif features.holder_count > 50:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.4)
        
        if features.liquidity_usd > 50_000:
            confidence_factors.append(0.9)
        elif features.liquidity_usd > 10_000:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.4)
        
        if features.metadata_completeness_score > 80:
            confidence_factors.append(0.9)
        elif features.metadata_completeness_score > 50:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.4)
        
        # Token Age beeinflusst Confidence
        if features.token_age_minutes > 60:
            confidence_factors.append(0.9)
        elif features.token_age_minutes > 10:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _estimate_expected_roi(self, score: float, features: TokenFeatures) -> float:
        """
        Schätze erwartete ROI basierend auf Score und Features
        
        Args:
            score: ML-Score (0-100)
            features: Token-Features
            
        Returns:
            Erwartete ROI in Prozent
        """
        # Basis-ROI aus Score ableiten
        base_roi = (score - 50) * 3  # Score 50 = 0% ROI, Score 100 = 150% ROI
        
        # Anpassungen basierend auf Features
        if features.lp_lock_days > 90:
            base_roi += 10  # Gelockte LP = positiver
        
        if features.top_10_holder_percentage < 30:
            base_roi += 15  # Gute Dezentralisierung
        
        if features.social_mentions_10min > 50:
            base_roi += 20  # Hoher Social Hype
        
        if features.tax_percentage > 10:
            base_roi -= 15  # Hohe Taxes negativ
        
        # Begrenze auf realistische Werte
        return max(-100, min(500, base_roi))
    
    def _determine_risk_level(self, score: float, features: TokenFeatures) -> str:
        """
        Bestimme Risk Level
        
        Args:
            score: ML-Score
            features: Token-Features
            
        Returns:
            Risk Level String
        """
        # Extreme Risiken erkennen
        if features.top_10_holder_percentage > 70:
            return "extreme"
        
        if features.lp_lock_days == 0:
            return "extreme"
        
        if features.tax_percentage > 20:
            return "extreme"
        
        # Normale Risikostufen
        if score < 30:
            return "high"
        elif score < 50:
            return "medium"
        elif score < 70:
            return "low"
        else:
            return "low"
    
    def _find_similar_tokens_performance(self, features: TokenFeatures) -> float:
        """
        Finde ähnliche Tokens und berechne deren durchschnittliche Performance
        
        Args:
            features: Aktuelle Token-Features
            
        Returns:
            Durchschnittliche ROI ähnlicher Tokens
        """
        if not self.historical_data:
            return 0.0  # Keine historischen Daten
        
        similar_tokens = []
        
        for historical_token in self.historical_data:
            # Vereinfachte Ähnlichkeitsprüfung
            hist_features = historical_token.get("features", {})
            
            # Prüfe ob Features ähnlich sind
            liquidity_diff = abs(hist_features.get("liquidity_usd", 0) - features.liquidity_usd)
            holder_diff = abs(hist_features.get("holder_count", 0) - features.holder_count)
            
            # Wenn innerhalb von 50% Unterschied
            if (liquidity_diff < features.liquidity_usd * 0.5 and
                holder_diff < features.holder_count * 0.5):
                similar_tokens.append(historical_token)
        
        if not similar_tokens:
            return 0.0
        
        # Durchschnittliche ROI berechnen
        rois = [t.get("roi_percent", 0) for t in similar_tokens]
        avg_roi = sum(rois) / len(rois)
        
        self.logger.debug(f"{len(similar_tokens)} ähnliche Tokens gefunden, Avg ROI: {avg_roi:.2f}%")
        
        return avg_roi
    
    def _identify_key_factors(self, features: TokenFeatures) -> List[str]:
        """
        Identifiziere die wichtigsten Einflussfaktoren
        
        Args:
            features: Normalisierte Features
            
        Returns:
            Liste der wichtigsten Faktoren als Strings
        """
        factors = []
        
        # Top positive Faktoren
        if features.lp_lock_days > 0.5:
            factors.append("✅ LP langfristig gelockt")
        
        if features.liquidity_usd > 0.5:
            factors.append("✅ Hohe Liquidität")
        
        if features.social_mentions_10min > 0.5:
            factors.append("✅ Starker Social Hype")
        
        if features.unique_buyers_10min > 0.5:
            factors.append("✅ Viele neue Käufer")
        
        # Top negative Faktoren
        if features.top_10_holder_percentage > 0.6:
            factors.append("⚠️ Hohe Holder-Konzentration")
        
        if features.tax_percentage > 0.1:
            factors.append("⚠️ Hohe Transaction Taxes")
        
        if features.unique_sellers_10min > 0.5:
            factors.append("⚠️ Viele Verkäufer")
        
        if features.dev_wallet_activity < 0.3:
            factors.append("⚠️ Dev-Wallet inaktiv/verdächtig")
        
        return factors[:5]  # Max 5 Faktoren
    
    def update_weights_from_results(self, training_data: List[Dict[str, Any]]):
        """
        Update Feature-Weights basierend auf neuen Ergebnissen
        
        Args:
            training_data: Liste von historischen Trades mit Features und Results
        """
        self.logger.info(f"Update ML-Weights mit {len(training_data)} neuen Datensätzen")
        
        # Einfache Gewichtsanpassung basierend auf Korrelation
        # In der Praxis: Verwende Gradient Descent oder Random Forest Feature Importance
        
        for feature_name in self.feature_weights.keys():
            # Berechne Korrelation zwischen Feature und Erfolg
            correlation = self._calculate_feature_correlation(training_data, feature_name)
            
            # Adjustiere Weight leicht in Richtung der Korrelation
            current_weight = self.feature_weights[feature_name]
            adjustment = correlation * 0.1  # Langsame Anpassung
            new_weight = current_weight + adjustment
            
            # Begrenze extreme Werte
            self.feature_weights[feature_name] = max(-0.5, min(0.5, new_weight))
        
        # Speichere aktualisierte Weights
        self._save_weights()
    
    def _calculate_feature_correlation(
        self,
        training_data: List[Dict[str, Any]],
        feature_name: str
    ) -> float:
        """
        Berechne Korrelation zwischen Feature und Trading-Erfolg
        
        Args:
            training_data: Trainingsdaten
            feature_name: Name des Features
            
        Returns:
            Korrelationskoeffizient (-1 bis 1)
        """
        if not training_data:
            return 0.0
        
        feature_values = []
        success_values = []
        
        for data in training_data:
            features = data.get("features", {})
            roi = data.get("roi_percent", 0)
            
            if feature_name in features:
                feature_values.append(features[feature_name])
                success_values.append(1 if roi > 0 else 0)
        
        if len(feature_values) < 10:
            return 0.0  # Zu wenig Daten
        
        # Einfache Korrelationsberechnung
        # In der Praxis: Verwende numpy.corrcoef oder scipy.stats.pearsonr
        mean_x = sum(feature_values) / len(feature_values)
        mean_y = sum(success_values) / len(success_values)
        
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(feature_values, success_values))
        denominator_x = sum((x - mean_x) ** 2 for x in feature_values) ** 0.5
        denominator_y = sum((y - mean_y) ** 2 for y in success_values) ** 0.5
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        correlation = numerator / (denominator_x * denominator_y)
        
        return correlation
    
    def _save_weights(self):
        """Speichere aktuelle Feature-Weights"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            model_data = {
                "feature_weights": self.feature_weights,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(self.model_path, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            self.logger.info(f"ML-Modell gespeichert nach {self.model_path}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des Modells: {e}")
    
    def get_recommendation(self, features: TokenFeatures) -> Dict[str, Any]:
        """
        Gib Handlungsempfehlung basierend auf ML-Score
        
        Args:
            features: Token-Features
            
        Returns:
            Empfehlung als Dictionary
        """
        ml_score = self.calculate_score(features)
        
        recommendation = {
            "action": "HOLD",
            "confidence": ml_score.confidence,
            "score": ml_score.score,
            "reasoning": [],
            "suggested_position_size": 0.0
        }
        
        if ml_score.score >= 75 and ml_score.confidence >= 0.7:
            recommendation["action"] = "STRONG_BUY"
            recommendation["suggested_position_size"] = 0.3  # 30% der maximalen Position
            recommendation["reasoning"].append("Sehr hoher Score mit guter Confidence")
            
        elif ml_score.score >= 65:
            recommendation["action"] = "BUY"
            recommendation["suggested_position_size"] = 0.2
            recommendation["reasoning"].append("Guter Score über Profitabilitäts-Threshold")
            
        elif ml_score.score >= 50:
            recommendation["action"] = "HOLD"
            recommendation["suggested_position_size"] = 0.1
            recommendation["reasoning"].append("Neutraler Score, abwarten empfohlen")
            
        elif ml_score.score >= 40:
            recommendation["action"] = "AVOID"
            recommendation["reasoning"].append("Unterhalb des neutralen Scores")
            
        else:
            recommendation["action"] = "STRONG_AVOID"
            recommendation["reasoning"].append("Sehr niedriger Score, hohes Risiko")
        
        # Füge ML-Score Details hinzu
        recommendation["ml_details"] = asdict(ml_score)
        
        return recommendation
