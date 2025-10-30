"""
Context Compression Module for Fireworks-Charlie
Implements intelligent sliding window and aggressive summarization
to fit within model context limits
"""
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from statistics import mean, median, stdev
import logging

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Compresses cumulative data to fit within token budgets"""

    def __init__(self,
                 max_days_recent: int = 7,
                 max_days_medium: int = 30,
                 max_days_historical: int = 90):
        """
        Initialize context compressor

        Args:
            max_days_recent: Days to keep in full detail (default: 7)
            max_days_medium: Days to keep in summarized form (default: 30)
            max_days_historical: Days to keep key insights (default: 90)
        """
        self.max_days_recent = max_days_recent
        self.max_days_medium = max_days_medium
        self.max_days_historical = max_days_historical
        self.logger = logging.getLogger(__name__)

    def compress_cumulative_data(self,
                                 ticker: str,
                                 cumulative_data: List[Dict[str, Any]],
                                 current_date: date) -> List[Dict[str, Any]]:
        """
        Compress cumulative data using sliding window approach

        Strategy:
        1. Recent data (0-7 days): Keep full detail
        2. Medium data (8-30 days): Summarize daily to weekly aggregates
        3. Historical data (31-90 days): Extract only key insights
        4. Very old data (90+ days): Discard completely

        Args:
            ticker: Stock ticker
            cumulative_data: List of daily data dictionaries
            current_date: Current analysis date

        Returns:
            Compressed data list
        """
        if not cumulative_data:
            return []

        # Separate data by age
        recent_data = []
        medium_data = []
        historical_data = []

        for day_data in cumulative_data:
            day_date = day_data.get('date')
            if not day_date:
                continue

            days_ago = (current_date - day_date).days

            if days_ago <= self.max_days_recent:
                # Keep full detail for recent data
                recent_data.append(day_data)
            elif days_ago <= self.max_days_medium:
                # Will be summarized
                medium_data.append(day_data)
            elif days_ago <= self.max_days_historical:
                # Will be compressed to key insights
                historical_data.append(day_data)
            # Else: discard (too old)

        compressed = []

        # 1. Keep recent data as-is
        compressed.extend(recent_data)

        # 2. Summarize medium data into weekly aggregates
        if medium_data:
            weekly_summaries = self._summarize_to_weekly(ticker, medium_data)
            compressed.extend(weekly_summaries)

        # 3. Extract only key insights from historical data
        if historical_data:
            key_insights = self._extract_key_insights(ticker, historical_data)
            if key_insights:
                compressed.append(key_insights)

        self.logger.info(
            f"{ticker}: Compressed {len(cumulative_data)} days to {len(compressed)} items "
            f"(Recent: {len(recent_data)}, Medium: {len(medium_data)}→{len(medium_data)//7 if medium_data else 0} weeks, "
            f"Historical: {len(historical_data)}→1 summary)"
        )

        return compressed

    def _summarize_to_weekly(self, ticker: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Summarize daily data into weekly aggregates

        Aggregates:
        - Price: Open (first), Close (last), High (max), Low (min)
        - Volume: Average
        - News: Count by sentiment, top headline
        - Fundamentals: Latest only
        - Indicators: End-of-week values
        """
        # Group by week
        weeks: Dict[date, List[Dict[str, Any]]] = {}

        for day_data in sorted(data, key=lambda x: x['date']):
            # Get Monday of the week
            week_start = day_data['date'] - timedelta(days=day_data['date'].weekday())

            if week_start not in weeks:
                weeks[week_start] = []
            weeks[week_start].append(day_data)

        # Create weekly summaries
        weekly_summaries = []

        for week_start in sorted(weeks.keys()):
            week_data = weeks[week_start]
            summary = self._create_weekly_summary(ticker, week_start, week_data)
            weekly_summaries.append(summary)

        return weekly_summaries

    def _create_weekly_summary(self,
                               ticker: str,
                               week_start: date,
                               week_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a single week summary"""
        summary = {
            'date': week_start,
            'type': 'weekly_summary',
            'days_in_week': len(week_data),
            'date_range': f"{week_data[0]['date']} to {week_data[-1]['date']}"
        }

        # Aggregate technical data
        technical_summary = self._aggregate_technical_weekly(week_data)
        if technical_summary:
            summary['technical'] = [technical_summary]

        # Aggregate news data
        news_summary = self._aggregate_news_weekly(week_data)
        if news_summary:
            summary['news'] = [news_summary]

        # Keep latest fundamentals
        for day in reversed(week_data):
            if day.get('fundamentals'):
                summary['fundamentals'] = day['fundamentals']
                break

        # Aggregate insider transactions
        all_insider = []
        for day in week_data:
            if day.get('insider_transactions'):
                all_insider.extend(day['insider_transactions'])

        if all_insider:
            summary['insider_transactions'] = self._summarize_insider_weekly(all_insider)

        # Keep latest macro features
        for day in reversed(week_data):
            if day.get('macro_features'):
                summary['macro_features'] = day['macro_features']
                break

        return summary

    def _aggregate_technical_weekly(self, week_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Aggregate technical indicators for a week"""
        all_technical = []
        for day in week_data:
            if day.get('technical'):
                all_technical.extend(day['technical'])

        if not all_technical:
            return None

        # Extract OHLC
        opens = [t['open'] for t in all_technical if 'open' in t]
        highs = [t['high'] for t in all_technical if 'high' in t]
        lows = [t['low'] for t in all_technical if 'low' in t]
        closes = [t['close'] for t in all_technical if 'close' in t]
        volumes = [t['volume'] for t in all_technical if 'volume' in t]

        if not closes:
            return None

        summary = {
            'date': week_data[-1]['date'],  # End of week
            'open': opens[0] if opens else None,
            'high': max(highs) if highs else None,
            'low': min(lows) if lows else None,
            'close': closes[-1] if closes else None,
            'volume': int(mean(volumes)) if volumes else None,
            'week_change_pct': ((closes[-1] - opens[0]) / opens[0] * 100) if opens and closes else 0,
        }

        # End-of-week indicators
        last_tech = all_technical[-1]
        for key in ['sma_20', 'sma_50', 'ema_20', 'rsi_14', 'macd', 'macd_signal',
                    'bollinger_upper', 'bollinger_middle', 'bollinger_lower']:
            if key in last_tech:
                summary[key] = last_tech[key]

        return summary

    def _aggregate_news_weekly(self, week_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Aggregate news for a week"""
        all_news = []
        for day in week_data:
            if day.get('news'):
                all_news.extend(day['news'])

        if not all_news:
            return None

        # Count by sentiment
        positive = sum(1 for n in all_news if n.get('sentiment_score', 0) > 0.1)
        negative = sum(1 for n in all_news if n.get('sentiment_score', 0) < -0.1)
        neutral = len(all_news) - positive - negative

        # Calculate average sentiment
        sentiments = [n.get('sentiment_score', 0) for n in all_news]
        avg_sentiment = mean(sentiments) if sentiments else 0

        # Find most significant headline (highest absolute sentiment)
        top_headline = max(all_news, key=lambda n: abs(n.get('sentiment_score', 0))) if all_news else None

        summary = {
            'total_articles': len(all_news),
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'avg_sentiment': avg_sentiment,
            'sentiment_label': 'positive' if avg_sentiment > 0.1 else 'negative' if avg_sentiment < -0.1 else 'neutral',
        }

        if top_headline:
            summary['top_headline'] = top_headline.get('headline', '')
            summary['top_sentiment'] = top_headline.get('sentiment_score', 0)

        return summary

    def _summarize_insider_weekly(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Summarize insider transactions for a week"""
        # Keep only significant transactions
        buys = [t for t in transactions if t.get('transaction_code') == 'P']
        sells = [t for t in transactions if t.get('transaction_code') == 'S']

        summary_items = []

        if buys:
            total_shares = sum(t.get('shares', 0) for t in buys)
            avg_price = mean(t.get('price', 0) for t in buys if t.get('price'))
            summary_items.append({
                'type': 'BUY_SUMMARY',
                'transaction_count': len(buys),
                'total_shares': total_shares,
                'avg_price': avg_price
            })

        if sells:
            total_shares = sum(t.get('shares', 0) for t in sells)
            avg_price = mean(t.get('price', 0) for t in sells if t.get('price'))
            summary_items.append({
                'type': 'SELL_SUMMARY',
                'transaction_count': len(sells),
                'total_shares': total_shares,
                'avg_price': avg_price
            })

        return summary_items[:5]  # Max 5 summary items

    def _extract_key_insights(self, ticker: str, historical_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Extract only key insights from historical data

        Key insights:
        - Price range (support/resistance levels)
        - Volatility metrics
        - Major trend direction
        - Significant news events (if any)
        """
        if not historical_data:
            return None

        # Collect all technical data
        all_prices = []
        all_returns = []

        for day_data in sorted(historical_data, key=lambda x: x['date']):
            if day_data.get('technical'):
                for tech in day_data['technical']:
                    if 'close' in tech:
                        all_prices.append(tech['close'])

        if len(all_prices) < 2:
            return None

        # Calculate returns
        for i in range(1, len(all_prices)):
            ret = (all_prices[i] - all_prices[i-1]) / all_prices[i-1] * 100
            all_returns.append(ret)

        # Calculate key metrics
        price_range_low = min(all_prices)
        price_range_high = max(all_prices)
        price_range_pct = (price_range_high - price_range_low) / price_range_low * 100

        avg_return = mean(all_returns) if all_returns else 0
        volatility = stdev(all_returns) if len(all_returns) > 1 else 0

        total_return = (all_prices[-1] - all_prices[0]) / all_prices[0] * 100

        insights = {
            'date': historical_data[-1]['date'],
            'type': 'historical_insights',
            'date_range': f"{historical_data[0]['date']} to {historical_data[-1]['date']}",
            'days_covered': len(historical_data),
            'price_range_low': price_range_low,
            'price_range_high': price_range_high,
            'price_range_pct': price_range_pct,
            'total_return_pct': total_return,
            'avg_daily_return_pct': avg_return,
            'daily_volatility_pct': volatility,
            'trend': 'upward' if total_return > 5 else 'downward' if total_return < -5 else 'sideways'
        }

        return insights

    def estimate_compressed_size(self, compressed_data: List[Dict[str, Any]]) -> int:
        """
        Estimate token count for compressed data

        Uses simple heuristic: len(str(data)) / 4
        (More accurate would be tiktoken, but this is fast)
        """
        total_chars = 0
        for item in compressed_data:
            total_chars += len(str(item))

        return total_chars // 4
