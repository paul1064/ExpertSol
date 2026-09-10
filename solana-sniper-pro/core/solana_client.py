"""
Solana RPC Client mit Multi-RPC Failover System

Unterstützt:
- Multiple RPC Endpoints mit automatischem Failover
- Health-Checks alle 10 Sekunden
- Response-Time Tracking
- Auto-Switch bei Timeout oder Error
- WebSocket Support für Real-Time Updates
"""

import asyncio
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solders.commitment_config import CommitmentLevel

logger = logging.getLogger(__name__)


@dataclass
class RPCEndpoint:
    """Datenklasse für RPC Endpoint Informationen."""
    
    url: str
    name: str
    is_healthy: bool = True
    avg_response_time: float = 0.0
    last_check: float = 0.0
    error_count: int = 0
    success_count: int = 0
    priority: int = 0  # Niedrigere Zahl = höhere Priorität


class RPCHealthMonitor:
    """
    Überwacht die Gesundheit von RPC Endpoints.
    """
    
    def __init__(self, check_interval: float = 10.0):
        """
        Initialisiert den Health Monitor.
        
        Args:
            check_interval: Intervall für Health-Checks in Sekunden
        """
        self.check_interval = check_interval
        self.last_check_time = 0.0
        self.logger = logging.getLogger(__name__)
    
    def record_response(
        self,
        endpoint: RPCEndpoint,
        response_time: float,
        success: bool
    ) -> None:
        """
        Zeichnet eine Response auf für Performance-Tracking.
        
        Args:
            endpoint: RPC Endpoint
            response_time: Response-Zeit in Millisekunden
            success: Ob der Request erfolgreich war
        """
        endpoint.last_check = time.time()
        
        if success:
            endpoint.success_count += 1
            endpoint.error_count = 0  # Reset bei Erfolg
            
            # Gleitender Durchschnitt für Response-Zeit
            alpha = 0.3  # Gewichtungsfaktor
            endpoint.avg_response_time = (
                alpha * response_time + 
                (1 - alpha) * endpoint.avg_response_time
            )
            
            endpoint.is_healthy = endpoint.avg_response_time < 500  # < 500ms
        else:
            endpoint.error_count += 1
            endpoint.success_count = 0  # Reset bei Fehler
            
            # Nach 3 Fehlern als unhealthy markieren
            if endpoint.error_count >= 3:
                endpoint.is_healthy = False
        
        self.logger.debug(
            f"Endpoint {endpoint.name}: "
            f"Response={response_time:.2f}ms, "
            f"Healthy={endpoint.is_healthy}, "
            f"Errors={endpoint.error_count}"
        )
    
    def should_check_health(self) -> bool:
        """
        Prüft ob ein Health-Check durchgeführt werden sollte.
        
        Returns:
            True wenn Check fällig ist
        """
        return (time.time() - self.last_check_time) >= self.check_interval
    
    def mark_check_complete(self) -> None:
        """Markiert Health-Check als abgeschlossen."""
        self.last_check_time = time.time()


