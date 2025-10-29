"""
Fundamental Analysis Engine for Fireworks-Charlie
Provides comprehensive fundamental analysis and insights
"""
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import date

logger = logging.getLogger(__name__)

class FundamentalAnalyzer:
    """Advanced fundamental analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_fundamentals(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze fundamental data and generate insights
        
        Args:
            data: List of fundamental data dictionaries
            
        Returns:
            Dictionary with fundamental analysis
        """
        if not data:
            return {"error": "No fundamental data provided"}
        
        # Get latest fundamentals
        latest = data[0] if data else {}
        
        analysis = {
            "valuation_metrics": self._analyze_valuation_metrics(latest),
            "growth_metrics": self._analyze_growth_metrics(data),
            "profitability_metrics": self._analyze_profitability_metrics(latest),
            "financial_health": self._analyze_financial_health(latest),
            "competitive_position": self._analyze_competitive_position(latest),
            "management_quality": self._analyze_management_quality(latest)
        }
        
        return analysis
    
    def generate_insights(self, data: List[Dict[str, Any]]) -> str:
        """
        Generate key fundamental insights
        
        Args:
            data: List of fundamental data dictionaries
            
        Returns:
            String with key fundamental insights
        """
        if not data:
            return "No fundamental data available"
        
        latest = data[0]
        insights = []
        
        # Valuation insights
        if latest.get('pe_ratio'):
            pe = latest['pe_ratio']
            if pe < 15:
                insights.append(f"P/E: {pe:.1f} (Undervalued)")
            elif pe < 25:
                insights.append(f"P/E: {pe:.1f} (Fair Value)")
            else:
                insights.append(f"P/E: {pe:.1f} (Overvalued)")
        
        # Growth insights
        if latest.get('revenue_yoy_change'):
            revenue_growth = latest['revenue_yoy_change']
            if revenue_growth > 20:
                insights.append(f"Revenue Growth: {revenue_growth:+.1f}% (Strong)")
            elif revenue_growth > 10:
                insights.append(f"Revenue Growth: {revenue_growth:+.1f}% (Moderate)")
            elif revenue_growth > 0:
                insights.append(f"Revenue Growth: {revenue_growth:+.1f}% (Weak)")
            else:
                insights.append(f"Revenue Growth: {revenue_growth:+.1f}% (Declining)")
        
        # Profitability insights
        if latest.get('net_income') and latest.get('revenue'):
            net_income = latest['net_income']
            revenue = latest['revenue']
            if revenue > 0:
                margin = (net_income / revenue) * 100
                if margin > 20:
                    insights.append(f"Net Margin: {margin:.1f}% (Excellent)")
                elif margin > 10:
                    insights.append(f"Net Margin: {margin:.1f}% (Good)")
                elif margin > 5:
                    insights.append(f"Net Margin: {margin:.1f}% (Fair)")
                else:
                    insights.append(f"Net Margin: {margin:.1f}% (Poor)")
        
        return " | ".join(insights) if insights else "Limited fundamental data available"
    
    def _analyze_valuation_metrics(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze valuation metrics"""
        metrics = {}
        
        if latest.get('pe_ratio'):
            pe = latest['pe_ratio']
            if pe < 15:
                metrics['pe_assessment'] = "Undervalued"
            elif pe < 25:
                metrics['pe_assessment'] = "Fair Value"
            else:
                metrics['pe_assessment'] = "Overvalued"
            metrics['pe_ratio'] = pe
        
        if latest.get('market_cap'):
            market_cap = latest['market_cap']
            if market_cap > 200_000_000_000:  # $200B
                metrics['size_category'] = "Large Cap"
            elif market_cap > 10_000_000_000:  # $10B
                metrics['size_category'] = "Mid Cap"
            else:
                metrics['size_category'] = "Small Cap"
            metrics['market_cap'] = market_cap
        
        return metrics
    
    def _analyze_growth_metrics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze growth metrics over time"""
        if len(data) < 2:
            return {"error": "Insufficient data for growth analysis"}
        
        growth_metrics = {}
        
        # Revenue growth trends
        revenues = [d.get('revenue', 0) for d in data if d.get('revenue')]
        if len(revenues) >= 2:
            latest_revenue = revenues[0]
            previous_revenue = revenues[1]
            if previous_revenue > 0:
                growth_metrics['revenue_growth'] = ((latest_revenue - previous_revenue) / previous_revenue) * 100
        
        # Net income growth trends
        net_incomes = [d.get('net_income', 0) for d in data if d.get('net_income')]
        if len(net_incomes) >= 2:
            latest_ni = net_incomes[0]
            previous_ni = net_incomes[1]
            if previous_ni > 0:
                growth_metrics['net_income_growth'] = ((latest_ni - previous_ni) / previous_ni) * 100
        
        return growth_metrics
    
    def _analyze_profitability_metrics(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze profitability metrics"""
        metrics = {}
        
        if latest.get('net_income') and latest.get('revenue'):
            net_income = latest['net_income']
            revenue = latest['revenue']
            if revenue > 0:
                margin = (net_income / revenue) * 100
                metrics['net_margin'] = margin
                
                if margin > 20:
                    metrics['profitability_assessment'] = "Excellent"
                elif margin > 10:
                    metrics['profitability_assessment'] = "Good"
                elif margin > 5:
                    metrics['profitability_assessment'] = "Fair"
                else:
                    metrics['profitability_assessment'] = "Poor"
        
        if latest.get('eps'):
            metrics['eps'] = latest['eps']
        
        return metrics
    
    def _analyze_financial_health(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial health indicators"""

        def _to_float(value: Any) -> Optional[float]:
            if value in (None, "", "NaN"):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        total_assets = _to_float(latest.get('total_assets'))
        total_liabilities = _to_float(latest.get('total_liabilities'))
        stockholder_equity = _to_float(latest.get('stockholder_equity'))
        total_debt = _to_float(latest.get('total_debt'))
        cash_and_equivalents = _to_float(latest.get('cash_and_equivalents'))
        operating_income = _to_float(latest.get('operating_income'))

        health: Dict[str, Any] = {
            'metrics': {},
            'warnings': [],
        }

        # Capital structure & leverage
        if total_debt is not None and stockholder_equity not in (None, 0):
            debt_to_equity = total_debt / stockholder_equity if stockholder_equity else None
            health['metrics']['debt_to_equity'] = debt_to_equity
            if debt_to_equity is not None:
                if debt_to_equity < 0.8:
                    health['metrics']['leverage_assessment'] = 'Low leverage'
                elif debt_to_equity < 1.5:
                    health['metrics']['leverage_assessment'] = 'Moderate leverage'
                else:
                    health['metrics']['leverage_assessment'] = 'High leverage'
                    health['warnings'].append('Debt-to-equity ratio elevated')

        if total_assets not in (None, 0) and stockholder_equity is not None:
            equity_ratio = stockholder_equity / total_assets
            health['metrics']['equity_ratio'] = equity_ratio
            if equity_ratio < 0.3:
                health['warnings'].append('Low equity ratio indicates balance-sheet risk')

        if total_debt is not None:
            net_debt = total_debt - (cash_and_equivalents or 0.0)
            health['metrics']['net_debt'] = net_debt
            if net_debt < 0:
                health['metrics']['net_debt_status'] = 'Net cash position'
            elif net_debt > 0 and stockholder_equity not in (None, 0):
                net_debt_to_equity = net_debt / stockholder_equity
                health['metrics']['net_debt_to_equity'] = net_debt_to_equity
                if net_debt_to_equity > 1.0:
                    health['warnings'].append('Net debt exceeds shareholder equity')

        if total_liabilities not in (None, 0) and cash_and_equivalents is not None:
            cash_to_liabilities = cash_and_equivalents / total_liabilities
            health['metrics']['cash_to_liabilities'] = cash_to_liabilities
            if cash_to_liabilities >= 0.5:
                health['metrics']['liquidity_assessment'] = 'Healthy liquidity buffer'
            elif cash_to_liabilities >= 0.2:
                health['metrics']['liquidity_assessment'] = 'Moderate liquidity'
            else:
                health['metrics']['liquidity_assessment'] = 'Tight liquidity'
                health['warnings'].append('Limited cash relative to liabilities')

        if operating_income is not None and total_debt not in (None, 0):
            operating_income_to_debt = operating_income / total_debt
            health['metrics']['operating_income_to_debt'] = operating_income_to_debt
            if operating_income_to_debt < 0.1:
                health['warnings'].append('Operating income may not cover debt obligations')

        # Determine overall assessment based on warnings/metrics availability
        if not health['metrics']:
            health['assessment'] = 'Insufficient data for financial health analysis'
        elif not health['warnings']:
            health['assessment'] = 'Balance sheet appears healthy'
        elif len(health['warnings']) <= 2:
            health['assessment'] = 'Financial health shows areas to monitor'
        else:
            health['assessment'] = 'Financial health presents notable risks'

        return health
    
    def _analyze_competitive_position(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitive position"""
        position = {}
        
        # Market cap can indicate competitive position
        if latest.get('market_cap'):
            market_cap = latest['market_cap']
            if market_cap > 500_000_000_000:  # $500B
                position['market_position'] = "Market Leader"
            elif market_cap > 100_000_000_000:  # $100B
                position['market_position'] = "Major Player"
            else:
                position['market_position'] = "Smaller Player"
        
        return position
    
    def _analyze_management_quality(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze management quality indicators based on insider transactions.

        Examines:
        - Insider buying vs selling patterns
        - Large transactions (>$100K)
        - Recent ownership changes
        - Transaction timing and frequency
        """
        quality = {}

        try:
            # Get insider transaction data from latest context
            insider_data = latest.get('insider_transactions', [])

            if not insider_data:
                quality['assessment'] = "Neutral - No recent insider transaction data available"
                quality['signal'] = "neutral"
                quality['details'] = "Insufficient data for management quality assessment"
                return quality

            # Analyze last 90 days of insider activity
            buy_count = 0
            sell_count = 0
            buy_value = 0.0
            sell_value = 0.0
            large_buys = []
            large_sells = []

            for transaction in insider_data:
                trans_code = transaction.get('transaction_code', '')
                amount = float(transaction.get('amount', 0) or 0)
                shares = int(transaction.get('shares', 0) or 0)
                owner = transaction.get('owner_name', 'Unknown')

                # Classify transaction type
                # P = Purchase, A = Award, M = Exercise
                # S = Sale, G = Gift
                if trans_code in ['P', 'A', 'M']:
                    buy_count += 1
                    buy_value += amount
                    if amount > 100000:  # Large buy > $100K
                        large_buys.append({
                            'owner': owner,
                            'shares': shares,
                            'amount': amount
                        })
                elif trans_code in ['S', 'G']:
                    sell_count += 1
                    sell_value += amount
                    if amount > 100000:  # Large sell > $100K
                        large_sells.append({
                            'owner': owner,
                            'shares': shares,
                            'amount': amount
                        })

            # Calculate net sentiment
            total_transactions = buy_count + sell_count
            if total_transactions == 0:
                quality['assessment'] = "Neutral - No transaction activity"
                quality['signal'] = "neutral"
                return quality

            buy_ratio = buy_count / total_transactions if total_transactions > 0 else 0
            net_value = buy_value - sell_value

            # Generate assessment
            if buy_ratio >= 0.7 and net_value > 0:
                quality['assessment'] = "Positive - Strong insider buying signal"
                quality['signal'] = "bullish"
                quality['confidence'] = "high"
            elif buy_ratio >= 0.6 and net_value > 0:
                quality['assessment'] = "Positive - Moderate insider buying"
                quality['signal'] = "bullish"
                quality['confidence'] = "medium"
            elif buy_ratio <= 0.3 and net_value < 0:
                quality['assessment'] = "Negative - Significant insider selling"
                quality['signal'] = "bearish"
                quality['confidence'] = "high"
            elif buy_ratio <= 0.4 and net_value < 0:
                quality['assessment'] = "Negative - Moderate insider selling"
                quality['signal'] = "bearish"
                quality['confidence'] = "medium"
            else:
                quality['assessment'] = "Neutral - Mixed insider activity"
                quality['signal'] = "neutral"
                quality['confidence'] = "medium"

            # Add detailed metrics
            quality['details'] = {
                'buy_count': buy_count,
                'sell_count': sell_count,
                'buy_value': round(buy_value, 2),
                'sell_value': round(sell_value, 2),
                'net_value': round(net_value, 2),
                'buy_ratio': round(buy_ratio, 3),
                'large_buys_count': len(large_buys),
                'large_sells_count': len(large_sells)
            }

            # Note significant large transactions
            if len(large_buys) > 0:
                quality['notable_buys'] = f"{len(large_buys)} large purchase(s) over $100K"
            if len(large_sells) > 0:
                quality['notable_sells'] = f"{len(large_sells)} large sale(s) over $100K"

        except Exception as e:
            quality['assessment'] = f"Error analyzing management quality: {str(e)}"
            quality['signal'] = "neutral"
            quality['error'] = str(e)

        return quality