"""
Dynamic Priority Fee Calculator für Solana Sniper Pro.

Berechnet optimale Priority Fees basierend auf Netzwerk-Kongestion.
"""

from typing import Dict, Any, Optional
import time
import aiohttp
import asyncio


class PriorityFeeCalculator:
    """Berechnet dynamische Priority Fees für Solana-Transaktionen."""
    
    # API-Endpoints
    PRIORITY_FEE_API = "https://solana.priorityfee.dev/api/v1/priority-fee"
    
    def __init__(self, rpc_endpoint: str = None):
        """
        Initialisiert den PriorityFeeCalculator.
        
        Args:
            rpc_endpoint: Solana RPC-Endpoint (optional)
        """
        self.rpc_endpoint = rpc_endpoint
        self._fee_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 30  # Sekunden
    
    async def get_recommended_fee(self, priority: str = "medium") -> float:
        """
        Berechnet empfohlene Priority Fee.
        
        Args:
            priority: Fee-Level (low, medium, high, ultra)
            
        Returns:
            Empfohlene Fee in Lamports per Compute Unit
        """
        multipliers = {
            "low": 1.0,
            "medium": 1.5,
            "high": 2.0,
            "ultra": 3.0
        }
        
        # Hole Basis-Fee
        base_fee = await self._get_base_fee()
        
        if base_fee is None:
            # Fallback-Werte bei API-Fehler
            fallback_fees = {
                "low": 1000,
                "medium": 5000,
                "high": 10000,
                "ultra": 25000
            }
            return fallback_fees.get(priority, 5000)
        
        multiplier = multipliers.get(priority, 1.5)
        recommended_fee = base_fee * multiplier
        
        return round(recommended_fee, 0)
    
    async def _get_base_fee(self) -> Optional[float]:
        """
        Holt aktuelle Basis-Priority-Fee von der API.
        
        Returns:
            Basis-Fee in Lamports per Compute Unit oder None
        """
        # Prüfe Cache
        now = time.time()
        if now - self._cache_timestamp < self._cache_ttl:
            return self._fee_cache.get('base')
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.PRIORITY_FEE_API, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extrahiere median fee
                        if 'median' in data:
                            base_fee = float(data['median'])
                            self._fee_cache['base'] = base_fee
                            self._cache_timestamp = now
                            return base_fee
                        
                        # Alternative Response-Struktur
                        if 'priorityFee' in data:
                            base_fee = float(data['priorityFee'])
                            self._fee_cache['base'] = base_fee
                            self._cache_timestamp = now
                            return base_fee
        except Exception as e:
            print(f"Fehler beim Abrufen der Priority Fee: {e}")
        
        # Fallback: Berechne aus RPC
        return await self._calculate_from_rpc()
    
    async def _calculate_from_rpc(self) -> Optional[float]:
        """
        Berechnet Priority Fee aus RPC-Block-Daten.
        
        Returns:
            Durchschnittliche Fee oder None
        """
        if not self.rpc_endpoint:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                # Hole letzte 20 Blöcke
                blocks = await self._get_recent_blocks(session, count=20)
                
                if not blocks:
                    return None
                
                # Berechne durchschnittliche Fee
                fees = []
                for block in blocks:
                    if 'rewards' in block:
                        for reward in block['rewards']:
                            if 'priorityFee' in reward:
                                fees.append(float(reward['priorityFee']))
                
                if not fees:
                    return None
                
                avg_fee = sum(fees) / len(fees)
                
                # Cache aktualisieren
                self._fee_cache['base'] = avg_fee
                self._cache_timestamp = time.time()
                
                return avg_fee
                
        except Exception as e:
            print(f"Fehler bei RPC-Berechnung: {e}")
            return None
    
    async def _get_recent_blocks(self, session: aiohttp.ClientSession, 
                                  count: int = 20) -> list:
        """
        Holt recente Blöcke vom RPC.
        
        Args:
            session: aiohttp Session
            count: Anzahl Blöcke
            
        Returns:
            Liste von Block-Daten
        """
        if not self.rpc_endpoint:
            return []
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getRecentPerformanceSamples",
            "params": [count]
        }
        
        try:
            async with session.post(
                self.rpc_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result', [])
        except Exception as e:
            print(f"Fehler beim Abrufen der Blöcke: {e}")
        
        return []
    
    def get_fee_for_transaction_type(self, tx_type: str) -> float:
        """
        Gibt empfohlene Fee für Transaktionstyp zurück.
        
        Args:
            tx_type: Typ der Transaktion (swap, transfer, nft_purchase, etc.)
            
        Returns:
            Empfohlene Fee in Lamports per Compute Unit
        """
        # Base-Fees für verschiedene Transaktionstypen
        type_multipliers = {
            "transfer": 1.0,      # Einfacher Transfer
            "swap": 1.5,          # DEX Swap
            "nft_purchase": 2.0,   # NFT Kauf
            "token_launch": 3.0,   # Token Launch (Sniping)
            "complex": 2.5         # Komplexe Transaktionen
        }
        
        base_fee = self._fee_cache.get('base', 5000)
        multiplier = type_multipliers.get(tx_type, 1.5)
        
        return round(base_fee * multiplier, 0)
    
    async def get_fee_tiers(self) -> Dict[str, float]:
        """
        Gibt alle Fee-Tiers zurück.
        
        Returns:
            Dictionary mit allen Fee-Levels
        """
        base_fee = await self._get_base_fee()
        
        if base_fee is None:
            base_fee = 5000  # Fallback
        
        return {
            "low": round(base_fee * 1.0, 0),
            "medium": round(base_fee * 1.5, 0),
            "high": round(base_fee * 2.0, 0),
            "ultra": round(base_fee * 3.0, 0)
        }
    
    def estimate_confirmation_time(self, fee: float) -> str:
        """
        Schätzt Bestätigungszeit basierend auf Fee.
        
        Args:
            fee: Priority Fee in Lamports per Compute Unit
            
        Returns:
            Geschätzte Zeit ("immediate", "< 5s", "< 30s", "> 30s")
        """
        base_fee = self._fee_cache.get('base', 5000)
        
        if fee >= base_fee * 3:
            return "immediate"
        elif fee >= base_fee * 2:
            return "< 5s"
        elif fee >= base_fee * 1.5:
            return "< 30s"
        else:
            return "> 30s"
    
    async def get_network_congestion_level(self) -> Dict[str, Any]:
        """
        Analysiert Netzwerk-Kongestion.
        
        Returns:
            Dictionary mit Kongestions-Level und Empfehlungen
        """
        base_fee = await self._get_base_fee()
        
        if base_fee is None:
            base_fee = 5000
        
        # Bestimme Kongestions-Level
        if base_fee < 1000:
            level = "low"
            recommendation = "Normale Fees ausreichend"
        elif base_fee < 5000:
            level = "medium"
            recommendation = "Erhöhe Fees für schnellere Bestätigung"
        elif base_fee < 15000:
            level = "high"
            recommendation = "Hohe Fees empfohlen"
        else:
            level = "extreme"
            recommendation = "Sehr hohe Fees nötig oder warten"
        
        return {
            "level": level,
            "base_fee": base_fee,
            "recommendation": recommendation,
            "timestamp": time.time()
        }
    
    def calculate_total_fee(self, priority_fee: float, compute_units: int = 200000) -> float:
        """
        Berechnet Gesamtgebühr für Transaktion.
        
        Args:
            priority_fee: Fee pro Compute Unit
            compute_units: Anzahl Compute Units (default 200k)
            
        Returns:
            Gesamtgebühr in Lamports
        """
        # Basis-Transaktionsgebühr: 5000 Lamports
        base_fee = 5000
        
        # Priority Fee: priority_fee * compute_units
        total_priority = priority_fee * compute_units
        
        return base_fee + total_priority
    
    def lamports_to_sol(self, lamports: float) -> float:
        """Konvertiert Lamports zu SOL."""
        return lamports / 1_000_000_000
    
    def sol_to_lamports(self, sol: float) -> float:
        """Konvertiert SOL zu Lamports."""
        return sol * 1_000_000_000


# Beispiel-Nutzung
async def main():
    calculator = PriorityFeeCalculator()
    
    # Empfohlene Fees
    print("Priority Fee Empfehlungen:")
    tiers = await calculator.get_fee_tiers()
    for tier, fee in tiers.items():
        print(f"  {tier}: {fee} Lamports/CU")
    
    # Netzwerk-Kongestion
    congestion = await calculator.get_network_congestion_level()
    print(f"\nNetzwerk-Kongestion: {congestion['level']}")
    print(f"Empfehlung: {congestion['recommendation']}")
    
    # Fee für spezifischen Transaktionstyp
    swap_fee = calculator.get_fee_for_transaction_type("swap")
    print(f"\nSwap-Transaktion Fee: {swap_fee} Lamports/CU")
    
    # Gesamtgebühr berechnen
    total_lamports = calculator.calculate_total_fee(swap_fee, 200000)
    total_sol = calculator.lamports_to_sol(total_lamports)
    print(f"Gesamtgebühr: {total_lamports:.0f} Lamports ({total_sol:.6f} SOL)")


if __name__ == '__main__':
    asyncio.run(main())
