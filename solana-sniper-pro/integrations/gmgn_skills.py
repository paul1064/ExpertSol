"""
GMGN Skill Manager

Manages GMGN.ai skills integration for Solana Sniper Pro.
Provides on-demand skill discovery, recommendation, and activation.

Skills Categories (prioritized for trading):
1. Smart Money Tracking - Follow profitable wallets
2. Token Research - Deep token analysis
3. KOL Signals - Key Opinion Leader buy signals  
4. Market Data - Real-time market information
5. Wallet Analysis - Profile wallet behavior
6. Launch Detection - New token opportunities
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """Priority categories for trading skills."""
    SMART_MONEY = "smart_money"
    TOKEN_RESEARCH = "token_research"
    KOL_SIGNALS = "kol_signals"
    MARKET_DATA = "market_data"
    WALLET_ANALYSIS = "wallet_analysis"
    LAUNCH_DETECTION = "launch_detection"
    RISK_MANAGEMENT = "risk_management"
    GENERAL = "general"


@dataclass
class Skill:
    """Represents a GMGN skill."""
    title: str
    subtitle: str
    description: str
    category: SkillCategory
    url: str
    capabilities: List[str]
    is_installed: bool = False
    is_active: bool = False
    priority_score: float = 0.0


class GMGNSkillManager:
    """
    Manages GMGN.ai skills for enhanced trading capabilities.
    
    Features:
    - On-demand skill search (not bulk install)
    - Priority-based recommendations
    - Skill activation/deactivation
    - Performance tracking per skill
    
    Usage:
        manager = GMGNSkillManager()
        await manager.initialize()
        
        # Search for specific skill type
        skills = await manager.search_skills("smart money")
        
        # Get recommendations for current market conditions
        recommended = manager.get_recommendations(market_condition="bull")
        
        # Activate a skill
        await manager.activate_skill("skill_name")
    """
    
    # Static skills directory (curated list based on gmgn.ai offerings)
    SKILLS_DIRECTORY = [
        {
            "title": "Smart Money Tracker",
            "subtitle": "Track and follow profitable whale wallets",
            "description": "Real-time monitoring of top-performing wallets with automatic alerts when they enter positions",
            "category": "smart_money",
            "url": "https://gmgn.ai/skills/smart-money-tracker",
            "capabilities": [
                "Track top 100 smart money wallets",
                "Real-time buy/sell alerts",
                "Win rate statistics",
                "PnL tracking",
                "Position copying"
            ],
            "priority": 10.0
        },
        {
            "title": "KOL Signal Monitor",
            "subtitle": "Monitor Key Opinion Leader trades",
            "description": "Track trades from verified crypto influencers and KOLs with proven track records",
            "category": "kol_signals",
            "url": "https://gmgn.ai/skills/kol-signals",
            "capabilities": [
                "Monitor 50+ verified KOLs",
                "Signal confidence scoring",
                "Follower count tracking",
                "Historical performance",
                "Auto-copy trading"
            ],
            "priority": 9.5
        },
        {
            "title": "Token Security Scanner",
            "subtitle": "Advanced rug-pull and honeypot detection",
            "description": "Comprehensive security analysis using multiple data sources and ML models",
            "category": "token_research",
            "url": "https://gmgn.ai/skills/security-scanner",
            "capabilities": [
                "Honeypot detection",
                "Rug-pull risk scoring",
                "LP lock verification",
                "Mint authority check",
                "Holder distribution analysis"
            ],
            "priority": 10.0
        },
        {
            "title": "New Pair Detector",
            "subtitle": "Instant new token launch notifications",
            "description": "Be first to know about new token launches on Raydium, Pump.fun, and other DEXs",
            "category": "launch_detection",
            "url": "https://gmgn.ai/skills/new-pair-detector",
            "capabilities": [
                "Sub-second launch detection",
                "Multi-DEX support",
                "Initial liquidity tracking",
                "Creator wallet monitoring",
                "Early bird alerts"
            ],
            "priority": 9.0
        },
        {
            "title": "Wallet Profiler",
            "subtitle": "Deep wallet behavior analysis",
            "description": "Comprehensive wallet profiling including trading patterns, preferences, and performance",
            "category": "wallet_analysis",
            "url": "https://gmgn.ai/skills/wallet-profiler",
            "capabilities": [
                "Trading history analysis",
                "Token preferences",
                "Hold time statistics",
                "Profit/loss breakdown",
                "Behavioral patterns"
            ],
            "priority": 8.5
        },
        {
            "title": "Market Sentiment Analyzer",
            "subtitle": "Real-time market sentiment from multiple sources",
            "description": "Aggregate sentiment from social media, news, and on-chain activity",
            "category": "market_data",
            "url": "https://gmgn.ai/skills/sentiment-analyzer",
            "capabilities": [
                "Twitter sentiment",
                "Telegram group monitoring",
                "News impact analysis",
                "On-chain flow tracking",
                "Sentiment scoring"
            ],
            "priority": 8.0
        },
        {
            "title": "Liquidity Monitor",
            "subtitle": "Track liquidity changes and LP movements",
            "description": "Monitor liquidity pools for additions, removals, and suspicious activities",
            "category": "token_research",
            "url": "https://gmgn.ai/skills/liquidity-monitor",
            "capabilities": [
                "LP change alerts",
                "Whale LP movements",
                "Lock expiration warnings",
                "Liquidity concentration",
                "Rug-pull prevention"
            ],
            "priority": 9.0
        },
        {
            "title": "Trending Tokens",
            "subtitle": "Discover trending tokens before they moon",
            "description": "Algorithmic detection of trending tokens based on volume, social buzz, and smart money flow",
            "category": "market_data",
            "url": "https://gmgn.ai/skills/trending-tokens",
            "capabilities": [
                "Volume spike detection",
                "Social mentions tracking",
                "Smart money inflow",
                "Trend scoring",
                "Early discovery"
            ],
            "priority": 8.5
        },
        {
            "title": "Dev Activity Tracker",
            "subtitle": "Monitor developer wallet activities",
            "description": "Track token creator and developer wallets for sell-offs or suspicious behavior",
            "category": "token_research",
            "url": "https://gmgn.ai/skills/dev-tracker",
            "capabilities": [
                "Creator wallet identification",
                "Dev sell alerts",
                "Team token movements",
                "Vesting schedule tracking",
                "Insider trading detection"
            ],
            "priority": 9.0
        },
        {
            "title": "Risk Calculator",
            "subtitle": "Dynamic position sizing and risk assessment",
            "description": "Calculate optimal position sizes based on token risk, market conditions, and portfolio exposure",
            "category": "risk_management",
            "url": "https://gmgn.ai/skills/risk-calculator",
            "capabilities": [
                "Position sizing",
                "Risk-reward calculation",
                "Portfolio exposure",
                "Correlation analysis",
                "Max loss protection"
            ],
            "priority": 8.0
        },
        {
            "title": "Insider Trading Detector",
            "subtitle": "Identify suspicious pre-launch trading patterns",
            "description": "Detect potential insider trading by analyzing wallet clusters and pre-launch accumulation",
            "category": "token_research",
            "url": "https://gmgn.ai/skills/insider-detector",
            "capabilities": [
                "Wallet cluster analysis",
                "Pre-launch tracking",
                "Suspicious pattern detection",
                "Cluster scoring",
                "Alert system"
            ],
            "priority": 8.5
        },
        {
            "title": "Airdrop Hunter",
            "subtitle": "Track eligible airdrops and claim opportunities",
            "description": "Monitor your wallet for eligible airdrops and upcoming claim opportunities",
            "category": "general",
            "url": "https://gmgn.ai/skills/airdrop-hunter",
            "capabilities": [
                "Airdrop eligibility check",
                "Claim reminders",
                "Historical airdrops",
                "Value estimation",
                "Multi-wallet support"
            ],
            "priority": 5.0
        }
    ]
    
    def __init__(self, auto_initialize: bool = True):
        """
        Initialize Skill Manager
        
        Args:
            auto_initialize: Whether to automatically load skills directory
        """
        self.skills: Dict[str, Skill] = {}
        self.active_skills: List[str] = []
        self._http_client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        
        if auto_initialize:
            asyncio.create_task(self.initialize())
    
    async def initialize(self):
        """Initialize the skill manager and load skills directory."""
        if self._initialized:
            return
        
        self._http_client = httpx.AsyncClient(timeout=30.0)
        
        # Load skills from static directory
        for skill_data in self.SKILLS_DIRECTORY:
            skill = Skill(
                title=skill_data["title"],
                subtitle=skill_data["subtitle"],
                description=skill_data["description"],
                category=SkillCategory(skill_data["category"]),
                url=skill_data["url"],
                capabilities=skill_data["capabilities"],
                priority_score=skill_data.get("priority", 5.0)
            )
            self.skills[skill.title.lower()] = skill
        
        self._initialized = True
        logger.info(f"GMGN Skill Manager initialized with {len(self.skills)} skills")
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
    
    async def search_skills(self, query: str) -> List[Skill]:
        """
        Search skills by keyword
        
        Args:
            query: Search query (e.g., "smart money", "KOL", "security")
            
        Returns:
            List of matching skills sorted by relevance
        """
        if not self._initialized:
            await self.initialize()
        
        query_lower = query.lower()
        matches = []
        
        for skill in self.skills.values():
            score = 0.0
            
            # Title match (highest priority)
            if query_lower in skill.title.lower():
                score += 10.0
            
            # Subtitle match
            if query_lower in skill.subtitle.lower():
                score += 5.0
            
            # Description match
            if query_lower in skill.description.lower():
                score += 3.0
            
            # Capabilities match
            for cap in skill.capabilities:
                if query_lower in cap.lower():
                    score += 2.0
            
            # Category match
            if query_lower in skill.category.value:
                score += 4.0
            
            if score > 0:
                matches.append((score, skill))
        
        # Sort by relevance score
        matches.sort(key=lambda x: x[0], reverse=True)
        
        return [skill for _, skill in matches]
    
    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a specific category."""
        return [
            skill for skill in self.skills.values()
            if skill.category == category
        ]
    
    def get_recommendations(
        self,
        market_condition: str = "normal",
        trading_style: str = "balanced"
    ) -> List[Skill]:
        """
        Get skill recommendations based on market conditions and trading style
        
        Args:
            market_condition: "bull", "bear", "sideways", "volatile", "normal"
            trading_style: "aggressive", "conservative", "balanced"
            
        Returns:
            List of recommended skills sorted by priority
        """
        recommendations = []
        
        # Base priorities
        base_priorities = {
            "smart_money": 10.0,
            "token_research": 9.5,
            "kol_signals": 9.0,
            "launch_detection": 8.5,
            "wallet_analysis": 8.0,
            "market_data": 7.5,
            "risk_management": 9.0,
            "general": 5.0
        }
        
        # Adjust based on market condition
        if market_condition == "bull":
            base_priorities["launch_detection"] += 2.0
            base_priorities["kol_signals"] += 1.5
        elif market_condition == "bear":
            base_priorities["risk_management"] += 2.5
            base_priorities["token_research"] += 2.0
        elif market_condition == "volatile":
            base_priorities["risk_management"] += 3.0
            base_priorities["smart_money"] += 1.5
        
        # Adjust based on trading style
        if trading_style == "aggressive":
            base_priorities["launch_detection"] += 2.0
            base_priorities["kol_signals"] += 1.5
            base_priorities["risk_management"] -= 1.0
        elif trading_style == "conservative":
            base_priorities["token_research"] += 2.5
            base_priorities["risk_management"] += 2.0
            base_priorities["launch_detection"] -= 1.5
        
        # Calculate final scores
        for skill in self.skills.values():
            base_score = base_priorities.get(skill.category.value, 5.0)
            final_score = base_score + (skill.priority_score * 0.1)
            
            if not skill.is_installed:
                skill.priority_score = final_score
                recommendations.append(skill)
        
        # Sort by priority
        recommendations.sort(key=lambda s: s.priority_score, reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
    
    async def activate_skill(self, skill_name: str) -> bool:
        """
        Activate a skill (simulate installation)
        
        In production, this would call: npx skills add GMGNAI/gmgn-skills
        
        Args:
            skill_name: Name of the skill to activate
            
        Returns:
            True if successful
        """
        skill_key = skill_name.lower()
        
        if skill_key not in self.skills:
            logger.error(f"Skill '{skill_name}' not found")
            return False
        
        skill = self.skills[skill_key]
        
        # Simulate installation process
        try:
            # In production: subprocess.run(["npx", "skills", "add", f"GMGNAI/gmgn-skills/{skill_name}"])
            
            skill.is_installed = True
            skill.is_active = True
            self.active_skills.append(skill_key)
            
            logger.info(f"✅ Skill '{skill.title}' activated successfully")
            
            # Log capabilities
            logger.info(f"   Capabilities: {', '.join(skill.capabilities[:3])}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate skill: {str(e)}")
            return False
    
    def deactivate_skill(self, skill_name: str) -> bool:
        """Deactivate a skill."""
        skill_key = skill_name.lower()
        
        if skill_key not in self.skills:
            return False
        
        skill = self.skills[skill_key]
        skill.is_active = False
        
        if skill_key in self.active_skills:
            self.active_skills.remove(skill_key)
        
        logger.info(f"Skill '{skill.title}' deactivated")
        return True
    
    def get_active_skills(self) -> List[Skill]:
        """Get list of currently active skills."""
        return [
            self.skills[key] for key in self.active_skills
            if key in self.skills
        ]
    
    def get_skill_details(self, skill_name: str) -> Optional[Skill]:
        """Get detailed information about a specific skill."""
        return self.skills.get(skill_name.lower())
    
    async def install_recommended(
        self,
        market_condition: str = "normal",
        trading_style: str = "balanced",
        max_skills: int = 3
    ) -> List[Skill]:
        """
        Install top recommended skills automatically
        
        Args:
            market_condition: Current market condition
            trading_style: User's trading style
            max_skills: Maximum number of skills to install
            
        Returns:
            List of installed skills
        """
        recommendations = self.get_recommendations(market_condition, trading_style)
        
        installed = []
        for skill in recommendations[:max_skills]:
            if not skill.is_installed:
                success = await self.activate_skill(skill.title)
                if success:
                    installed.append(skill)
        
        return installed
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate status report of all skills."""
        total = len(self.skills)
        installed = sum(1 for s in self.skills.values() if s.is_installed)
        active = len(self.active_skills)
        
        by_category = {}
        for skill in self.skills.values():
            cat = skill.category.value
            if cat not in by_category:
                by_category[cat] = {"total": 0, "installed": 0}
            by_category[cat]["total"] += 1
            if skill.is_installed:
                by_category[cat]["installed"] += 1
        
        return {
            "total_skills": total,
            "installed": installed,
            "active": active,
            "by_category": by_category,
            "active_skill_names": self.active_skills
        }


# Singleton instance
_skill_manager: Optional[GMGNSkillManager] = None


def get_skill_manager() -> GMGNSkillManager:
    """Get or create singleton skill manager instance."""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = GMGNSkillManager(auto_initialize=False)
    return _skill_manager


async def initialize_skill_manager() -> GMGNSkillManager:
    """Initialize and return skill manager."""
    global _skill_manager
    _skill_manager = GMGNSkillManager(auto_initialize=True)
    await _skill_manager.initialize()
    return _skill_manager


if __name__ == "__main__":
    async def main():
        manager = get_skill_manager()
        await manager.initialize()
        
        print("🎯 GMGN Skill Manager\n")
        
        # Show recommendations
        print("📌 Recommended Skills (Bull Market, Aggressive):")
        recs = manager.get_recommendations("bull", "aggressive")
        for i, skill in enumerate(recs, 1):
            print(f"  {i}. {skill.title} - {skill.subtitle}")
        
        print("\n🔍 Searching for 'smart money' skills:")
        matches = await manager.search_skills("smart money")
        for skill in matches:
            print(f"  • {skill.title}: {skill.description[:60]}...")
        
        print("\n📊 Status Report:")
        report = manager.get_status_report()
        print(f"  Total: {report['total_skills']}")
        print(f"  Installed: {report['installed']}")
        print(f"  Active: {report['active']}")
        
        await manager.close()
    
    asyncio.run(main())
