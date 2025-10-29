"""
Macroeconomic Analysis Engine for Fireworks-Charlie
Provides comprehensive macroeconomic analysis and insights
"""
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import date, datetime

logger = logging.getLogger(__name__)

class MacroAnalyzer:
    """Advanced macroeconomic analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_macro_environment(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze macroeconomic environment
        
        Args:
            data: List of macro data dictionaries
            
        Returns:
            Dictionary with macro analysis
        """
        if not data:
            return {"error": "No macro data provided"}
        
        analysis = {
            "interest_rate_environment": self._analyze_interest_rates(data),
            "inflation_environment": self._analyze_inflation(data),
            "economic_growth": self._analyze_economic_growth(data),
            "employment_environment": self._analyze_employment(data),
            "market_conditions": self._assess_market_conditions(data)
        }
        
        return analysis
    
    def generate_insights(self, data: List[Dict[str, Any]]) -> str:
        """
        Generate key macro insights
        
        Args:
            data: List of macro data dictionaries
            
        Returns:
            String with key macro insights
        """
        if not data:
            return "No macro data available"
        
        latest = data[0] if data else {}
        insights = []
        
        # Yield curve analysis
        if latest.get('yield_curve_spread'):
            spread = latest['yield_curve_spread']
            if spread > 2.0:
                insights.append(f"Yield Curve: Steep ({spread:.2f}%)")
            elif spread > 0.5:
                insights.append(f"Yield Curve: Normal ({spread:.2f}%)")
            elif spread > 0:
                insights.append(f"Yield Curve: Flat ({spread:.2f}%)")
            else:
                insights.append(f"Yield Curve: Inverted ({spread:.2f}%)")
        
        # Inflation analysis
        if latest.get('cpi_monthly_change'):
            cpi = latest['cpi_monthly_change']
            if cpi > 0.5:
                insights.append(f"Inflation: High ({cpi:+.2f}%)")
            elif cpi > 0.2:
                insights.append(f"Inflation: Moderate ({cpi:+.2f}%)")
            elif cpi > 0:
                insights.append(f"Inflation: Low ({cpi:+.2f}%)")
            else:
                insights.append(f"Inflation: Deflationary ({cpi:+.2f}%)")
        
        # GDP analysis
        if latest.get('gdp_quarterly_change'):
            gdp = latest['gdp_quarterly_change']
            if gdp > 3.0:
                insights.append(f"GDP Growth: Strong ({gdp:+.2f}%)")
            elif gdp > 1.0:
                insights.append(f"GDP Growth: Moderate ({gdp:+.2f}%)")
            elif gdp > 0:
                insights.append(f"GDP Growth: Weak ({gdp:+.2f}%)")
            else:
                insights.append(f"GDP Growth: Negative ({gdp:+.2f}%)")
        
        # Unemployment analysis
        if latest.get('unemployment_rate_change'):
            unemployment = latest['unemployment_rate_change']
            if unemployment < -0.5:
                insights.append(f"Unemployment: Improving ({unemployment:+.2f}%)")
            elif unemployment < 0.5:
                insights.append(f"Unemployment: Stable ({unemployment:+.2f}%)")
            else:
                insights.append(f"Unemployment: Rising ({unemployment:+.2f}%)")
        
        return " | ".join(insights) if insights else "Limited macro data available"
    
    def _analyze_interest_rates(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze interest rate environment"""
        latest = data[0] if data else {}
        
        interest_analysis = {}
        
        # Yield curve analysis
        if latest.get('yield_curve_spread'):
            spread = latest['yield_curve_spread']
            interest_analysis['yield_curve_spread'] = spread
            
            if spread > 2.0:
                interest_analysis['yield_curve_assessment'] = "Steep - Economic Expansion Expected"
            elif spread > 0.5:
                interest_analysis['yield_curve_assessment'] = "Normal - Healthy Economic Conditions"
            elif spread > 0:
                interest_analysis['yield_curve_assessment'] = "Flat - Economic Uncertainty"
            else:
                interest_analysis['yield_curve_assessment'] = "Inverted - Recession Risk"
        
        return interest_analysis
    
    def _analyze_inflation(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze inflation environment"""
        latest = data[0] if data else {}
        
        inflation_analysis = {}
        
        if latest.get('cpi_monthly_change'):
            cpi = latest['cpi_monthly_change']
            inflation_analysis['cpi_monthly_change'] = cpi
            
            if cpi > 0.5:
                inflation_analysis['inflation_assessment'] = "High - Monetary Tightening Likely"
            elif cpi > 0.2:
                inflation_analysis['inflation_assessment'] = "Moderate - Stable Policy Expected"
            elif cpi > 0:
                inflation_analysis['inflation_assessment'] = "Low - Accommodative Policy Possible"
            else:
                inflation_analysis['inflation_assessment'] = "Deflationary - Stimulus Likely"
        
        return inflation_analysis
    
    def _analyze_economic_growth(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze economic growth indicators"""
        latest = data[0] if data else {}
        
        growth_analysis = {}
        
        if latest.get('gdp_quarterly_change'):
            gdp = latest['gdp_quarterly_change']
            growth_analysis['gdp_quarterly_change'] = gdp
            
            if gdp > 3.0:
                growth_analysis['growth_assessment'] = "Strong - Bullish for Equities"
            elif gdp > 1.0:
                growth_analysis['growth_assessment'] = "Moderate - Mixed Market Impact"
            elif gdp > 0:
                growth_analysis['growth_assessment'] = "Weak - Defensive Positioning"
            else:
                growth_analysis['growth_assessment'] = "Negative - Risk-Off Environment"
        
        return growth_analysis
    
    def _analyze_employment(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze employment environment"""
        latest = data[0] if data else {}
        
        employment_analysis = {}
        
        if latest.get('unemployment_rate_change'):
            unemployment = latest['unemployment_rate_change']
            employment_analysis['unemployment_rate_change'] = unemployment
            
            if unemployment < -0.5:
                employment_analysis['employment_assessment'] = "Improving - Consumer Confidence Rising"
            elif unemployment < 0.5:
                employment_analysis['employment_assessment'] = "Stable - Neutral Market Impact"
            else:
                employment_analysis['employment_assessment'] = "Deteriorating - Consumer Spending Risk"
        
        return employment_analysis
    
    def _assess_market_conditions(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall market conditions based on macro factors"""
        latest = data[0] if data else {}
        
        conditions = {
            "overall_assessment": "Neutral",
            "risk_level": "Medium",
            "market_outlook": "Mixed"
        }
        
        # Simple scoring system based on available indicators
        score = 0
        factors = 0
        
        # Yield curve factor
        if latest.get('yield_curve_spread'):
            spread = latest['yield_curve_spread']
            if spread > 1.0:
                score += 1
            elif spread < 0:
                score -= 1
            factors += 1
        
        # Inflation factor
        if latest.get('cpi_monthly_change'):
            cpi = latest['cpi_monthly_change']
            if 0.2 <= cpi <= 0.5:
                score += 1
            elif cpi > 0.5 or cpi < 0:
                score -= 1
            factors += 1
        
        # GDP factor
        if latest.get('gdp_quarterly_change'):
            gdp = latest['gdp_quarterly_change']
            if gdp > 2.0:
                score += 1
            elif gdp < 0:
                score -= 1
            factors += 1
        
        # Unemployment factor
        if latest.get('unemployment_rate_change'):
            unemployment = latest['unemployment_rate_change']
            if unemployment < 0:
                score += 1
            elif unemployment > 0.5:
                score -= 1
            factors += 1
        
        if factors > 0:
            avg_score = score / factors
            if avg_score > 0.5:
                conditions['overall_assessment'] = "Positive"
                conditions['risk_level'] = "Low"
                conditions['market_outlook'] = "Bullish"
            elif avg_score < -0.5:
                conditions['overall_assessment'] = "Negative"
                conditions['risk_level'] = "High"
                conditions['market_outlook'] = "Bearish"
        
        return conditions