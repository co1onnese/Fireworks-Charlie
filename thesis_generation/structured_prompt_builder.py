"""
Structured Prompt Builder for 5-7 Section Investment Thesis Format

This module creates prompts specifically designed to generate structured responses
with 5-7 sections: fundamentals, technical, news, valuation, risk_assessment, macro, conclusion.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal

from data_collection.database_manager import (
    DatabaseManager, Ticker, MarketData, Fundamental, News,
    InsiderTransaction, MacroFeature, AnalystRecommendation
)
from orchestration.market_calendar import MarketCalendar

logger = logging.getLogger(__name__)


class StructuredPromptBuilder:
    """
    Builds structured prompts for 5-7 section investment thesis format.
    
    Response structure:
    1. fundamentals - Financial statements, balance sheet, income performance
    2. technical - Price action, indicators, momentum
    3. news - Recent developments, earnings, sentiment
    4. valuation - Based on earnings and growth metrics
    5. risk_assessment - Data center delays, regulatory risks
    6. macro - Economic environment impact
    7. conclusion - Final recommendation (Strong Buy/Buy/Hold/Sell/Strong Sell)
    """
    
    def __init__(self, db_manager: DatabaseManager, market_calendar: Optional[MarketCalendar] = None):
        """
        Initialize structured prompt builder.
        
        Args:
            db_manager: Database manager instance
            market_calendar: Market calendar instance (optional, will create if not provided)
        """
        self.db_manager = db_manager
        self.market_calendar = market_calendar or MarketCalendar()
        self.logger = logging.getLogger(__name__)
    
    def build_structured_prompt(self, ticker: str, as_of_date: date) -> Tuple[str, str]:
        """
        Build structured prompt for a ticker as of a specific date.
        
        Args:
            ticker: Stock ticker symbol
            as_of_date: Analysis date (point-in-time)
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        session = self.db_manager.get_session()
        try:
            # Get ticker ID
            ticker_obj = session.query(Ticker).filter_by(symbol=ticker).first()
            if not ticker_obj:
                raise ValueError(f"Ticker {ticker} not found in database")
            
            ticker_id = ticker_obj.ticker_id
            
            # Query all required data
            fundamentals = self._query_fundamentals(session, ticker_id, as_of_date)
            news_buckets = self._query_news_by_buckets(session, ticker_id, as_of_date)
            price_history = self._query_price_history(session, ticker_id, as_of_date, days=11)
            insider_transactions = self._query_insider_transactions(session, ticker_id, as_of_date)
            macro_indicators = self._query_macro_indicators(session, as_of_date, days=90)
            analyst_recommendations = self._query_analyst_recommendations(session, ticker_id, as_of_date)
            
            # Build prompts
            system_prompt = self._build_system_prompt(ticker)
            user_prompt = self._build_user_prompt(
                ticker, as_of_date, fundamentals, news_buckets, price_history,
                insider_transactions, macro_indicators, analyst_recommendations
            )
            
            return system_prompt, user_prompt
            
        finally:
            session.close()
    
    def _query_fundamentals(self, session, ticker_id: int, as_of_date: date) -> List[Dict[str, Any]]:
        """
        Query quarterly fundamentals with full JSONB statements.
        
        Returns most recent quarterly reports available as of the analysis date.
        """
        fundamentals = session.query(Fundamental)\
            .filter(
                Fundamental.ticker_id == ticker_id,
                Fundamental.report_date <= as_of_date
            )\
            .order_by(Fundamental.report_date.desc())\
            .limit(4)\
            .all()
        
        result = []
        for f in fundamentals:
            result.append({
                'report_date': f.report_date,
                'filing_date': f.filing_date,
                'market_cap': float(f.market_cap) if f.market_cap else None,
                'pe_ratio': float(f.pe_ratio) if f.pe_ratio else None,
                'pb_ratio': float(f.pb_ratio) if f.pb_ratio else None,
                'ps_ratio': float(f.ps_ratio) if f.ps_ratio else None,
                'eps': float(f.eps) if f.eps else None,
                'revenue': float(f.revenue) if f.revenue else None,
                'net_income': float(f.net_income) if f.net_income else None,
                'ebitda': float(f.ebitda) if f.ebitda else None,
                'total_assets': float(f.total_assets) if f.total_assets else None,
                'total_liabilities': float(f.total_liabilities) if f.total_liabilities else None,
                'cash_and_equivalents': float(f.cash_and_equivalents) if f.cash_and_equivalents else None,
                'total_debt': float(f.total_debt) if f.total_debt else None,
                'operating_cash_flow': float(f.operating_cash_flow) if f.operating_cash_flow else None,
                'free_cash_flow': float(f.free_cash_flow) if f.free_cash_flow else None,
                'revenue_qoq_pct': float(f.revenue_qoq_pct) if f.revenue_qoq_pct else None,
                'revenue_yoy_pct': float(f.revenue_yoy_pct) if f.revenue_yoy_pct else None,
                'net_income_qoq_pct': float(f.net_income_qoq_pct) if f.net_income_qoq_pct else None,
                'net_income_yoy_pct': float(f.net_income_yoy_pct) if f.net_income_yoy_pct else None,
                'balance_sheet_json': f.balance_sheet_json,
                'income_statement_json': f.income_statement_json,
                'cash_flow_json': f.cash_flow_json
            })
        
        return result
    
    def _query_news_by_buckets(self, session, ticker_id: int, as_of_date: date) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query news in time buckets: 3 trading days, 4-10 trading days, 11-30 trading days.
        
        Returns dictionary with keys: 'recent_3_days', 'recent_4_10_days', 'recent_11_30_days'
        """
        # Get trading days
        trading_days = self.market_calendar.get_trading_days(
            as_of_date - timedelta(days=60),  # Look back enough to get 30 trading days
            as_of_date
        )
        
        # Filter to only trading days up to as_of_date
        trading_days = [d for d in trading_days if d <= as_of_date]
        trading_days.sort(reverse=True)  # Most recent first
        
        if len(trading_days) < 1:
            return {
                'recent_3_days': [],
                'recent_4_10_days': [],
                'recent_11_30_days': []
            }
        
        # Define buckets
        recent_3_days = trading_days[:3] if len(trading_days) >= 3 else trading_days
        recent_4_10_days = trading_days[3:10] if len(trading_days) >= 10 else trading_days[3:]
        recent_11_30_days = trading_days[10:30] if len(trading_days) >= 30 else trading_days[10:]
        
        # Query news for each bucket
        def query_news_for_dates(dates: List[date]) -> List[Dict[str, Any]]:
            if not dates:
                return []
            min_date = min(dates)
            max_date = max(dates)
            
            news_items = session.query(News)\
                .filter(
                    News.ticker_id == ticker_id,
                    News.published_at >= min_date,
                    News.published_at <= max_date
                )\
                .order_by(News.published_at.desc())\
                .all()
            
            return [{
                'published_at': n.published_at,
                'headline': n.headline,
                'summary': n.summary,
                'content': n.content[:500] if n.content else None,  # Truncate for prompt
                'source': n.source,
                'url': n.url,
                'sentiment_score': float(n.sentiment_score) if n.sentiment_score else None,
                'sentiment_label': n.sentiment_label,
                'sentiment_confidence': float(n.sentiment_confidence) if n.sentiment_confidence else None
            } for n in news_items]
        
        return {
            'recent_3_days': query_news_for_dates(recent_3_days),
            'recent_4_10_days': query_news_for_dates(recent_4_10_days),
            'recent_11_30_days': query_news_for_dates(recent_11_30_days)
        }
    
    def _query_price_history(self, session, ticker_id: int, as_of_date: date, days: int = 11) -> List[Dict[str, Any]]:
        """
        Query exactly N trading days of price history with all technical indicators.
        
        Args:
            session: Database session
            ticker_id: Ticker ID
            as_of_date: Analysis date
            days: Number of trading days to query (default: 11)
            
        Returns:
            List of market data dictionaries, most recent first
        """
        # Get trading days
        trading_days = self.market_calendar.get_trading_days(
            as_of_date - timedelta(days=days * 2),  # Look back enough to get N trading days
            as_of_date
        )
        
        # Filter to only trading days up to as_of_date
        trading_days = [d for d in trading_days if d <= as_of_date]
        trading_days.sort(reverse=True)  # Most recent first
        
        # Get exactly N trading days
        target_dates = trading_days[:days]
        
        if not target_dates:
            return []
        
        # Query market data
        market_data = session.query(MarketData)\
            .filter(
                MarketData.ticker_id == ticker_id,
                MarketData.date.in_(target_dates)
            )\
            .order_by(MarketData.date.desc())\
            .all()
        
        result = []
        for md in market_data:
            result.append({
                'date': md.date,
                'open': float(md.open) if md.open else None,
                'high': float(md.high) if md.high else None,
                'low': float(md.low) if md.low else None,
                'close': float(md.close) if md.close else None,
                'adjusted_close': float(md.adjusted_close) if md.adjusted_close else None,
                'volume': int(md.volume) if md.volume else None,
                'sma_20': float(md.sma_20) if md.sma_20 else None,
                'sma_50': float(md.sma_50) if md.sma_50 else None,
                'ema_20': float(md.ema_20) if md.ema_20 else None,
                'rsi_14': float(md.rsi_14) if md.rsi_14 else None,
                'macd': float(md.macd) if md.macd else None,
                'macd_signal': float(md.macd_signal) if md.macd_signal else None,
                'bollinger_upper': float(md.bollinger_upper) if md.bollinger_upper else None,
                'bollinger_lower': float(md.bollinger_lower) if md.bollinger_lower else None,
                'atr_14': float(md.atr_14) if md.atr_14 else None,
                'adx_14': float(md.adx_14) if md.adx_14 else None,
                'di_plus_14': float(md.di_plus_14) if md.di_plus_14 else None,
                'di_minus_14': float(md.di_minus_14) if md.di_minus_14 else None
            })
        
        return result
    
    def _query_insider_transactions(self, session, ticker_id: int, as_of_date: date) -> List[Dict[str, Any]]:
        """
        Query recent insider transactions.
        """
        # Query last 90 days
        start_date = as_of_date - timedelta(days=90)
        
        transactions = session.query(InsiderTransaction)\
            .filter(
                InsiderTransaction.ticker_id == ticker_id,
                InsiderTransaction.transaction_date >= start_date,
                InsiderTransaction.transaction_date <= as_of_date
            )\
            .order_by(InsiderTransaction.transaction_date.desc())\
            .limit(20)\
            .all()
        
        return [{
            'transaction_date': t.transaction_date,
            'filing_date': t.filing_date,
            'owner_name': t.owner_name,
            'owner_title': t.owner_title,
            'transaction_code': t.transaction_code,
            'shares': int(t.shares) if t.shares else None,
            'transaction_price': float(t.transaction_price) if t.transaction_price else None,
            'shares_owned_after': int(t.shares_owned_after) if t.shares_owned_after else None
        } for t in transactions]
    
    def _query_macro_indicators(self, session, as_of_date: date, days: int = 90) -> Dict[str, Any]:
        """
        Query macro indicators for the past N days.
        """
        start_date = as_of_date - timedelta(days=days)
        
        # Get most recent macro features
        macro_features = session.query(MacroFeature)\
            .filter(
                MacroFeature.date >= start_date,
                MacroFeature.date <= as_of_date
            )\
            .order_by(MacroFeature.date.desc())\
            .limit(1)\
            .first()
        
        if not macro_features:
            return {}
        
        return {
            'date': macro_features.date,
            'yield_curve_10y_2y': float(macro_features.yield_curve_10y_2y) if macro_features.yield_curve_10y_2y else None,
            'yield_curve_10y_3m': float(macro_features.yield_curve_10y_3m) if macro_features.yield_curve_10y_3m else None,
            'cpi_monthly_pct': float(macro_features.cpi_monthly_pct) if macro_features.cpi_monthly_pct else None,
            'cpi_yoy_pct': float(macro_features.cpi_yoy_pct) if macro_features.cpi_yoy_pct else None,
            'pce_monthly_pct': float(macro_features.pce_monthly_pct) if macro_features.pce_monthly_pct else None,
            'pce_yoy_pct': float(macro_features.pce_yoy_pct) if macro_features.pce_yoy_pct else None,
            'gdp_qoq_pct': float(macro_features.gdp_qoq_pct) if macro_features.gdp_qoq_pct else None,
            'industrial_production_mom_pct': float(macro_features.industrial_production_mom_pct) if macro_features.industrial_production_mom_pct else None,
            'unemployment_rate': float(macro_features.unemployment_rate) if macro_features.unemployment_rate else None,
            'unemployment_rate_change': float(macro_features.unemployment_rate_change) if macro_features.unemployment_rate_change else None,
            'fed_funds_rate': float(macro_features.fed_funds_rate) if macro_features.fed_funds_rate else None
        }
    
    def _query_analyst_recommendations(self, session, ticker_id: int, as_of_date: date) -> Dict[str, Any]:
        """
        Query analyst recommendations from the last 90 days.
        
        Returns dictionary with: recent_upgrades, recent_downgrades, recent_maintains, consensus
        """
        start_date = as_of_date - timedelta(days=90)
        
        recommendations = session.query(AnalystRecommendation)\
            .filter(
                AnalystRecommendation.ticker_id == ticker_id,
                AnalystRecommendation.date >= start_date,
                AnalystRecommendation.date <= as_of_date
            )\
            .order_by(AnalystRecommendation.date.desc())\
            .limit(50)\
            .all()
        
        upgrades = []
        downgrades = []
        maintains = []
        
        for rec in recommendations:
            rec_dict = {
                'firm': rec.firm,
                'action': rec.action,
                'rating': rec.rating,
                'target_price': float(rec.target_price) if rec.target_price else None,
                'date': rec.date,
                'analyst_insights': rec.analyst_insights
            }
            
            if rec.action and 'upgrade' in rec.action.lower():
                upgrades.append(rec_dict)
            elif rec.action and 'downgrade' in rec.action.lower():
                downgrades.append(rec_dict)
            else:
                maintains.append(rec_dict)
        
        # Calculate consensus
        rating_counts = {}
        for rec in recommendations:
            rating = rec.rating or 'Unknown'
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        consensus_parts = []
        for rating, count in sorted(rating_counts.items(), key=lambda x: x[1], reverse=True):
            consensus_parts.append(f"{count} {rating}")
        consensus = ", ".join(consensus_parts) if consensus_parts else "No consensus"
        
        # Calculate average target price
        target_prices = [float(r.target_price) for r in recommendations if r.target_price]
        avg_target_price = sum(target_prices) / len(target_prices) if target_prices else None
        
        return {
            'recent_upgrades': upgrades[:10],  # Limit to 10 most recent
            'recent_downgrades': downgrades[:10],
            'recent_maintains': maintains[:10],
            'consensus': consensus,
            'average_target_price': avg_target_price,
            'total_recommendations': len(recommendations)
        }
    
    def _build_system_prompt(self, ticker: str) -> str:
        """Build system prompt with 5-7 section structure instructions."""
        return f"""You are an expert financial analyst specializing in comprehensive investment thesis generation for {ticker}.