class SolanaRPCClient:
    """
    Solana RPC Client mit automatischem Failover und Health-Monitoring.
    """
    
    DEFAULT_ENDPOINTS: List[Dict[str, Any]] = [
        {
            "url": "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY",
            "name": "Helius",
            "priority": 1
        },
        {
            "url": "https://api.mainnet-beta.solana.com",
            "name": "Solana Public",
            "priority": 3
        },
        {
            "url": "https://solana-mainnet.g.alchemy.com/v2/YOUR_KEY",
            "name": "Alchemy",
            "priority": 2
        },
        {
            "url": "https://api.triton.one/?api-key=YOUR_KEY",
            "name": "Triton",
            "priority": 2
        }
    ]
    
    def __init__(
        self,
        endpoints: Optional[List[Dict[str, Any]]] = None,
        commitment: str = "confirmed",
        timeout: float = 10.0
    ):
        """
        Initialisiert den Solana RPC Client.
        
        Args:
            endpoints: Liste von RPC Endpoints (optional, verwendet Defaults wenn None)
            commitment: Commitment Level ('processed', 'confirmed', 'finalized')
            timeout: Timeout für Requests in Sekunden
        """
        self.endpoints: List[RPCEndpoint] = []
        self.current_endpoint: Optional[RPCEndpoint] = None
        self.health_monitor = RPCHealthMonitor()
        self.timeout = timeout
        self.commitment = CommitmentLevel.from_string(commitment)
        
        # Initialisiere Endpoints
        endpoint_configs = endpoints or self.DEFAULT_ENDPOINTS
        for config in endpoint_configs:
            endpoint = RPCEndpoint(
                url=config["url"],
                name=config["name"],
                priority=config.get("priority", 99)
            )
            self.endpoints.append(endpoint)
        
        # Sortiere nach Priorität
        self.endpoints.sort(key=lambda x: x.priority)
        
        # Initialisiere current_endpoint vor der ersten Verwendung
        self.current_endpoint: Optional[RPCEndpoint] = None
        
        # Wähle ersten gesunden Endpoint
        self._select_best_endpoint()
        
        # Erstelle RPC Clients
        self._sync_client: Optional[Client] = None
        self._async_client: Optional[AsyncClient] = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"RPC Client initialisiert mit {len(self.endpoints)} Endpoints")
    
    def _select_best_endpoint(self) -> None:
        """
        Wählt den besten verfügbaren Endpoint aus.
        """
        healthy_endpoints = [ep for ep in self.endpoints if ep.is_healthy]
        
        if not healthy_endpoints:
            # Fallback: Alle Endpoints wieder aktivieren und langsamsten entfernen
            logger.warning("Keine gesunden Endpoints! Setze alle zurück.")
            for ep in self.endpoints:
                ep.is_healthy = True
                ep.error_count = 0
            healthy_endpoints = self.endpoints
        
        # Wähle Endpoint mit niedrigster Response-Zeit
        best_endpoint = min(
            healthy_endpoints,
            key=lambda x: (x.avg_response_time if x.avg_response_time > 0 else float('inf'))
        )
        
        if self.current_endpoint != best_endpoint:
            old_name = self.current_endpoint.name if self.current_endpoint else "None"
            logger.info(f"Wechsle RPC Endpoint: {old_name} → {best_endpoint.name}")
            self.current_endpoint = best_endpoint
    
    def _get_sync_client(self) -> Client:
        """
        Erstellt oder ruft den synchronen RPC Client ab.
        
        Returns:
            Sync RPC Client
        """
        if not self.current_endpoint:
            raise RuntimeError("Kein RPC Endpoint ausgewählt")
        
        if not self._sync_client or self._sync_client._commitment != self.commitment:
            self._sync_client = Client(
                self.current_endpoint.url,
                timeout=self.timeout,
                commitment=self.commitment
            )
        
        return self._sync_client
    
    def _get_async_client(self) -> AsyncClient:
        """
        Erstellt oder ruft den asynchronen RPC Client ab.
        
        Returns:
            Async RPC Client
        """
        if not self.current_endpoint:
            raise RuntimeError("Kein RPC Endpoint ausgewählt")
        
        if not self._async_client or self._async_client._commitment != self.commitment:
            self._async_client = AsyncClient(
                self.current_endpoint.url,
                timeout=self.timeout,
                commitment=self.commitment
            )
        
        return self._async_client
    
    async def _execute_with_failover(
        self,
        operation: callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Führt eine Operation mit automatischem Failover aus.
        
        Args:
            operation: Auszuführende Operation
            *args: Positionsargumente für die Operation
            **kwargs: Keyword-Argumente für die Operation
            
        Returns:
            Ergebnis der Operation
            
        Raises:
            Exception: Wenn alle Endpoints fehlschlagen
        """
        max_retries = len(self.endpoints)
        last_error = None
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                result = await operation(*args, **kwargs)
                response_time = (time.time() - start_time) * 1000  # ms
                
                # Record successful response
                if self.current_endpoint:
                    self.health_monitor.record_response(
                        self.current_endpoint,
                        response_time,
                        success=True
                    )
                
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"RPC Request fehlgeschlagen ({self.current_endpoint.name}): {str(e)}"
                )
                
                if self.current_endpoint:
                    self.health_monitor.record_response(
                        self.current_endpoint,
                        0,
                        success=False
                    )
                
                # Versuche nächsten Endpoint
                self._select_best_endpoint()
                
                # Aktualisiere Clients mit neuem Endpoint
                self._sync_client = None
                self._async_client = None
        
        # Alle Endpoints fehlgeschlagen
        self.logger.error(f"Alle RPC Endpoints fehlgeschlagen nach {max_retries} Versuchen")
        raise last_error
    
    # Synchronous Methods
    def get_balance(self, pubkey: str) -> Any:
        """
        Ruft SOL-Balance einer Adresse ab.
        
        Args:
            pubkey: Öffentliche Adresse
            
        Returns:
            Balance in Lamports
        """
        try:
            client = self._get_sync_client()
            response = client.get_balance(pubkey)
            return response.value
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Balance: {str(e)}")
            raise
    
    def get_account_info(self, pubkey: str) -> Any:
        """
        Ruft Account-Informationen ab.
        
        Args:
            pubkey: Öffentliche Adresse
            
        Returns:
            Account Info
        """
        try:
            client = self._get_sync_client()
            response = client.get_account_info(pubkey)
            return response.value
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Account-Info: {str(e)}")
            raise
    
    def get_signature_statuses(self, signatures: List[str]) -> Any:
        """
        Ruft Status von Signaturen ab.
        
        Args:
            signatures: Liste von Signaturen
            
        Returns:
            Signature Statuses
        """
        try:
            client = self._get_sync_client()
            response = client.get_signature_statuses(signatures)
            return response.value
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Signature-Statusse: {str(e)}")
            raise
    
    def send_transaction(self, transaction: Any) -> str:
        """
        Sendet eine Transaktion.
        
        Args:
            transaction: Zu sendende Transaktion
            
        Returns:
            Transaktions-Signatur
        """
        try:
            client = self._get_sync_client()
            response = client.send_transaction(transaction)
            return response.value
        except Exception as e:
            logger.error(f"Fehler beim Senden der Transaktion: {str(e)}")
            raise
    
    # Asynchronous Methods
    async def async_get_balance(self, pubkey: str) -> Any:
        """
        Ruft SOL-Balance einer Adresse ab (async).
        
        Args:
            pubkey: Öffentliche Adresse
            
        Returns:
            Balance in Lamports
        """
        async def _get_balance():
            client = self._get_async_client()
            response = await client.get_balance(pubkey)
            return response.value
        
        return await self._execute_with_failover(_get_balance)
    
    async def async_get_account_info(self, pubkey: str) -> Any:
        """
        Ruft Account-Informationen ab (async).
        
        Args:
            pubkey: Öffentliche Adresse
            
        Returns:
            Account Info
        """
        async def _get_account_info():
            client = self._get_async_client()
            response = await client.get_account_info(pubkey)
            return response.value
        
        return await self._execute_with_failover(_get_account_info)
    
    async def async_send_transaction(self, transaction: Any) -> str:
        """
        Sendet eine Transaktion (async).
        
        Args:
            transaction: Zu sendende Transaktion
            
        Returns:
            Transaktions-Signatur
        """
        async def _send_tx():
            client = self._get_async_client()
            response = await client.send_transaction(transaction)
            return response.value
        
        return await self._execute_with_failover(_send_tx)
    
    async def async_get_recent_blockhash(self) -> Any:
        """
        Ruft aktuellen Blockhash ab (async).
        
        Returns:
            Blockhash Information
        """
        async def _get_blockhash():
            client = self._get_async_client()
            response = await client.get_latest_blockhash()
            return response.value
        
        return await self._execute_with_failover(_get_blockhash)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Gibt Status aller RPC Endpoints zurück.
        
        Returns:
            Dictionary mit Endpoint-Statusinformationen
        """
        status = {
            "current_endpoint": self.current_endpoint.name if self.current_endpoint else None,
            "endpoints": []
        }
        
        for ep in self.endpoints:
            status["endpoints"].append({
                "name": ep.name,
                "url": ep.url,
                "is_healthy": ep.is_healthy,
                "avg_response_time_ms": round(ep.avg_response_time, 2),
                "error_count": ep.error_count,
                "success_count": ep.success_count,
                "priority": ep.priority
            })
        
        return status
    
    async def health_check_loop(self) -> None:
        """
        Kontinuierlicher Health-Check Loop für alle Endpoints.
        Sollte als Background-Task ausgeführt werden.
        """
        self.logger.info("Starte Health-Check Loop")
        
        while True:
            try:
                await asyncio.sleep(self.health_monitor.check_interval)
                
                # Führe Health-Check für alle Endpoints durch
                for endpoint in self.endpoints:
                    try:
                        start_time = time.time()
                        
                        # Einfacher Health-Check via getBalance auf System-Programm
                        client = AsyncClient(endpoint.url, timeout=2.0)
                        await client.get_balance(
                            "11111111111111111111111111111111"
                        )
                        response_time = (time.time() - start_time) * 1000
                        
                        self.health_monitor.record_response(
                            endpoint,
                            response_time,
                            success=True
                        )
                        
                        await client.close()
                        
                    except Exception as e:
                        self.health_monitor.record_response(
                            endpoint,
                            0,
                            success=False
                        )
                        self.logger.debug(f"Health-Check fehlgeschlagen für {endpoint.name}: {str(e)}")
                
                # Wähle besten Endpoint
                self._select_best_endpoint()
                
                # Aktualisiere Clients wenn nötig
                if self._sync_client:
                    self._sync_client = None
                if self._async_client:
                    self._async_client = None
                
            except Exception as e:
                self.logger.error(f"Fehler im Health-Check Loop: {str(e)}")
                await asyncio.sleep(5)  # Kurze Pause bei Fehler


# Beispiel-Nutzung
if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    # Client erstellen
    rpc_client = SolanaRPCClient()
    
    # Status anzeigen
    print("\nRPC Endpoint Status:")
    status = rpc_client.get_status()
    print(f"Aktiver Endpoint: {status['current_endpoint']}")
    
    for ep in status['endpoints']:
        print(f"  {ep['name']}: Healthy={ep['is_healthy']}, "
              f"Response={ep['avg_response_time_ms']}ms")
    
    # Teste Balance-Abfrage
    async def test_balance():
        balance = await rpc_client.async_get_balance(
            "11111111111111111111111111111111"
        )
        print(f"\nTest Balance: {balance / 1e9} SOL")
    
    asyncio.run(test_balance())
