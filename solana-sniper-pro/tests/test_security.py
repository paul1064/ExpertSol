"""
Unit-Tests für Security-Module

Testet:
- Wallet Manager
- Rug-Pull Checker
- Token Analyzer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import base58


class TestSecureKeyManager:
    """Tests für SecureKeyManager."""
    
    def test_validate_private_key_format_valid(self):
        """Testet Validierung eines gültigen Private Keys."""
        from security.wallet_manager import SecureKeyManager
        
        manager = SecureKeyManager()
        
        # Gültiger Base58 Key (64 Bytes decoded)
        valid_key = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
        
        result = manager._validate_private_key_format(valid_key)
        assert result == True
    
    def test_validate_private_key_format_invalid_length(self):
        """Testet Validierung bei ungültiger Länge."""
        from security.wallet_manager import SecureKeyManager
        
        manager = SecureKeyManager()
        
        # Zu kurz
        invalid_key = "tooshort"
        result = manager._validate_private_key_format(invalid_key)
        assert result == False
        
        # Zu lang
        invalid_key_long = "a" * 150
        result = manager._validate_private_key_format(invalid_key_long)
        assert result == False
    
    def test_load_private_key_from_env_success(self, monkeypatch):
        """Testet erfolgreiches Laden aus Environment Variable."""
        from security.wallet_manager import SecureKeyManager
        
        manager = SecureKeyManager()
        
        # Mock environment variable
        valid_key = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
        monkeypatch.setenv("SOLANA_PRIVATE_KEY", valid_key)
        
        result = manager.load_private_key_from_env()
        assert result == valid_key
    
    def test_load_private_key_from_env_missing(self):
        """Testet fehlende Environment Variable."""
        from security.wallet_manager import SecureKeyManager
        
        manager = SecureKeyManager()
        
        result = manager.load_private_key_from_env("NONEXISTENT_VAR")
        assert result is None
    
    @patch('security.wallet_manager.Keypair')
    def test_verify_keypair_valid(self, mock_keypair_class):
        """Testet Verifikation eines gültigen Keypairs."""
        from security.wallet_manager import SecureKeyManager
        
        manager = SecureKeyManager()
        
        # Mock Keypair
        mock_keypair = Mock()
        mock_keypair.sign.return_value = b"fake_signature"
        mock_keypair.pubkey().verify.return_value = True
        
        result = manager.verify_keypair(mock_keypair)
        assert result == True
    
    @patch('security.wallet_manager.Keypair')
    def test_verify_keypair_invalid(self, mock_keypair_class):
        """Testet Verifikation eines ungültigen Keypairs."""
        from security.wallet_manager import SecureKeyManager
        
        manager = SecureKeyManager()
        
        # Mock Keypair mit fehlerhafter Signatur
        mock_keypair = Mock()
        mock_keypair.sign.side_effect = Exception("Signing failed")
        
        result = manager.verify_keypair(mock_keypair)
        assert result == False


class TestRugPullChecker:
    """Tests für RugPullChecker."""
    
    @pytest.fixture
    def mock_rpc_client(self):
        """Erstellt einen gemockten RPC Client."""
        return Mock()
    
    @pytest.fixture
    def rug_checker(self, mock_rpc_client):
        """Erstellt einen RugPullChecker mit gemocktem RPC."""
        from security.rug_pull_checker import RugPullChecker
        return RugPullChecker(mock_rpc_client)
    
    @pytest.mark.asyncio
    async def test_check_mint_authority_null(self, rug_checker, mock_rpc_client):
        """Testet Mint Authority Check wenn null."""
        # Mock Response mit null mintAuthority
        mock_response = Mock()
        mock_response.value = Mock(
            data=Mock(
                parsed={
                    "info": {
                        "mintAuthority": None
                    }
                }
            )
        )
        mock_rpc_client.get_account_info_json_parsed.return_value = mock_response
        
        result = await rug_checker.check_mint_authority("TOKEN_ADDRESS")
        
        assert result.passed == True
        assert result.severity == "critical"
        assert "deaktiviert" in result.message
    
    @pytest.mark.asyncio
    async def test_check_mint_authority_active(self, rug_checker, mock_rpc_client):
        """Testet Mint Authority Check wenn aktiv."""
        # Mock Response mit aktiver mintAuthority
        mock_response = Mock()
        mock_response.value = Mock(
            data=Mock(
                parsed={
                    "info": {
                        "mintAuthority": "SomeAddress123"
                    }
                }
            )
        )
        mock_rpc_client.get_account_info_json_parsed.return_value = mock_response
        
        result = await rug_checker.check_mint_authority("TOKEN_ADDRESS")
        
        assert result.passed == False
        assert result.severity == "critical"
        assert "Risiko" in result.message
    
    @pytest.mark.asyncio
    async def test_check_top_holders_safe(self, rug_checker, mock_rpc_client):
        """Testet Top Holder Check bei sicherer Verteilung."""
        # Mock größte Accounts (jeweils < 10%)
        mock_accounts = [
            Mock(amount=Mock(ui_amount=1000)) for _ in range(10)
        ]
        
        mock_supply = Mock()
        mock_supply.value = Mock(ui_amount=100000)
        
        mock_rpc_client.get_token_largest_accounts.return_value = Mock(value=mock_accounts)
        mock_rpc_client.get_token_supply.return_value = mock_supply
        
        result = await rug_checker.check_top_holders("TOKEN_ADDRESS")
        
        assert result.passed == True
        assert result.details["top_10_percentage"] == 10.0  # 10 * 1000 / 100000 * 100
    
    @pytest.mark.asyncio
    async def test_check_top_holders_dangerous(self, rug_checker, mock_rpc_client):
        """Testet Top Holder Check bei gefährlicher Konzentration."""
        # Mock größte Accounts (> 60%)
        mock_accounts = [
            Mock(amount=Mock(ui_amount=10000)) for _ in range(10)
        ]
        
        mock_supply = Mock()
        mock_supply.value = Mock(ui_amount=100000)
        
        mock_rpc_client.get_token_largest_accounts.return_value = Mock(value=mock_accounts)
        mock_rpc_client.get_token_supply.return_value = mock_supply
        
        result = await rug_checker.check_top_holders("TOKEN_ADDRESS")
        
        assert result.passed == False
        assert result.severity == "critical"
        assert result.details["top_10_percentage"] == 100.0
    
    @pytest.mark.asyncio
    async def test_perform_all_checks_safe(self, rug_checker, mock_rpc_client):
        """Testet alle Sicherheitschecks für sicheres Token."""
        # Mock alle Checks als bestanden
        mock_response = Mock()
        mock_response.value = Mock(
            data=Mock(
                parsed={"info": {"mintAuthority": None}}
            )
        )
        mock_rpc_client.get_account_info_json_parsed.return_value = mock_response
        
        mock_rpc_client.get_account_info.return_value = Mock(value=Mock())
        
        mock_accounts = [Mock(amount=Mock(ui_amount=1000)) for _ in range(5)]
        mock_supply = Mock()
        mock_supply.value = Mock(ui_amount=100000)
        mock_rpc_client.get_token_largest_accounts.return_value = Mock(value=mock_accounts)
        mock_rpc_client.get_token_supply.return_value = mock_supply
        
        result = await rug_checker.perform_all_checks("TOKEN_ADDRESS")
        
        assert result["overall_status"] == "safe"
        assert result["recommendation"] == "allow"
    
    @pytest.mark.asyncio
    async def test_perform_all_checks_dangerous(self, rug_checker, mock_rpc_client):
        """Testet alle Sicherheitschecks für gefährliches Token."""
        # Mock Mint Authority als aktiv (kritisch!)
        mock_response = Mock()
        mock_response.value = Mock(
            data=Mock(
                parsed={"info": {"mintAuthority": "DevWallet"}}
            )
        )
        mock_rpc_client.get_account_info_json_parsed.return_value = mock_response
        
        result = await rug_checker.perform_all_checks("TOKEN_ADDRESS")
        
        assert result["overall_status"] == "dangerous"
        assert result["recommendation"] == "block"


class TestTradingStrategy:
    """Tests für Trading-Strategien."""
    
    def test_strategy_creation(self):
        """Testet Erstellung einer Strategie."""
        from config.strategies import TradingStrategy
        
        strategy = TradingStrategy(
            name="test",
            gewinnziel=100,
            stop_loss=30,
            trailing_stop=35,
            erstsicherung_ab=40,
            erstsicherung_prozent=50,
            frueh_stop=12,
            frueh_stop_zeitfenster=10,
            tagesverlustgrenze=25,
            runner_modus=False,
            nachkauf_ab=60,
            nachkauf_groesse=35,
            max_positionen=6,
            einsatz_pro_trade=0.1
        )
        
        assert strategy.name == "test"
        assert strategy.gewinnziel == 100
        assert strategy.max_positionen == 6
    
    def test_strategy_to_dict(self):
        """Testet Konvertierung zu Dictionary."""
        from config.strategies import TradingStrategy
        
        strategy = TradingStrategy(
            name="test",
            gewinnziel=100,
            stop_loss=30,
            trailing_stop=35,
            erstsicherung_ab=40,
            erstsicherung_prozent=50,
            frueh_stop=12,
            frueh_stop_zeitfenster=10,
            tagesverlustgrenze=25,
            runner_modus=False,
            nachkauf_ab=60,
            nachkauf_groesse=35,
            max_positionen=6,
            einsatz_pro_trade=0.1
        )
        
        dict_repr = strategy.to_dict()
        
        assert isinstance(dict_repr, dict)
        assert dict_repr["name"] == "test"
        assert dict_repr["gewinnziel"] == 100


class TestStrategyManager:
    """Tests für StrategyManager."""
    
    def test_get_strategy_existing(self):
        """Testet Abrufen einer existierenden Strategie."""
        from config.strategies import StrategyManager
        
        manager = StrategyManager()
        strategy = manager.get_strategy("konservativ")
        
        assert strategy is not None
        assert strategy.name == "konservativ"
        assert strategy.gewinnziel == 100
    
    def test_get_strategy_nonexistent(self):
        """Testet Abrufen einer nicht-existierenden Strategie."""
        from config.strategies import StrategyManager
        
        manager = StrategyManager()
        
        with pytest.raises(ValueError):
            manager.get_strategy("nonexistent")
    
    def test_set_active_strategy(self):
        """Testet Setzen der aktiven Strategie."""
        from config.strategies import StrategyManager
        
        manager = StrategyManager()
        manager.set_active_strategy("aggressiv")
        
        assert manager.active_strategy.name == "aggressiv"
        assert manager.active_strategy.gewinnziel == 250
    
    def test_validate_strategy_params_valid(self):
        """Testet Validierung gültiger Parameter."""
        from config.strategies import StrategyManager
        
        manager = StrategyManager()
        
        params = {
            "gewinnziel": 100,
            "stop_loss": 30,
            "einsatz_pro_trade": 0.1,
            "max_positionen": 5
        }
        
        result = manager.validate_strategy_params(params)
        assert result == True
    
    def test_validate_strategy_params_invalid(self):
        """Testet Validierung ungültiger Parameter."""
        from config.strategies import StrategyManager
        
        manager = StrategyManager()
        
        # Ungültig: Stop-Loss größer als Gewinnziel
        params = {
            "gewinnziel": 50,
            "stop_loss": 100,  # Invalid!
            "einsatz_pro_trade": 0.1,
            "max_positionen": 5
        }
        
        result = manager.validate_strategy_params(params)
        assert result == False


# Run tests with: pytest tests/test_security.py -v
