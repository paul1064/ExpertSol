"""
Trading-Strategien für Solana Sniper Pro

Enthält drei vordefinierte Strategien: Konservativ, Aggressiv, Jackpot
"""

from typing import Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class TradingStrategy:
    """Datenklasse für Trading-Strategie-Konfiguration."""
    
    name: str
    gewinnziel: float  # Prozent
    stop_loss: float  # Prozent
    trailing_stop: float  # Prozent
    erstsicherung_ab: float  # Prozent
    erstsicherung_prozent: float  # Prozent der Position
    frueh_stop: float  # Prozent
    frueh_stop_zeitfenster: int  # Minuten
    tagesverlustgrenze: float  # USD
    runner_modus: bool
    nachkauf_ab: float  # Prozent
    nachkauf_groesse: float  # Prozent
    max_positionen: int
    einsatz_pro_trade: float  # SOL/USD
    
    # Zusätzliche Felder für Runner-Modus
    runner_verkauf_ab: float = 0.0
    runner_verkauf_prozent: float = 0.0
    runner_trailing: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Strategie in ein Dictionary."""
        return asdict(self)


# Vordefinierte Strategien gemäß Spezifikation
STRATEGIES: Dict[str, TradingStrategy] = {
    "konservativ": TradingStrategy(
        name="konservativ",
        gewinnziel=100,  # 100% Gewinnziel
        stop_loss=30,  # 30% Stop Loss
        trailing_stop=35,  # 35% Trailing Stop
        erstsicherung_ab=40,  # Ab 40% Profit
        erstsicherung_prozent=50,  # 50% der Position verkaufen
        frueh_stop=12,  # 12% Early Stop
        frueh_stop_zeitfenster=10,  # Innerhalb 10 Minuten
        tagesverlustgrenze=25,  # $25 maximaler Tagesverlust
        runner_modus=False,  # Kein Runner Modus
        nachkauf_ab=60,  # Nachkauf ab 60% Profit
        nachkauf_groesse=35,  # 35% der ursprünglichen Position
        max_positionen=6,  # Maximal 6 gleichzeitige Positionen
        einsatz_pro_trade=0.1  # 0.1 SOL pro Trade
    ),
    
    "aggressiv": TradingStrategy(
        name="aggressiv",
        gewinnziel=250,  # 250% Gewinnziel
        stop_loss=40,  # 40% Stop Loss
        trailing_stop=25,  # 25% Trailing Stop
        erstsicherung_ab=50,  # Ab 50% Profit
        erstsicherung_prozent=40,  # 40% der Position verkaufen
        frueh_stop=15,  # 15% Early Stop
        frueh_stop_zeitfenster=15,  # Innerhalb 15 Minuten
        tagesverlustgrenze=40,  # $40 maximaler Tagesverlust
        runner_modus=True,  # Runner Modus aktiv
        runner_verkauf_ab=100,  # Ab 100% Profit
        runner_verkauf_prozent=30,  # 30% verkaufen
        runner_trailing=30,  # 30% Trailing für Runner
        nachkauf_ab=80,  # Nachkauf ab 80% Profit
        nachkauf_groesse=50,  # 50% der ursprünglichen Position
        max_positionen=4,  # Maximal 4 gleichzeitige Positionen
        einsatz_pro_trade=0.2  # 0.2 SOL pro Trade
    ),
    
    "jackpot": TradingStrategy(
        name="jackpot",
        gewinnziel=500,  # 500% Gewinnziel
        stop_loss=35,  # 35% Stop Loss
        trailing_stop=40,  # 40% Trailing Stop
        erstsicherung_ab=30,  # Ab 30% Profit
        erstsicherung_prozent=50,  # 50% der Position verkaufen
        frueh_stop=10,  # 10% Early Stop
        frueh_stop_zeitfenster=8,  # Innerhalb 8 Minuten
        tagesverlustgrenze=30,  # $30 maximaler Tagesverlust
        runner_modus=True,  # Runner Modus aktiv
        runner_verkauf_ab=500,  # Ab 500% Profit
        runner_verkauf_prozent=25,  # 25% verkaufen
        runner_trailing=50,  # 50% Trailing für Runner
        nachkauf_ab=100,  # Nachkauf ab 100% Profit
        nachkauf_groesse=50,  # 50% der ursprünglichen Position
        max_positionen=3,  # Maximal 3 gleichzeitige Positionen
        einsatz_pro_trade=0.15  # 0.15 SOL pro Trade
    )
}


class StrategyManager:
    """
    Verwaltet Trading-Strategien und stellt Methoden zur Verfügung.
    """
    
    def __init__(self):
        """Initialisiert den Strategy Manager."""
        self.strategies = STRATEGIES
        self.active_strategy: TradingStrategy = self.strategies["konservativ"]
    
    def get_strategy(self, name: str) -> TradingStrategy:
        """
        Ruft eine Strategie nach Namen ab.
        
        Args:
            name: Name der Strategie ('konservativ', 'aggressiv', 'jackpot')
            
        Returns:
            TradingStrategy Objekt
            
        Raises:
            ValueError: Wenn Strategie nicht existiert
        """
        if name not in self.strategies:
            raise ValueError(f"Unbekannte Strategie: {name}")
        
        return self.strategies[name]
    
    def set_active_strategy(self, name: str) -> None:
        """
        Setzt die aktive Strategie.
        
        Args:
            name: Name der Strategie
        """
        self.active_strategy = self.get_strategy(name)
    
    def get_all_strategies(self) -> Dict[str, TradingStrategy]:
        """
        Gibt alle verfügbaren Strategien zurück.
        
        Returns:
            Dictionary aller Strategien
        """
        return self.strategies
    
    def compare_strategies(self) -> Dict[str, Any]:
        """
        Vergleicht alle Strategien nebeneinander.
        
        Returns:
            Vergleichsdaten als Dictionary
        """
        comparison = {}
        
        for name, strategy in self.strategies.items():
            comparison[name] = {
                "gewinnziel": strategy.gewinnziel,
                "stop_loss": strategy.stop_loss,
                "trailing_stop": strategy.trailing_stop,
                "max_positionen": strategy.max_positionen,
                "einsatz_pro_trade": strategy.einsatz_pro_trade,
                "runner_modus": strategy.runner_modus
            }
        
        return comparison
    
    def validate_strategy_params(self, params: Dict[str, Any]) -> bool:
        """
        Validiert Strategie-Parameter auf Plausibilität.
        
        Args:
            params: Parameter-Dictionary
            
        Returns:
            True wenn valide, False sonst
        """
        try:
            # Basis-Checks
            if params.get("gewinnziel", 0) <= 0:
                return False
            
            if params.get("stop_loss", 0) <= 0:
                return False
            
            if params.get("einsatz_pro_trade", 0) <= 0:
                return False
            
            if params.get("max_positionen", 0) <= 0:
                return False
            
            # Logik-Checks
            if params.get("erstsicherung_ab", 0) > params.get("gewinnziel", 0):
                return False
            
            if params.get("stop_loss", 0) > params.get("gewinnziel", 0):
                return False
            
            return True
            
        except Exception:
            return False
    
    def create_custom_strategy(
        self,
        name: str,
        **kwargs
    ) -> TradingStrategy:
        """
        Erstellt eine benutzerdefinierte Strategie.
        
        Args:
            name: Name der neuen Strategie
            **kwargs: Überschriebene Parameter
            
        Returns:
            Neue TradingStrategy Instanz
        """
        # Starte mit konservativer Basis
        base_strategy = self.strategies["konservativ"]
        base_dict = base_strategy.to_dict()
        
        # Überschreibe mit custom Werten
        base_dict.update(kwargs)
        base_dict["name"] = name
        
        # Validiere
        if not self.validate_strategy_params(base_dict):
            raise ValueError("Ungültige Strategie-Parameter")
        
        custom_strategy = TradingStrategy(**base_dict)
        
        # Füge zu Strategien hinzu
        self.strategies[name] = custom_strategy
        
        return custom_strategy


# Beispiel-Nutzung
if __name__ == "__main__":
    manager = StrategyManager()
    
    # Alle Strategien anzeigen
    print("Verfügbare Strategien:")
    for name in manager.strategies.keys():
        print(f"  - {name}")
    
    # Aktive Strategie setzen
    manager.set_active_strategy("aggressiv")
    print(f"\nAktive Strategie: {manager.active_strategy.name}")
    print(f"Gewinnziel: {manager.active_strategy.gewinnziel}%")
    print(f"Stop Loss: {manager.active_strategy.stop_loss}%")
    print(f"Max Positionen: {manager.active_strategy.max_positionen}")
    
    # Custom Strategie erstellen
    custom = manager.create_custom_strategy(
        "my_custom",
        gewinnziel=200,
        stop_loss=25,
        einsatz_pro_trade=0.3
    )
    print(f"\nCustom Strategie erstellt: {custom.name}")
