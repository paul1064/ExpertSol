# Solana Sniper Pro

**Professioneller automatischer Token-Sniper für Solana mit Fokus auf Sicherheit, Risikomanagement und Performance.**

## ⚠️ WICHTIGE WARNUNG

Dieser Bot handelt mit echtem Geld und birgt erhebliche Risiken:
- **Verlustrisiko:** Du kannst dein gesamtes eingesetztes Kapital verlieren
- **Technische Risiken:** Bugs, Netzwerkprobleme, RPC-Ausfälle
- **Marktrisiken:** Extreme Volatilität, Rug-Pulls, Honeypots
- **Sicherheit:** Private Keys müssen sicher verwahrt werden

**Nutze diesen Bot nur auf eigene Gefahr und nur mit Geld, dessen Verlust du verkraften kannst!**

---

## 📋 Inhaltsverzeichnis

- [Features](#-features)
- [Installation](#-installation)
- [Konfiguration](#-konfiguration)
- [Trading-Strategien](#-trading-strategien)
- [Sicherheit](#-sicherheit)
- [Verwendung](#-verwendung)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### Phase 1: Kritische Features ✅

- **Sichere Wallet-Verwaltung**
  - Private Keys aus Environment Variables
  - Support für JSON Keypair-Dateien und Base58-Strings
  - Multi-Wallet Support
  - Balance-Checks vor Trades

- **Multi-RPC Failover System**
  - Automatische Health-Checks alle 10 Sekunden
  - Response-Time Tracking
  - Auto-Switch bei Timeout oder Error
  - Support für Helius, Triton, Alchemy, Public RPC

- **Rug-Pull Schutz**
  - Mint Authority Check
  - Top Holder Konzentrations-Check (einstellbare Thresholds)
  - Honeypot-Erkennung
  - LP-Lock Verifizierung (in Entwicklung)

- **Trading-Strategien**
  - Konservativ: Geringes Risiko, stabile Gewinne
  - Aggressiv: Höheres Risiko, größere Gewinne
  - Jackpot: Maximales Risiko, Moonshot-Potential
  - Custom Strategien erstellbar

- **Emergency Kill Switch**
  - Sofortiges Schließen aller Positionen
  - Trading-Pause für 24h
  - Benachrichtigungen
  - Ausführliches Logging

### Phase 2: Wichtige Features 🚧

- Telegram Bot Integration
- Health Monitoring
- Erweiterte Token-Analyse
- Dynamic Priority Fee Calculator
- Logging & Debugging System

### Phase 3: Advanced Features 📅

- Jito Bundle Integration (MEV-Schutz)
- Machine Learning Token-Score
- Backtesting Tool
- Market Regime Detection

---

## 🚀 Installation

### Voraussetzungen

- Python 3.10 oder höher
- Git
- Solana Mainnet RPC Endpoint (empfohlen: Helius, Triton)
- Solana Wallet mit SOL

### Schritt-für-Schritt

```bash
# 1. Repository klonen
git clone https://github.com/yourusername/solana-sniper-pro.git
cd solana-sniper-pro

# 2. Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Environment konfigurieren
cp config/.env.example .env
# Bearbeite .env mit deinen Daten (siehe Konfiguration)

# 5. Bot testen
python core/bot.py
```

---

## ⚙️ Konfiguration

### Environment Variables (.env)

```env
# Solana
SOLANA_PRIVATE_KEY=dein_private_key_hier
SOLANA_RPC_ENDPOINT=https://mainnet.helius-rpc.com/?api-key=DEIN_KEY

# Trading
MIN_BALANCE=0.1
DEFAULT_STRATEGY=konservativ

# Security
BLOCK_TOP_HOLDER_PERCENT=60
WARN_TOP_HOLDER_PERCENT=40
MIN_LP_LOCK_DAYS=30

# Optional: Telegram (Phase 2)
TELEGRAM_API_ID=deine_api_id
TELEGRAM_API_HASH=dein_api_hash
TELEGRAM_BOT_TOKEN=dein_bot_token

# Optional: Monitoring
HEALTHCHECK_URL=https://hc-ping.com/dein-uuid
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### ⚠️ SICHERHEITSHINWEISE

1. **NIEMALS** Private Keys im Code hardcoden
2. **.env Datei niemals committen** (in .gitignore aufgenommen)
3. Private Keys verschlüsselt speichern für Production
4. Regelmäßig Keys rotieren

---

## 📊 Trading-Strategien

### Konservativ (Empfohlen für Einsteiger)

```python
{
    "gewinnziel": 100%,      # Take-Profit bei +100%
    "stop_loss": 30%,        # Stop-Loss bei -30%
    "trailing_stop": 35%,    # Trailing ab 35% Profit
    "max_positionen": 6,     # Max 6 gleichzeitige Trades
    "einsatz_pro_trade": 0.1 SOL
}
```

**Charakteristika:**
- ✅ Niedriges Risiko
- ✅ Häufige kleine Gewinne
- ✅ Enges Risikomanagement
- ❌ Begrenztes Upside-Potential

### Aggressiv

```python
{
    "gewinnziel": 250%,
    "stop_loss": 40%,
    "trailing_stop": 25%,
    "max_positionen": 4,
    "einsatz_pro_trade": 0.2 SOL,
    "runner_modus": True
}
```

**Charakteristika:**
- ⚠️ Mittleres bis hohes Risiko
- ✅ Größere Gewinnmöglichkeiten
- ✅ Runner-Modus für Moonshots
- ❌ Höhere Volatilität

### Jackpot

```python
{
    "gewinnziel": 500%,
    "stop_loss": 35%,
    "trailing_stop": 40%,
    "max_positionen": 3,
    "einsatz_pro_trade": 0.15 SOL,
    "runner_modus": True
}
```

**Charakteristika:**
- 🔴 Sehr hohes Risiko
- 🚀 Maximales Upside-Potential
- 🎯 Nur für erfahrene Trader
- ⚡ Kann schnell zu Totalverlust führen

---

## 🔒 Sicherheit

### Implementierte Sicherheitsmaßnahmen

1. **Private Key Protection**
   - Keys nur in Environment Variables
   - Keine Ausgabe in Logs
   - Validierung vor Nutzung

2. **Rug-Pull Prevention**
   - Automatische Token-Checks vor jedem Kauf
   - Blockierung unsicherer Tokens
   - Einstellbare Risk-Thresholds

3. **Rate Limiting**
   - Schutz vor API-Bans
   - Respektvolle RPC-Nutzung

4. **Error Handling**
   - Try-Except in allen kritischen Funktionen
   - Graceful Degradation
   - Ausführliches Logging

### Best Practices

- Starte mit kleinen Beträgen (< 0.1 SOL pro Trade)
- Teste zuerst auf Devnet
- Überwache den Bot regelmäßig
- Halte Software aktuell
- Backup deiner Wallet

---

## 💻 Verwendung

### Bot starten

```bash
# Mit Standard-Konfiguration
python core/bot.py

# Mit custom Konfiguration
python -c "from core.bot import SolanaSniperBot; bot = SolanaSniperBot({'min_balance': 0.5}); asyncio.run(bot.initialize()); asyncio.run(bot.start())"
```

### Status abrufen

Der Bot-Status kann über die `get_status()` Methode abgerufen werden:

```python
status = bot.get_status()
print(f"Offene Positionen: {status['open_positions']}")
print(f"Daily P&L: ${status['daily_pnl']:.2f}")
print(f"Win-Rate: {status['win_rate']:.1f}%")
```

### Emergency Kill Switch

```python
# Manuell aktivieren
bot.emergency_switch.activate(reason="Manueller Stop")

# Oder Tastenkürzel: STRG+C im Terminal
```

---

## 🧪 Testing

### Unit Tests ausführen

```bash
# Alle Tests
pytest tests/

# Mit Coverage
pytest --cov=solana_sniper_pro tests/

# Spezifischer Test
pytest tests/test_security.py::test_mint_authority_check
```

### Tests schreiben

Beispiel für einen Security-Test:

```python
import pytest
from unittest.mock import Mock
from security.rug_pull_checker import RugPullChecker

def test_mint_authority_check():
    mock_rpc = Mock()
    mock_rpc.get_account_info_json_parsed.return_value = Mock(
        value=Mock(data=Mock(parsed={"info": {"mintAuthority": None}}))
    )
    
    checker = RugPullChecker(mock_rpc)
    result = await checker.check_mint_authority("TOKEN_ADDRESS")
    
    assert result.passed == True
    assert result.severity == "critical"
```

---

## 🐳 Deployment

### Docker (Empfohlen)

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Logs
docker-compose logs -f bot

# Stop
docker-compose down
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  bot:
    build: .
    restart: always
    environment:
      - SOLANA_PRIVATE_KEY=${SOLANA_PRIVATE_KEY}
      - RPC_ENDPOINT=${RPC_ENDPOINT}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

### Production Checklist

- [ ] Environment Variables gesetzt
- [ ] Private Keys verschlüsselt
- [ ] RPC Endpoints konfiguriert
- [ ] Logging aktiviert
- [ ] Health-Monitoring eingerichtet
- [ ] Backups konfiguriert
- [ ] Notfallplan erstellt

---

## 🔧 Troubleshooting

### Häufige Probleme

#### "Private Key nicht gefunden"

**Lösung:**
```bash
# Prüfe ob .env existiert
ls -la .env

# Prüfe Inhalt
cat .env | grep SOLANA_PRIVATE_KEY

# Key-Format validieren (Base58, 64 Bytes decoded)
```

#### "Wallet-Balance zu niedrig"

**Lösung:**
- Mindestens 0.1 SOL in Wallet einzahlen
- `MIN_BALANCE` in Config reduzieren (nicht empfohlen)

#### "RPC Request fehlgeschlagen"

**Lösung:**
- RPC Endpoint wechseln
- API-Key prüfen (bei Helius/Triton)
- Internet-Verbindung checken

#### "Token blockiert"

**Ursache:** Sicherheitschecks haben Risiken erkannt

**Optionen:**
1. Finger weg (empfohlen!)
2. Thresholds anpassen (nur für Experten)
3. Token manuell analysieren

### Logs einsehen

```bash
# Log-Dateien
tail -f logs/bot.log

# Nur Errors
grep ERROR logs/bot.log

# Letzte 100 Zeilen
tail -n 100 logs/bot.log
```

---

## 📞 Support & Contact

- **Issues:** GitHub Issues verwenden
- **Discord:** [Link zum Discord Server]
- **Telegram:** [Link zur Telegram Gruppe]

---

## 📄 Lizenz

MIT License - Siehe LICENSE Datei

---

## 🙏 Disclaimer

**DIESER BOT WIRD OHNE JEGLICHE GARANTIE BEREITGESTELLT.**

- Der Bot ist ein experimentelles Werkzeug
- Past Performance garantiert keine zukünftigen Ergebnisse
- Crypto-Trading ist hochriskant
- Entwickler haften nicht für Verluste

**Trade verantwortungsbewusst und nur was du bereit bist zu verlieren!**

---

## 🚀 Roadmap

- [x] Phase 1: Grundgerüst & Sicherheit (Woche 1-2)
- [ ] Phase 2: UI & Integration (Woche 3-4)
- [ ] Phase 3: Advanced Features (Woche 5-8)
- [ ] Phase 4: Optimization & Scaling (Woche 9+)

---

**Viel Erfolg beim Trading! 🚀📈**

Denk immer daran: **Sicherheit > Profit!**