Your task is to analyze all available data and generate a structured investment thesis in JSON format with exactly 5-7 sections:

1. **fundamentals** - Financial statements, balance sheet strength, income performance, cash flow
2. **technical** - Price action, indicators (RSI, MACD, Bollinger Bands, ATR, ADX), momentum
3. **news** - Recent developments (last 3, 4-10, 11-30 trading days), earnings, sentiment, analyst recommendations
4. **valuation** - Based on earnings and growth metrics (P/E, P/S, PEG, P/B, EV/EBITDA)
5. **risk_assessment** - Ticker-specific risks, market risks, mitigation factors, regulatory concerns
6. **macro** - Economic environment impact, key indicators (yield curve, CPI, unemployment, Fed funds rate)
7. **conclusion** - Final recommendation with 5-tier scale: "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"

**CRITICAL REQUIREMENTS:**
- You MUST respond in valid JSON format only
- The "conclusion.recommendation" field MUST be exactly one of: "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"
- Include specific numerical metrics and percentages where available
- Support all analysis with data from the provided information
- Be explicit about uncertainty and alternative scenarios
- Provide actionable insights, not just observations

**JSON RESPONSE FORMAT:**
{{
  "fundamentals": {{
    "balance_sheet_strength": "Analysis text...",
    "income_performance": "Analysis text...",
    "cash_flow": "Analysis text...",
    "key_metrics": {{
      "pe_ratio": 25.5,
      "pb_ratio": 8.2,
      "ps_ratio": 5.3,
      "debt_to_equity": 0.3,
      "revenue_growth_yoy": 12.5,
      "net_income_margin": 18.2
    }}
  }},
  "technical": {{
    "price_action": "Analysis text...",
    "indicators": {{
      "rsi_14": 58.5,
      "macd": "bullish",
      "bollinger_position": "upper_band",
      "atr_14": 2.5,
      "adx_14": 28.3
    }},
    "momentum": "Analysis text..."
  }},
  "news": {{
    "recent_3_days": "Summary text...",
    "recent_4_10_days": "Summary text...",
    "recent_11_30_days": "Summary text...",
    "sentiment_summary": "Overall sentiment...",
    "analyst_recommendations": {{
      "recent_upgrades": [...],
      "recent_downgrades": [...],
      "consensus": "Buy (12 Buy, 5 Hold, 2 Sell)"
    }}
  }},
  "valuation": {{
    "metrics": {{"pe_ratio": 25.5, "ps_ratio": 5.3, ...}},
    "assessment": "Fair value/Overvalued/Undervalued...",
    "comparison": "Comparison vs peers..."
  }},
  "risk_assessment": {{
    "ticker_specific_risks": "...",
    "market_risks": "...",
    "mitigation": "...",
    "regulatory": "..."
  }},
  "macro": {{
    "economic_environment": "...",
    "impact": "...",
    "key_indicators": {{"yield_curve_10y_2y": "+0.5%", ...}}
  }},
  "conclusion": {{
    "recommendation": "Strong Buy|Buy|Hold|Sell|Strong Sell",
    "reasoning": "Summary reasoning...",
    "confidence": 0.75,
    "target_price": "$150.00",
    "time_horizon": "3-6 months"
  }}
}}

