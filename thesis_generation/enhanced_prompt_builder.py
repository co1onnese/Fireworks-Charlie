"""
Enhanced Cumulative Prompt Builder for Fireworks-Charlie
Implements hierarchical data organization and smart summarization
"""
from typing import List, Dict, Any, Tuple, Optional
from datetime import date, datetime, timedelta
from statistics import mean, pstdev
import logging
from .data_deduplicator import DataDeduplicator
from data_collection.technical_analyzer import TechnicalAnalyzer

logger = logging.getLogger(__name__)

class EnhancedCumulativePromptBuilder:
    """Enhanced prompt builder with hierarchical data organization and smart summarization"""
    
    def __init__(self, deduplicator: DataDeduplicator = None, technical_analyzer: TechnicalAnalyzer = None):
        """
        Initialize enhanced prompt builder
        
        Args:
            deduplicator: DataDeduplicator instance
            technical_analyzer: TechnicalAnalyzer instance
        """
        self.deduplicator = deduplicator or DataDeduplicator()
        self.technical_analyzer = technical_analyzer or TechnicalAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    def build_comprehensive_prompt(self, 
                                 ticker: str, 
                                 data_up_to_date: List[Dict[str, Any]],
                                 response_format: str = "json") -> Tuple[str, str]:
        """
        Build comprehensive prompt with hierarchical data organization
        
        Args:
            ticker: Stock ticker symbol
            data_up_to_date: List of daily data dictionaries in chronological order
            response_format: Format for response (json, text)
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        if not data_up_to_date:
            raise ValueError("No data provided for prompt building")
        
        # Deduplicate the data
        deduped_data = self.deduplicator.deduplicate_cumulative_data(ticker, data_up_to_date)
        
        # Organize data hierarchically
        organized_data = self._organize_data_hierarchically(deduped_data)
        
        # Build system prompt
        system_prompt = self._build_system_prompt(ticker, response_format)
        
        # Build user prompt with hierarchical data
        user_prompt = self._build_hierarchical_user_prompt(ticker, organized_data)
        
        return system_prompt, user_prompt
    
    def _organize_data_hierarchically(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Organize data into hierarchical structure:
        - Recent (0-7 days): Full detail
        - Medium (8-30 days): Summarized
        - Historical (31+ days): Key insights only
        """
        if not data:
            return {}
        
        # Sort data by date
        sorted_data = sorted(data, key=lambda x: x['date'])
        latest_date = sorted_data[-1]['date']
        
        # Categorize data by recency
        recent_data = []
        medium_data = []
        historical_data = []
        
        for day_data in sorted_data:
            days_ago = (latest_date - day_data['date']).days if isinstance(day_data['date'], date) else 0
            
            if days_ago <= 7:
                recent_data.append(day_data)
            elif days_ago <= 30:
                medium_data.append(day_data)
            else:
                historical_data.append(day_data)
        
        return {
            "recent": recent_data,
            "medium": medium_data,
            "historical": historical_data,
            "latest_date": latest_date
        }
    
    def _build_system_prompt(self, ticker: str, response_format: str) -> str:
        """Build comprehensive system prompt"""
        system_prompt = f"""You are an expert financial analyst specializing in comprehensive investment thesis generation for {ticker}.

Your task is to analyze all available data and generate a detailed investment thesis with the following structure:

1. **EXECUTIVE SUMMARY** (2-3 sentences)
   - Key investment recommendation (Strong Buy/Buy/Hold/Sell/Strong Sell)
   - Primary reasoning in 1-2 sentences
   - Risk assessment level

2. **TECHNICAL ANALYSIS** (Detailed)
   - Price action analysis and trend identification
   - Key technical indicators (RSI, MACD, Bollinger Bands, Moving Averages)
   - Support and resistance levels
   - Volume analysis and momentum indicators
   - Short-term (1-2 weeks) and medium-term (1-3 months) outlook

3. **FUNDAMENTAL ANALYSIS** (Comprehensive)
   - Financial health assessment (revenue, profitability, growth)
   - Valuation metrics (P/E, P/S, PEG ratios)
   - Competitive position and market share
   - Management quality and corporate governance
   - Long-term growth prospects and sustainability

4. **MARKET SENTIMENT & NEWS** (Contextual)
   - Recent news impact and sentiment analysis
   - Analyst coverage and recommendations
   - Insider trading activity and implications
   - Market expectations vs. reality

5. **MACROECONOMIC FACTORS** (Strategic)
   - Interest rate environment impact
   - Economic indicators relevance
   - Sector-specific macro trends
   - Geopolitical and regulatory considerations

6. **RISK ASSESSMENT** (Critical)
   - Key risks and mitigation strategies
   - Downside scenarios and probability
   - Volatility expectations
   - Liquidity and market risk factors

7. **INVESTMENT RECOMMENDATION** (Actionable)
   - Clear buy/sell/hold decision with conviction level
   - Target price range with time horizon
   - Position sizing recommendations
   - Key catalysts to monitor

**IMPORTANT GUIDELINES:**
- Use ALL available data sources comprehensively
- Provide specific numerical targets and timeframes
- Balance technical and fundamental analysis
- Consider both short-term trading and long-term investment perspectives
- Be explicit about uncertainty and alternative scenarios
- Support all claims with specific data points
- Maintain professional, objective tone while being decisive

**RESPONSE FORMAT:** {response_format.upper()}
- If JSON: Use structured format with clear sections
- If text: Use clear headings and bullet points
- Include specific metrics, percentages, and timeframes
- Provide actionable insights, not just observations

Focus on generating the most comprehensive and actionable investment thesis possible using all available data."""
        
        return system_prompt
    
    def _build_hierarchical_user_prompt(self, ticker: str, organized_data: Dict[str, Any]) -> str:
        """Build user prompt with hierarchical data organization"""
        prompt_parts = []
        
        # Header
        prompt_parts.append(f"=== COMPREHENSIVE INVESTMENT ANALYSIS FOR {ticker} ===")
        prompt_parts.append(f"Analysis Date: {organized_data['latest_date']}")
        prompt_parts.append("")
        
        # Recent Data (0-7 days) - Full Detail
        if organized_data['recent']:
            prompt_parts.append("?? **RECENT DATA (Last 7 Days) - FULL DETAIL**")
            prompt_parts.append("=" * 60)
            prompt_parts.extend(self._build_detailed_recent_section(ticker, organized_data['recent']))
            prompt_parts.append("")
        
        # Medium Data (8-30 days) - Summarized
        if organized_data['medium']:
            prompt_parts.append("?? **MEDIUM-TERM DATA (8-30 Days) - SUMMARIZED**")
            prompt_parts.append("=" * 60)
            prompt_parts.extend(self._build_summarized_medium_section(ticker, organized_data['medium']))
            prompt_parts.append("")
        
        # Historical Data (31+ days) - Key Insights
        if organized_data['historical']:
            prompt_parts.append("?? **HISTORICAL DATA (31+ Days) - KEY INSIGHTS**")
            prompt_parts.append("=" * 60)
            prompt_parts.extend(self._build_historical_insights_section(ticker, organized_data['historical']))
            prompt_parts.append("")
        
        # Data Quality Summary
        prompt_parts.append("?? **DATA QUALITY SUMMARY**")
        prompt_parts.append("=" * 30)
        prompt_parts.extend(self._build_data_quality_summary(organized_data))
        
        return "\n".join(prompt_parts)
    
    def _build_detailed_recent_section(self, ticker: str, recent_data: List[Dict[str, Any]]) -> List[str]:
        """Build detailed recent data section"""
        sections = []

        # Filter out compressed summaries from recent data
        daily_data = [d for d in recent_data if d.get('type') not in ['weekly_summary', 'historical_insights']]

        # Technical Analysis (Detailed)
        sections.append("**TECHNICAL ANALYSIS (Recent)**")
        sections.extend(self._build_detailed_technical_analysis(ticker, daily_data))
        sections.append("")

        # News Analysis (Detailed)
        sections.append("**NEWS & SENTIMENT (Recent)**")
        sections.extend(self._build_detailed_news_analysis(ticker, daily_data))
        sections.append("")

        # Fundamentals (Latest)
        sections.append("**FUNDAMENTALS (Latest)**")
        sections.extend(self._build_detailed_fundamentals(ticker, daily_data))
        sections.append("")

        # Insider Transactions (Recent)
        sections.append("**INSIDER ACTIVITY (Recent)**")
        sections.extend(self._build_detailed_insider_analysis(ticker, daily_data))
        sections.append("")

        return sections
    
    def _build_summarized_medium_section(self, ticker: str, medium_data: List[Dict[str, Any]]) -> List[str]:
        """Build summarized medium-term data section"""
        sections = []

        # Separate weekly summaries from daily data
        weekly_summaries = [d for d in medium_data if d.get('type') == 'weekly_summary']
        daily_data = [d for d in medium_data if d.get('type') not in ['weekly_summary', 'historical_insights']]

        # If we have pre-computed weekly summaries, use them
        if weekly_summaries:
            sections.append("**TECHNICAL TRENDS (Medium-term) - Weekly Summaries**")
            for week in weekly_summaries:
                sections.append(f"  Week of {week['date_range']}: {week.get('days_in_week', 0)} trading days")
                if week.get('technical'):
                    tech = week['technical'][0] if isinstance(week['technical'], list) else week['technical']
                    sections.append(
                        f"    Price: ${tech.get('open', 0):.2f} ? ${tech.get('close', 0):.2f} "
                        f"({tech.get('week_change_pct', 0):+.2f}%), "
                        f"Range: ${tech.get('low', 0):.2f}-${tech.get('high', 0):.2f}"
                    )
                if week.get('news'):
                    news = week['news'][0] if isinstance(week['news'], list) else week['news']
                    sections.append(
                        f"    News: {news.get('total_articles', 0)} articles, "
                        f"Sentiment: {news.get('sentiment_label', 'neutral')} ({news.get('avg_sentiment', 0):.2f})"
                    )
            sections.append("")
        else:
            # Fall back to original weekly summarization
            sections.append("**TECHNICAL TRENDS (Medium-term)**")
            sections.extend(self._build_weekly_technical_summaries(daily_data))
            sections.append("")

            sections.append("**NEWS SENTIMENT TRENDS**")
            sections.extend(self._build_news_sentiment_trends(daily_data))
            sections.append("")

        # Macro environment (from most recent data point)
        sections.append("**MACROECONOMIC ENVIRONMENT**")
        all_data = weekly_summaries + daily_data
        sections.extend(self._build_macro_summary(all_data))
        sections.append("")

        return sections
    
    def _build_historical_insights_section(self, ticker: str, historical_data: List[Dict[str, Any]]) -> List[str]:
        """Build historical insights section"""
        sections = []

        # Check if we have pre-computed insights
        insights = [d for d in historical_data if d.get('type') == 'historical_insights']

        if insights:
            # Use pre-computed insights
            sections.append("**HISTORICAL INSIGHTS (Pre-Computed)**")
            for insight in insights:
                sections.append(f"  Period: {insight.get('date_range', 'N/A')} ({insight.get('days_covered', 0)} days)")
                sections.append(f"  Price Range: ${insight.get('price_range_low', 0):.2f} - ${insight.get('price_range_high', 0):.2f} ({insight.get('price_range_pct', 0):.1f}% range)")
                sections.append(f"  Total Return: {insight.get('total_return_pct', 0):+.2f}%")
                sections.append(f"  Trend: {insight.get('trend', 'unknown')}")
                sections.append(f"  Avg Daily Return: {insight.get('avg_daily_return_pct', 0):+.2f}%")
                sections.append(f"  Daily Volatility: {insight.get('daily_volatility_pct', 0):.2f}%")
            sections.append("")
        else:
            # Fall back to computing insights from raw data
            daily_data = [d for d in historical_data if d.get('type') not in ['weekly_summary', 'historical_insights']]

            if daily_data:
                # Key price levels and patterns
                sections.append("**KEY PRICE LEVELS & PATTERNS**")
                sections.extend(self._build_price_levels_analysis(daily_data))
                sections.append("")

                # Long-term trends
                sections.append("**LONG-TERM TRENDS**")
                sections.extend(self._build_long_term_trends(daily_data))
                sections.append("")

                # Historical volatility
                sections.append("**HISTORICAL VOLATILITY**")
                sections.extend(self._build_volatility_analysis(daily_data))
                sections.append("")

        return sections
    
    def _build_detailed_technical_analysis(self, ticker: str, data: List[Dict[str, Any]]) -> List[str]:
        """Build detailed technical analysis section"""
        sections = []
        
        # Get technical analyzer insights
        technical_insights = self.technical_analyzer.generate_insights(data)
        sections.append(f"Key Technical Insights: {technical_insights}")
        sections.append("")
        
        # Daily price action
        sections.append("**Daily Price Action:**")
        for day_data in data[-5:]:  # Last 5 days
            if day_data.get('technical'):
                for tech in day_data['technical']:
                    sections.append(f"  {tech['date']}: O=${tech['open']:.2f} H=${tech['high']:.2f} L=${tech['low']:.2f} C=${tech['close']:.2f} V={tech['volume']:,}")
                    
                    # Technical indicators
                    indicators = []
                    if tech.get('sma_20'): indicators.append(f"SMA20: ${tech['sma_20']:.2f}")
                    if tech.get('sma_50'): indicators.append(f"SMA50: ${tech['sma_50']:.2f}")
                    if tech.get('ema_20'): indicators.append(f"EMA20: ${tech['ema_20']:.2f}")
                    if tech.get('rsi_14'): indicators.append(f"RSI: {tech['rsi_14']:.1f}")
                    if tech.get('macd'): indicators.append(f"MACD: {tech['macd']:.4f}")
                    if tech.get('macd_signal'): indicators.append(f"Signal: {tech['macd_signal']:.4f}")
                    if tech.get('bollinger_upper'): indicators.append(f"BB Upper: ${tech['bollinger_upper']:.2f}")
                    if tech.get('bollinger_lower'): indicators.append(f"BB Lower: ${tech['bollinger_lower']:.2f}")
                    
                    if indicators:
                        sections.append(f"    Indicators: {' | '.join(indicators)}")
        
        return sections
    
    def _build_detailed_news_analysis(self, ticker: str, data: List[Dict[str, Any]]) -> List[str]:
        """Build detailed news analysis section"""
        sections = []
        
        # Collect all news
        all_news = []
        days_with_news = 0
        days_checked = len(data)
        
        for day_data in data:
            if day_data.get('news'):
                all_news.extend(day_data['news'])
                if day_data['news']:  # If not empty list
                    days_with_news += 1
        
        if not all_news:
            # Provide more diagnostic context
            sections.append(
                f"No news articles available in this period.\n"
                f"    Note: Checked {days_checked} trading days, found news on {days_with_news} days.\n"
                f"    This may indicate limited media coverage for {ticker} during this timeframe."
            )
            return sections
        
        # Group by sentiment
        positive_news = [n for n in all_news if n.get('sentiment_score', 0) > 0.1]
        negative_news = [n for n in all_news if n.get('sentiment_score', 0) < -0.1]
        neutral_news = [n for n in all_news if -0.1 <= n.get('sentiment_score', 0) <= 0.1]
        
        sections.append(f"Total News Articles: {len(all_news)}")
        sections.append(f"Positive: {len(positive_news)} | Negative: {len(negative_news)} | Neutral: {len(neutral_news)}")
        sections.append("")
        
        # Show recent headlines
        sections.append("**Recent Headlines:**")
        for news in all_news[:10]:  # Last 10 articles
            sentiment_emoji = "??" if news.get('sentiment_score', 0) > 0.1 else "??" if news.get('sentiment_score', 0) < -0.1 else "??"
            sections.append(f"  {sentiment_emoji} {news.get('headline', 'No headline')}")
            if news.get('sentiment_score'):
                sections.append(f"    Sentiment: {news['sentiment_score']:.2f}")
        
        return sections
    
    def _build_detailed_fundamentals(self, ticker: str, data: List[Dict[str, Any]]) -> List[str]:
        """Build detailed fundamentals section"""
        sections = []
        
        # Get latest fundamentals
        latest_fundamentals = None
        for day_data in reversed(data):
            if day_data.get('fundamentals'):
                latest_fundamentals = day_data['fundamentals']
                break
        
        if not latest_fundamentals:
            sections.append("No fundamental data available")
            return sections
        
        sections.append("**Latest Financial Metrics:**")
        sections.append(f"  Market Cap: ${latest_fundamentals.get('market_cap', 'N/A'):,}" if latest_fundamentals.get('market_cap') else "  Market Cap: N/A")
        sections.append(f"  P/E Ratio: {latest_fundamentals.get('pe_ratio', 'N/A')}")
        sections.append(f"  EPS: ${latest_fundamentals.get('eps', 'N/A')}")
        sections.append(f"  Revenue: ${latest_fundamentals.get('revenue', 'N/A'):,}" if latest_fundamentals.get('revenue') else "  Revenue: N/A")
        sections.append(f"  Net Income: ${latest_fundamentals.get('net_income', 'N/A'):,}" if latest_fundamentals.get('net_income') else "  Net Income: N/A")
        
        if latest_fundamentals.get('revenue_qoq_change'):
            sections.append(f"  Revenue QoQ: {latest_fundamentals['revenue_qoq_change']:+.2f}%")
        if latest_fundamentals.get('revenue_yoy_change'):
            sections.append(f"  Revenue YoY: {latest_fundamentals['revenue_yoy_change']:+.2f}%")
        
        return sections
    
    def _build_detailed_insider_analysis(self, ticker: str, data: List[Dict[str, Any]]) -> List[str]:
        """Build detailed insider analysis section"""
        sections = []
        
        # Collect all insider transactions
        all_insider = []
        for day_data in data:
            if day_data.get('insider_transactions'):
                all_insider.extend(day_data['insider_transactions'])
        
        if not all_insider:
            sections.append("No recent insider transactions")
            return sections
        
        # Analyze transactions
        buys = [t for t in all_insider if t.get('transaction_code') == 'P']
        sells = [t for t in all_insider if t.get('transaction_code') == 'S']
        
        sections.append(f"Total Insider Transactions: {len(all_insider)}")
        sections.append(f"Buys: {len(buys)} | Sells: {len(sells)}")
        sections.append("")
        
        # Show recent transactions
        sections.append("**Recent Insider Activity:**")
        for transaction in all_insider[:10]:  # Last 10 transactions
            action = "BUY" if transaction.get('transaction_code') == 'P' else "SELL"
            sections.append(f"  {action}: {transaction.get('owner_name', 'Unknown')} - {transaction.get('shares', 0):,} shares @ ${transaction.get('price', 0):.2f}")
        
        return sections
    
    def _build_weekly_technical_summaries(self, data: List[Dict[str, Any]]) -> List[str]:
        """Build weekly technical summaries for medium-term data"""
        sections = []
        
        # Group data by week
        weekly_groups = {}
        for day_data in data:
            if day_data.get('technical'):
                week_start = day_data['date'] - timedelta(days=day_data['date'].weekday())
                if week_start not in weekly_groups:
                    weekly_groups[week_start] = []
                weekly_groups[week_start].extend(day_data['technical'])
        
        # Summarize each week
        for week_start in sorted(weekly_groups.keys()):
            week_data = weekly_groups[week_start]
            if not week_data:
                continue
            
            # Calculate week statistics
            closes = [d['close'] for d in week_data if 'close' in d]
            volumes = [d['volume'] for d in week_data if 'volume' in d]
            
            if closes:
                week_open = closes[0]
                week_close = closes[-1]
                week_change = ((week_close - week_open) / week_open) * 100
                avg_volume = sum(volumes) / len(volumes) if volumes else 0
                
                sections.append(f"  Week of {week_start}: {week_change:+.2f}% change, Avg Volume: {avg_volume:,.0f}")
        
        return sections
    
    def _build_news_sentiment_trends(self, data: List[Dict[str, Any]]) -> List[str]:
        """Build news sentiment trends for medium-term data"""
        sections = []
        
        # Collect all news with dates
        all_news = []
        for day_data in data:
            if day_data.get('news'):
                for news in day_data['news']:
                    all_news.append({
                        'date': day_data['date'],
                        'sentiment': news.get('sentiment_score', 0)
                    })
        
        if not all_news:
            sections.append("No news data available for this period")
            return sections
        
        # Calculate weekly sentiment averages
        weekly_sentiment = {}
        for news in all_news:
            week_start = news['date'] - timedelta(days=news['date'].weekday())
            if week_start not in weekly_sentiment:
                weekly_sentiment[week_start] = []
            weekly_sentiment[week_start].append(news['sentiment'])
        
        sections.append("**Weekly Sentiment Trends:**")
        for week_start in sorted(weekly_sentiment.keys()):
            sentiments = weekly_sentiment[week_start]
            avg_sentiment = sum(sentiments) / len(sentiments)
            sentiment_label = "Positive" if avg_sentiment > 0.1 else "Negative" if avg_sentiment < -0.1 else "Neutral"
            sections.append(f"  Week of {week_start}: {avg_sentiment:.2f} ({sentiment_label})")
        
        return sections
    
    def _build_macro_summary(self, data: List[Dict[str, Any]]) -> List[str]:
        """Build macroeconomic summary"""
        sections = []
        
        # Get latest macro features
        latest_macro = None
        for day_data in reversed(data):
            if day_data.get('macro_features'):
                latest_macro = day_data['macro_features']
                break
        
        if not latest_macro:
            sections.append("No macroeconomic data available")
            return sections
        
        sections.append("**Key Macro Indicators:**")
        if latest_macro.get('yield_curve_spread'):
            sections.append(f"  Yield Curve Spread: {latest_macro['yield_curve_spread']:.2f}%")
        if latest_macro.get('cpi_monthly_change'):
            sections.append(f"  CPI Monthly Change: {latest_macro['cpi_monthly_change']:+.2f}%")
        if latest_macro.get('gdp_quarterly_change'):
            sections.append(f"  GDP Quarterly Change: {latest_macro['gdp_quarterly_change']:+.2f}%")
        if latest_macro.get('unemployment_rate_change'):
            sections.append(f"  Unemployment Rate Change: {latest_macro['unemployment_rate_change']:+.2f}%")
        
        return sections
    
    def _build_price_levels_analysis(self, data: List[Dict[str, Any]]) -> List[str]:
        """Build price levels analysis for historical data"""
        sections = []
        
        # Collect all price data
        all_prices = []
        for day_data in data:
            if day_data.get('technical'):
                for tech in day_data['technical']:
                    all_prices.append({
                        'date': tech['date'],
                        'high': tech['high'],
                        'low': tech['low'],
                        'close': tech['close']
                    })
        
        if not all_prices:
            sections.append("No historical price data available")
            return sections
        
        # Calculate key levels
        highs = [p['high'] for p in all_prices]
        lows = [p['low'] for p in all_prices]
        closes = [p['close'] for p in all_prices]
        
        sections.append(f"**Price Range Analysis:**")
        sections.append(f"  Historical High: ${max(highs):.2f}")
        sections.append(f"  Historical Low: ${min(lows):.2f}")
        sections.append(f"  Current Price: ${closes[-1]:.2f}")
        sections.append(f"  Range: {((max(highs) - min(lows)) / min(lows)) * 100:.1f}%")
        
        return sections
    
    def _build_long_term_trends(self, data: List[Dict[str, Any]]) -> List[str]:
        """Build long-term trends analysis"""
        sections: List[str] = []
        records = self._collect_unique_technical_records(data)

        if len(records) < 5:
            sections.append("  Insufficient historical technical data to assess long-term trend")
            return sections

        closes = [self._safe_float(rec.get('close')) for rec in records]
        dates = [rec['date'] for rec in records]
        closes = [c for c in closes if c is not None]

        if len(closes) < 2:
            sections.append("  Not enough closing prices to evaluate long-term trend")
            return sections

        start_price = closes[0]
        end_price = closes[-1]
        total_change = self._percent_change(start_price, end_price)

        sections.append(
            f"  Price change over {len(closes)} trading days ({dates[0]} ? {dates[-1]}): {total_change:+.2f}%"
        )

        # 60-day trend if available, otherwise fallback to 30-day
        window = 60 if len(closes) >= 60 else 30 if len(closes) >= 30 else None
        if window:
            window_start_price = closes[-window]
            window_change = self._percent_change(window_start_price, end_price)
            sections.append(
                f"  Rolling {window}-day trend: {window_change:+.2f}%"
            )

        # 50-day SMA slope approximation
        sma_values = [self._safe_float(rec.get('sma_50')) for rec in records if self._safe_float(rec.get('sma_50')) is not None]
        if len(sma_values) >= 2:
            sma_trend = self._percent_change(sma_values[0], sma_values[-1])
            sections.append(
                f"  SMA(50) drift: {sma_trend:+.2f}% (longer-term momentum indicator)"
            )

        # Support/resistance from highs/lows
        highs = [self._safe_float(rec.get('high')) for rec in records if self._safe_float(rec.get('high')) is not None]
        lows = [self._safe_float(rec.get('low')) for rec in records if self._safe_float(rec.get('low')) is not None]
        if highs and lows:
            max_high = max(highs)
            min_low = min(lows)
            range_pct = self._percent_change(min_low, max_high)
            sections.append(
                f"  Trading range: high ${max_high:.2f} vs low ${min_low:.2f} ({range_pct:+.2f}% span)"
            )

        return sections
    
    def _build_volatility_analysis(self, data: List[Dict[str, Any]]) -> List[str]:
        """Build volatility analysis"""
        sections: List[str] = []
        records = self._collect_unique_technical_records(data)

        if len(records) < 2:
            sections.append("  Not enough data to compute volatility measures")
            return sections

        closes: List[float] = []
        returns: List[float] = []
        intraday_ranges: List[float] = []

        for idx, rec in enumerate(records):
            close = self._safe_float(rec.get('close'))
            if close is None:
                continue
            closes.append(close)
            if idx > 0:
                prev_close = self._safe_float(records[idx - 1].get('close'))
                if prev_close not in (None, 0):
                    returns.append(((close - prev_close) / prev_close) * 100)

            high = self._safe_float(rec.get('high'))
            low = self._safe_float(rec.get('low'))
            if None not in (high, low) and high > low:
                intraday_ranges.append((high - low) / close * 100 if close else None)

        valid_returns = [r for r in returns if r is not None]
        if len(valid_returns) >= 2:
            daily_vol = pstdev(valid_returns)
            sections.append(f"  Daily return volatility (?): {daily_vol:.2f}%")
            sections.append(f"  Average absolute return: {mean(abs(r) for r in valid_returns):.2f}%")
        else:
            sections.append("  Daily return volatility unavailable (insufficient observations)")

        valid_ranges = [r for r in intraday_ranges if r is not None]
        if valid_ranges:
            sections.append(f"  Avg intraday range: {mean(valid_ranges):.2f}% of price")

        if valid_returns:
            ninety_percentile = sorted(abs(r) for r in valid_returns)[int(0.9 * (len(valid_returns) - 1))]
            sections.append(f"  90th percentile daily move: ?{ninety_percentile:.2f}%")

        return sections

    def _collect_unique_technical_records(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect unique technical records keyed by date and sorted chronologically."""
        by_date: Dict[date, Dict[str, Any]] = {}

        for bucket in data:
            for record in bucket.get('technical', []) or []:
                record_date = self._normalize_to_date(record.get('date'))
                if record_date is None:
                    continue
                # Keep the most recent instance encountered for that date
                if record_date not in by_date:
                    normalized = dict(record)
                    normalized['date'] = record_date
                    by_date[record_date] = normalized

        return [by_date[key] for key in sorted(by_date.keys())]

    def _normalize_to_date(self, value: Any) -> Optional[date]:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
        return None

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _percent_change(self, start: Optional[float], end: Optional[float]) -> float:
        if start in (None, 0) or end is None:
            return 0.0
        return ((end - start) / start) * 100.0
    
    def _build_data_quality_summary(self, organized_data: Dict[str, Any]) -> List[str]:
        """Build data quality summary"""
        sections = []
        
        recent_count = len(organized_data['recent'])
        medium_count = len(organized_data['medium'])
        historical_count = len(organized_data['historical'])
        
        sections.append(f"Data Coverage:")
        sections.append(f"  Recent (0-7 days): {recent_count} days")
        sections.append(f"  Medium (8-30 days): {medium_count} days")
        sections.append(f"  Historical (31+ days): {historical_count} days")
        sections.append(f"  Total: {recent_count + medium_count + historical_count} days")
        
        return sections