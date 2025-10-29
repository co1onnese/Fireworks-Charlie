"""
Cumulative prompt builder for investment thesis generation
"""
from typing import List, Dict, Any
from datetime import date, datetime
import logging
from .data_deduplicator import DataDeduplicator

logger = logging.getLogger(__name__)

class CumulativePromptBuilder:
    """Builds cumulative prompts with all historical data organized by type"""
    
    def __init__(self, deduplicator: DataDeduplicator = None):
        """
        Initialize prompt builder
        
        Args:
            deduplicator: DataDeduplicator instance (creates new one if not provided)
        """
        self.deduplicator = deduplicator or DataDeduplicator()
    
    def build_cumulative_prompt(self, 
                              ticker: str, 
                              data_up_to_date: List[Dict[str, Any]],
                              include_instructions: bool = True) -> str:
        """
        Build a cumulative prompt with all historical data up to the specified date
        
        Args:
            ticker: Stock ticker symbol
            data_up_to_date: List of daily data dictionaries in chronological order
            include_instructions: Whether to include analysis instructions
            
        Returns:
            Formatted prompt string
        """
        if not data_up_to_date:
            raise ValueError("No data provided for prompt building")
        
        # Deduplicate the data
        deduped_data = self.deduplicator.deduplicate_cumulative_data(ticker, data_up_to_date)
        
        # Build prompt sections
        prompt_parts = []
        
        # Header
        prompt_parts.append(f"=== COMPREHENSIVE INVESTMENT ANALYSIS FOR {ticker} ===")
        prompt_parts.append(f"Analysis Date: {data_up_to_date[-1]['date']}")
        prompt_parts.append(f"Historical Data Range: {data_up_to_date[0]['date']} to {data_up_to_date[-1]['date']}")
        prompt_parts.append(f"Total Trading Days Analyzed: {len(data_up_to_date)}\n")
        
        # Technical Data Section
        prompt_parts.append(self._build_technical_section(ticker, deduped_data))
        
        # Fundamental Data Section
        prompt_parts.append(self._build_fundamentals_section(ticker, deduped_data))
        
        # News and Sentiment Section
        prompt_parts.append(self._build_news_section(ticker, deduped_data))
        
        # Macroeconomic Data Section
        prompt_parts.append(self._build_macro_section(deduped_data))
        
        # Insider Transactions Section (if available)
        insider_section = self._build_insider_section(ticker, deduped_data)
        if insider_section:
            prompt_parts.append(insider_section)
        
        # Instructions (if requested)
        if include_instructions:
            prompt_parts.append(self._build_instructions())
        
        return "\n".join(prompt_parts)
    
    def _build_technical_section(self, ticker: str, data: List[Dict[str, Any]]) -> str:
        """Build technical analysis section"""
        section_parts = ["=== TECHNICAL DATA ==="]
        section_parts.append(f"Price and technical indicators for {ticker}:\n")
        
        # Group by week for more compact display
        weekly_summaries = []
        current_week = []
        
        for day_data in data:
            if not day_data.get("technical"):
                continue
                
            for tech_record in day_data["technical"]:
                current_week.append(tech_record)
                
                # If we have 5 days or it's the last record, summarize the week
                if len(current_week) >= 5 or day_data == data[-1]:
                    if current_week:
                        weekly_summaries.append(self._summarize_week_technical(current_week))
                        current_week = []
        
        section_parts.extend(weekly_summaries)
        return "\n".join(section_parts)
    
    def _summarize_week_technical(self, week_data: List[Dict[str, Any]]) -> str:
        """Summarize a week of technical data"""
        if not week_data:
            return ""
        
        start_date = week_data[0]["date"]
        end_date = week_data[-1]["date"]
        
        # Calculate week statistics
        opens = [d["open"] for d in week_data]
        closes = [d["close"] for d in week_data]
        highs = [d["high"] for d in week_data]
        lows = [d["low"] for d in week_data]
        volumes = [d["volume"] for d in week_data]
        
        week_open = opens[0]
        week_close = closes[-1]
        week_high = max(highs)
        week_low = min(lows)
        week_volume = sum(volumes)
        week_change = ((week_close - week_open) / week_open) * 100
        
        summary = f"Week {start_date} to {end_date}:\n"
        summary += f"  Open: ${week_open:.2f}, Close: ${week_close:.2f}, Change: {week_change:+.2f}%\n"
        summary += f"  High: ${week_high:.2f}, Low: ${week_low:.2f}, Volume: {week_volume:,}\n"
        
        # Include latest technical indicators
        latest = week_data[-1]
        if latest.get("sma_20"):
            summary += f"  SMA(20): ${latest['sma_20']:.2f}"
        if latest.get("ema_20"):
            summary += f", EMA(20): ${latest['ema_20']:.2f}"
        if latest.get("rsi_14"):
            summary += f", RSI(14): {latest['rsi_14']:.1f}"
        summary += "\n"
        
        return summary
    
    def _build_fundamentals_section(self, ticker: str, data: List[Dict[str, Any]]) -> str:
        """Build fundamentals section"""
        section_parts = ["\n=== FUNDAMENTAL DATA ==="]
        
        # Find all fundamentals updates
        fundamentals_updates = []
        for day_data in data:
            if day_data.get("fundamentals"):
                fundamentals_updates.append((day_data["date"], day_data["fundamentals"]))
        
        if not fundamentals_updates:
            section_parts.append("No fundamental data available in this period.")
            return "\n".join(section_parts)
        
        section_parts.append(f"Financial statements and metrics for {ticker}:\n")
        
        # Show each fundamentals update
        for update_date, fund_data in fundamentals_updates:
            section_parts.append(f"Report Date: {fund_data['report_date']} (Filed: {fund_data['filing_date']})")
            
            if fund_data.get("market_cap"):
                section_parts.append(f"  Market Cap: ${fund_data['market_cap']:,}")
            if fund_data.get("pe_ratio"):
                section_parts.append(f"  P/E Ratio: {fund_data['pe_ratio']:.2f}")
            if fund_data.get("eps"):
                section_parts.append(f"  EPS: ${fund_data['eps']:.2f}")
            
            if fund_data.get("revenue"):
                section_parts.append(f"  Revenue: ${fund_data['revenue']:,}")
                if fund_data.get("revenue_qoq_change"):
                    section_parts.append(f"    QoQ Change: {fund_data['revenue_qoq_change']:+.2f}%")
                if fund_data.get("revenue_yoy_change"):
                    section_parts.append(f"    YoY Change: {fund_data['revenue_yoy_change']:+.2f}%")
            
            if fund_data.get("net_income"):
                section_parts.append(f"  Net Income: ${fund_data['net_income']:,}")
            
            section_parts.append("")  # Blank line between reports
        
        return "\n".join(section_parts)
    
    def _build_news_section(self, ticker: str, data: List[Dict[str, Any]]) -> str:
        """Build news and sentiment section"""
        section_parts = ["\n=== NEWS AND SENTIMENT ==="]
        
        # Collect all news articles
        all_news = []
        for day_data in data:
            if day_data.get("news"):
                for article in day_data["news"]:
                    all_news.append(article)
        
        if not all_news:
            section_parts.append("No news articles available in this period.")
            return "\n".join(section_parts)
        
        section_parts.append(f"News coverage for {ticker} ({len(all_news)} articles):\n")
        
        # Group news by recency buckets
        recent_news = []  # Last 3 days
        medium_news = []  # 4-10 days
        older_news = []   # 11-30 days
        
        latest_date = data[-1]["date"]
        
        for article in all_news:
            pub_date = article["published_at"]
            if isinstance(pub_date, str):
                pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).date()
            elif isinstance(pub_date, datetime):
                pub_date = pub_date.date()

            days_ago = (latest_date - pub_date).days
            
            if days_ago <= 3:
                recent_news.append(article)
            elif days_ago <= 10:
                medium_news.append(article)
            elif days_ago <= 30:
                older_news.append(article)
        
        # Display news by bucket
        if recent_news:
            section_parts.append("Recent News (0-3 days):")
            for article in recent_news[:10]:  # Limit to 10 most recent
                section_parts.append(self._format_news_item(article))
        
        if medium_news:
            section_parts.append("\nMedium-term News (4-10 days):")
            for article in medium_news[:8]:  # Limit to 8
                section_parts.append(self._format_news_item(article))
        
        if older_news:
            section_parts.append("\nOlder News (11-30 days):")
            for article in older_news[:5]:  # Limit to 5
                section_parts.append(self._format_news_item(article))
        
        # Sentiment summary
        sentiment_scores = [a.get("sentiment_score", 0) for a in all_news if a.get("sentiment_score") is not None]
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            section_parts.append(f"\nOverall Sentiment: {avg_sentiment:.3f} ({self._interpret_sentiment(avg_sentiment)})")
        
        return "\n".join(section_parts)
    
    def _format_news_item(self, article: Dict[str, Any]) -> str:
        """Format a single news item"""
        pub_date = article["published_at"]
        if isinstance(pub_date, datetime):
            pub_date = pub_date.strftime("%Y-%m-%d")
        elif isinstance(pub_date, date):
            pub_date = pub_date.strftime("%Y-%m-%d")
        
        formatted = f"  [{pub_date}] {article['headline']}"
        
        if article.get("sentiment_score") is not None:
            formatted += f" (Sentiment: {article['sentiment_score']:.2f})"
        
        if article.get("summary"):
            # Truncate summary to 100 characters
            summary = article["summary"][:100] + "..." if len(article["summary"]) > 100 else article["summary"]
            formatted += f"\n    {summary}"
        
        return formatted
    
    def _interpret_sentiment(self, score: float) -> str:
        """Interpret sentiment score"""
        if score >= 0.6:
            return "Very Positive"
        elif score >= 0.2:
            return "Positive"
        elif score >= -0.2:
            return "Neutral"
        elif score >= -0.6:
            return "Negative"
        else:
            return "Very Negative"
    
    def _build_macro_section(self, data: List[Dict[str, Any]]) -> str:
        """Build macroeconomic section"""
        section_parts = ["\n=== MACROECONOMIC DATA ==="]
        
        # Collect all macro updates
        macro_updates = []
        for day_data in data:
            if day_data.get("macro_features"):
                macro_updates.append((day_data["date"], day_data["macro_features"]))
        
        if not macro_updates:
            section_parts.append("No macroeconomic data available in this period.")
            return "\n".join(section_parts)
        
        section_parts.append("Key economic indicators:\n")
        
        # Show latest values for each indicator
        latest_values = {}
        for update_date, macro_data in macro_updates:
            for key, value in macro_data.items():
                if key != "date" and value is not None:
                    latest_values[key] = (update_date, value)
        
        # Format macro indicators
        indicator_names = {
            "yield_curve_spread": "Yield Curve Spread (10Y-2Y)",
            "cpi_monthly_change": "CPI Monthly Change",
            "gdp_quarterly_change": "GDP Quarterly Change",
            "unemployment_rate_change": "Unemployment Rate Change",
            "cpi_annualized_change": "CPI Annualized Change",
            "pce_monthly_change": "PCE Monthly Change",
        }
        
        for indicator, (update_date, value) in sorted(latest_values.items()):
            display_name = indicator_names.get(indicator, indicator)
            section_parts.append(f"  {display_name}: {value:+.2f}% (as of {update_date})")
        
        return "\n".join(section_parts)
    
    def _build_insider_section(self, ticker: str, data: List[Dict[str, Any]]) -> str:
        """Build insider transactions section if available"""
        # Collect all insider transactions
        all_transactions = []
        for day_data in data:
            if day_data.get("insider_transactions"):
                all_transactions.extend(day_data["insider_transactions"])
        
        if not all_transactions:
            return ""  # Don't include section if no data
        
        section_parts = ["\n=== INSIDER TRANSACTIONS ==="]
        section_parts.append(f"Insider trading activity for {ticker}:\n")
        
        # Summarize by transaction type
        buys = [t for t in all_transactions if t.get("transaction_code") in ["P", "A"]]
        sells = [t for t in all_transactions if t.get("transaction_code") in ["S", "D"]]
        
        if buys:
            total_buy_amount = sum(t.get("transaction_amount", 0) for t in buys)
            section_parts.append(f"  Insider Buys: {len(buys)} transactions, Total: ${total_buy_amount:,}")
        
        if sells:
            total_sell_amount = sum(t.get("transaction_amount", 0) for t in sells)
            section_parts.append(f"  Insider Sells: {len(sells)} transactions, Total: ${total_sell_amount:,}")
        
        # Show recent transactions
        section_parts.append("\nRecent Transactions:")
        for trans in sorted(all_transactions, key=lambda x: x.get("transaction_date", ""), reverse=True)[:5]:
            trans_type = "Buy" if trans.get("transaction_code") in ["P", "A"] else "Sell"
            section_parts.append(
                f"  [{trans['transaction_date']}] {trans['owner_name']} - {trans_type} "
                f"${trans.get('transaction_amount', 0):,} @ ${trans.get('transaction_price', 0):.2f}"
            )
        
        return "\n".join(section_parts)
    
    def _build_instructions(self) -> str:
        """Build analysis instructions"""
        return """
=== ANALYSIS INSTRUCTIONS ===

Based on ALL the data provided above, generate a comprehensive investment thesis that:

1. Synthesizes technical indicators, price movements, and trading patterns
2. Evaluates the company's fundamental health and growth trajectory
3. Incorporates sentiment from news coverage and market perception
4. Considers the macroeconomic environment and its impact
5. Weighs any insider trading activity (if available)

Your analysis should demonstrate deep understanding of how these different data sources interact and influence the investment outlook. Identify key trends, inflection points, and correlations across the data.

Generate your thesis in the following XML format:

<reasoning>
Provide a comprehensive analysis that references specific data points from the technical, fundamental, news, and macro sections above. Explain how these factors combine to support your investment recommendation.
</reasoning>

<action>
Choose exactly ONE: strong_buy | buy | hold | sell | strong_sell
</action>

<support>
List 3-5 specific data points from the analysis that most strongly support your recommendation. Reference actual numbers, dates, and trends from the data provided.
</support>"""
    
    def build_cumulative_prompt_messages(self, 
                                       ticker: str, 
                                       data_up_to_date: List[Dict[str, Any]],
                                       response_format: str = "json") -> tuple[str, str]:
        """
        Build cumulative prompt messages for RLVR training datasets
        
        Args:
            ticker: Stock ticker symbol
            data_up_to_date: List of daily data dictionaries in chronological order
            response_format: Response format ("json" or "xml")
            
        Returns:
            Tuple of (system_prompt, user_prompt) for RLVR training
        """
        if not data_up_to_date:
            raise ValueError("No data provided for prompt building")
        
        # Deduplicate the data
        deduped_data = self.deduplicator.deduplicate_cumulative_data(ticker, data_up_to_date)
        
        # Build system prompt (instructions)
        system_prompt = self._build_rlvr_system_prompt(response_format)
        
        # Build user prompt (data + analysis request)
        user_prompt_parts = []
        
        # Header
        user_prompt_parts.append(f"=== COMPREHENSIVE INVESTMENT ANALYSIS FOR {ticker} ===")
        user_prompt_parts.append(f"\\nDate: {data_up_to_date[-1]['date']}")
        user_prompt_parts.append(f"\\nPlease analyze {ticker} stock and provide your investment recommendation with detailed reasoning.")
        
        # Data sections
        user_prompt_parts.append(self._build_technical_section(ticker, deduped_data))
        user_prompt_parts.append(self._build_fundamentals_section(ticker, deduped_data))
        user_prompt_parts.append(self._build_news_section(ticker, deduped_data))
        user_prompt_parts.append(self._build_macro_section(deduped_data))
        
        # Insider transactions (if available)
        insider_section = self._build_insider_section(ticker, deduped_data)
        if insider_section:
            user_prompt_parts.append(insider_section)
        
        # Analysis request
        user_prompt_parts.append("\\nConsider:")
        user_prompt_parts.append("- Technical indicators and price trends")
        user_prompt_parts.append("- Company fundamentals and financial health")
        user_prompt_parts.append("- Market conditions and economic factors")
        user_prompt_parts.append("- Risk assessment and potential returns")
        user_prompt_parts.append("\\nProvide your recommendation as JSON with reasoning, action, and supporting evidence.")
        
        user_prompt = "\\n".join(user_prompt_parts)
        
        return system_prompt, user_prompt
    
    def _build_rlvr_system_prompt(self, response_format: str = "json") -> str:
        """Build system prompt for RLVR training"""
        if response_format.lower() == "json":
            return """You are a senior financial analyst with expertise in stock market analysis. Provide investment recommendations based on comprehensive analysis of market data, company fundamentals, and economic indicators.

Your response MUST be valid JSON in this exact format:
{
  "reasoning": "Comprehensive analysis with specific data points and trends...",
  "action": "buy",  // one of: strong_buy, buy, hold, sell, strong_sell
  "support": "Key supporting evidence with specific metrics and data points..."
}"""
        else:
            # XML format for backward compatibility
            return """You are a senior financial analyst with expertise in stock market analysis. Provide investment recommendations based on comprehensive analysis of market data, company fundamentals, and economic indicators.

Generate your thesis in the following XML format:

<reasoning>
Provide a comprehensive analysis that references specific data points from the technical, fundamental, news, and macro sections above. Explain how these factors combine to support your investment recommendation.
</reasoning>

<action>
Choose exactly ONE: strong_buy | buy | hold | sell | strong_sell
</action>

<support>
List 3-5 specific data points from the analysis that most strongly support your recommendation. Reference actual numbers, dates, and trends from the data provided.
</support>"""