Focus on generating a comprehensive, data-driven investment thesis using all available information."""
    
    def _build_user_prompt(self, ticker: str, as_of_date: date, fundamentals: List[Dict],
                          news_buckets: Dict[str, List[Dict]], price_history: List[Dict],
                          insider_transactions: List[Dict], macro_indicators: Dict,
                          analyst_recommendations: Dict) -> str:
        """Build user prompt with organized data sections."""
        parts = []
        
        parts.append(f"=== COMPREHENSIVE INVESTMENT ANALYSIS FOR {ticker} ===")
        parts.append(f"Analysis Date: {as_of_date}")
        parts.append("")
        
        # Fundamentals Section
        parts.append("## FUNDAMENTALS DATA")
        parts.append("=" * 60)
        if fundamentals:
            for i, fund in enumerate(fundamentals[:4], 1):  # Show up to 4 quarters
                parts.append(f"\n### Quarter {i} (Report Date: {fund['report_date']})")
                parts.append(f"Filing Date: {fund.get('filing_date', 'N/A')}")
                if fund.get('revenue'):
                    parts.append(f"Revenue: ${fund['revenue']:,.0f}")
                if fund.get('net_income'):
                    parts.append(f"Net Income: ${fund['net_income']:,.0f}")
                if fund.get('eps'):
                    parts.append(f"EPS: ${fund['eps']:.2f}")
                if fund.get('pe_ratio'):
                    parts.append(f"P/E Ratio: {fund['pe_ratio']:.2f}")
                if fund.get('revenue_yoy_pct'):
                    parts.append(f"Revenue YoY Growth: {fund['revenue_yoy_pct']*100:.2f}%")
                if fund.get('cash_and_equivalents'):
                    parts.append(f"Cash & Equivalents: ${fund['cash_and_equivalents']:,.0f}")
                if fund.get('total_debt'):
                    parts.append(f"Total Debt: ${fund['total_debt']:,.0f}")
        else:
            parts.append("No fundamental data available.")
        parts.append("")
        
        # Technical Section
        parts.append("## TECHNICAL DATA (Last 11 Trading Days)")
        parts.append("=" * 60)
        if price_history:
            for md in price_history[:11]:  # Show all 11 days
                parts.append(f"\n### {md['date']}")
                parts.append(f"OHLC: O=${md.get('open', 0):.2f} H=${md.get('high', 0):.2f} L=${md.get('low', 0):.2f} C=${md.get('close', 0):.2f}")
                parts.append(f"Volume: {md.get('volume', 0):,}")
                if md.get('rsi_14'):
                    parts.append(f"RSI(14): {md['rsi_14']:.2f}")
                if md.get('macd'):
                    parts.append(f"MACD: {md['macd']:.4f} (Signal: {md.get('macd_signal', 0):.4f})")
                if md.get('sma_20'):
                    parts.append(f"SMA(20): ${md['sma_20']:.2f}")
                if md.get('atr_14'):
                    parts.append(f"ATR(14): ${md['atr_14']:.2f}")
                if md.get('adx_14'):
                    parts.append(f"ADX(14): {md['adx_14']:.2f}")
        else:
            parts.append("No technical data available.")
        parts.append("")
        
        # News Section
        parts.append("## NEWS DATA")
        parts.append("=" * 60)
        parts.append("\n### Recent 3 Trading Days")
        if news_buckets.get('recent_3_days'):
            for news in news_buckets['recent_3_days'][:10]:
                parts.append(f"\n- [{news['published_at']}] {news.get('headline', 'N/A')}")
                if news.get('sentiment_score'):
                    parts.append(f"  Sentiment: {news['sentiment_score']:.2f} ({news.get('sentiment_label', 'N/A')})")
        else:
            parts.append("No news in last 3 trading days.")
        
        parts.append("\n### Recent 4-10 Trading Days")
        if news_buckets.get('recent_4_10_days'):
            parts.append(f"Total articles: {len(news_buckets['recent_4_10_days'])}")
            for news in news_buckets['recent_4_10_days'][:5]:
                parts.append(f"- [{news['published_at']}] {news.get('headline', 'N/A')}")
        else:
            parts.append("No news in 4-10 trading days range.")
        
        parts.append("\n### Recent 11-30 Trading Days")
        if news_buckets.get('recent_11_30_days'):
            parts.append(f"Total articles: {len(news_buckets['recent_11_30_days'])}")
            for news in news_buckets['recent_11_30_days'][:5]:
                parts.append(f"- [{news['published_at']}] {news.get('headline', 'N/A')}")
        else:
            parts.append("No news in 11-30 trading days range.")
        parts.append("")
        
        # Analyst Recommendations
        if analyst_recommendations:
            parts.append("## ANALYST RECOMMENDATIONS")
            parts.append("=" * 60)
            if analyst_recommendations.get('recent_upgrades'):
                parts.append("\n### Recent Upgrades:")
                for rec in analyst_recommendations['recent_upgrades'][:5]:
                    parts.append(f"- {rec['firm']}: {rec['action']} to {rec['rating']} (Target: ${rec.get('target_price', 'N/A')})")
            if analyst_recommendations.get('recent_downgrades'):
                parts.append("\n### Recent Downgrades:")
                for rec in analyst_recommendations['recent_downgrades'][:5]:
                    parts.append(f"- {rec['firm']}: {rec['action']} to {rec['rating']} (Target: ${rec.get('target_price', 'N/A')})")
            if analyst_recommendations.get('consensus'):
                parts.append(f"\n### Consensus: {analyst_recommendations['consensus']}")
            parts.append("")
        
        # Insider Transactions
        if insider_transactions:
            parts.append("## INSIDER TRANSACTIONS (Last 90 Days)")
            parts.append("=" * 60)
            for trans in insider_transactions[:10]:
                parts.append(f"- [{trans['transaction_date']}] {trans.get('owner_name', 'N/A')} ({trans.get('owner_title', 'N/A')})")
                parts.append(f"  {trans.get('transaction_code', 'N/A')}: {trans.get('shares', 0):,} shares @ ${trans.get('transaction_price', 0):.2f}")
            parts.append("")
        
        # Macro Section
        parts.append("## MACROECONOMIC INDICATORS")
        parts.append("=" * 60)
        if macro_indicators:
            if macro_indicators.get('yield_curve_10y_2y') is not None:
                parts.append(f"Yield Curve (10Y-2Y): {macro_indicators['yield_curve_10y_2y']*100:.2f}%")
            if macro_indicators.get('cpi_yoy_pct') is not None:
                parts.append(f"CPI YoY: {macro_indicators['cpi_yoy_pct']*100:.2f}%")
            if macro_indicators.get('unemployment_rate') is not None:
                parts.append(f"Unemployment Rate: {macro_indicators['unemployment_rate']:.2f}%")
            if macro_indicators.get('fed_funds_rate') is not None:
                parts.append(f"Fed Funds Rate: {macro_indicators['fed_funds_rate']:.2f}%")
            if macro_indicators.get('gdp_qoq_pct') is not None:
                parts.append(f"GDP QoQ: {macro_indicators['gdp_qoq_pct']*100:.2f}%")
        else:
            parts.append("No macro indicators available.")
        parts.append("")
        
        parts.append("=== END OF DATA ===")
        parts.append("\nPlease generate your structured investment thesis in JSON format as specified in the system prompt.")
        
        return "\n".join(parts)
