"""
Technical Analysis Engine for Fireworks-Charlie
Provides advanced technical analysis and insights generation
"""
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import date

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """Advanced technical analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_trends(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze price trends and momentum
        
        Args:
            data: List of technical data dictionaries
            
        Returns:
            Dictionary with trend analysis
        """
        if not data:
            return {"error": "No data provided"}
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate trend indicators
        trend_analysis = {
            "short_term_trend": self._analyze_short_term_trend(df),
            "medium_term_trend": self._analyze_medium_term_trend(df),
            "long_term_trend": self._analyze_long_term_trend(df),
            "momentum": self._analyze_momentum(df),
            "volatility": self._analyze_volatility(df),
            "volume_analysis": self._analyze_volume(df)
        }
        
        return trend_analysis
    
    def generate_insights(self, data: List[Dict[str, Any]]) -> str:
        """
        Generate key technical insights from data
        
        Args:
            data: List of technical data dictionaries
            
        Returns:
            String with key technical insights
        """
        if not data:
            return "No technical data available"
        
        # Handle different data structures
        if isinstance(data, list) and len(data) > 0 and 'technical' in data[0]:
            # Data is in the format from enhanced prompt builder
            technical_data = []
            for day_data in data:
                if day_data.get('technical'):
                    technical_data.extend(day_data['technical'])
            
            if not technical_data:
                return "No technical data available"
            
            df = pd.DataFrame(technical_data)
        else:
            # Data is already technical data
            df = pd.DataFrame(data)
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        insights = []
        
        # Price action insights
        latest = df.iloc[-1]
        previous = df.iloc[-2] if len(df) > 1 else latest
        
        # Price change analysis
        if 'close' in latest and 'close' in previous:
            price_change = ((latest['close'] - previous['close']) / previous['close']) * 100
            insights.append(f"Price Change: {price_change:+.2f}%")
        
        # RSI analysis
        if latest.get('rsi_14') and not pd.isna(latest['rsi_14']):
            rsi = latest['rsi_14']
            if rsi > 70:
                insights.append(f"RSI: {rsi:.1f} (Overbought)")
            elif rsi < 30:
                insights.append(f"RSI: {rsi:.1f} (Oversold)")
            else:
                insights.append(f"RSI: {rsi:.1f} (Neutral)")
        
        # MACD analysis
        if latest.get('macd') and latest.get('macd_signal') and not pd.isna(latest['macd']):
            macd = latest['macd']
            signal = latest['macd_signal']
            if macd > signal:
                insights.append("MACD: Bullish (MACD > Signal)")
            else:
                insights.append("MACD: Bearish (MACD < Signal)")
        
        # Bollinger Bands analysis
        if all(key in latest for key in ['bollinger_upper', 'bollinger_lower', 'close']):
            close = latest['close']
            upper = latest['bollinger_upper']
            lower = latest['bollinger_lower']

            # ✅ Check ALL values for None/NaN before comparison
            if (close is not None and upper is not None and lower is not None and
                not pd.isna(close) and not pd.isna(upper) and not pd.isna(lower)):
                if close > upper:
                    insights.append("Price: Above Bollinger Upper Band (Overbought)")
                elif close < lower:
                    insights.append("Price: Below Bollinger Lower Band (Oversold)")
                else:
                    insights.append("Price: Within Bollinger Bands (Normal)")
        
        # Moving averages analysis
        if latest.get('sma_20') and latest.get('sma_50') and not pd.isna(latest['sma_20']):
            sma_20 = latest['sma_20']
            sma_50 = latest['sma_50']
            close = latest['close']

            # ✅ Check ALL values for None/NaN before chained comparison
            if (close is not None and sma_20 is not None and sma_50 is not None and
                not pd.isna(close) and not pd.isna(sma_20) and not pd.isna(sma_50)):
                if close > sma_20 > sma_50:
                    insights.append("Moving Averages: Bullish Alignment")
                elif close < sma_20 < sma_50:
                    insights.append("Moving Averages: Bearish Alignment")
                else:
                    insights.append("Moving Averages: Mixed Signals")
        
        return " | ".join(insights)
    
    def _analyze_short_term_trend(self, df: pd.DataFrame) -> str:
        """Analyze short-term trend (last 5-10 days)"""
        if len(df) < 5:
            return "Insufficient data"
        
        recent = df.tail(5)
        closes = recent['close'].values
        
        # Simple trend detection
        if closes[-1] > closes[0]:
            return "Uptrend"
        elif closes[-1] < closes[0]:
            return "Downtrend"
        else:
            return "Sideways"
    
    def _analyze_medium_term_trend(self, df: pd.DataFrame) -> str:
        """Analyze medium-term trend (last 20 days)"""
        if len(df) < 10:
            return "Insufficient data"
        
        recent = df.tail(min(20, len(df)))
        closes = recent['close'].values
        
        # Linear regression slope
        x = range(len(closes))
        slope = np.polyfit(x, closes, 1)[0]
        
        if slope > 0.1:
            return "Strong Uptrend"
        elif slope > 0:
            return "Weak Uptrend"
        elif slope < -0.1:
            return "Strong Downtrend"
        elif slope < 0:
            return "Weak Downtrend"
        else:
            return "Sideways"
    
    def _analyze_long_term_trend(self, df: pd.DataFrame) -> str:
        """Analyze long-term trend (last 50+ days)"""
        if len(df) < 20:
            return "Insufficient data"
        
        recent = df.tail(min(50, len(df)))
        closes = recent['close'].values
        
        # Compare first and last values
        first_close = closes[0]
        last_close = closes[-1]
        change = ((last_close - first_close) / first_close) * 100
        
        if change > 10:
            return f"Strong Uptrend ({change:+.1f}%)"
        elif change > 5:
            return f"Moderate Uptrend ({change:+.1f}%)"
        elif change < -10:
            return f"Strong Downtrend ({change:+.1f}%)"
        elif change < -5:
            return f"Moderate Downtrend ({change:+.1f}%)"
        else:
            return f"Sideways ({change:+.1f}%)"
    
    def _analyze_momentum(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze momentum indicators"""
        momentum = {}
        
        if 'rsi_14' in df.columns:
            latest_rsi = df['rsi_14'].iloc[-1]
            if not pd.isna(latest_rsi):
                if latest_rsi > 70:
                    momentum['rsi'] = "Overbought"
                elif latest_rsi < 30:
                    momentum['rsi'] = "Oversold"
                else:
                    momentum['rsi'] = "Neutral"
        
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            latest_macd = df['macd'].iloc[-1]
            latest_signal = df['macd_signal'].iloc[-1]
            if not pd.isna(latest_macd) and not pd.isna(latest_signal):
                if latest_macd > latest_signal:
                    momentum['macd'] = "Bullish"
                else:
                    momentum['macd'] = "Bearish"
        
        return momentum
    
    def _analyze_volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price volatility"""
        if len(df) < 5:
            return {"error": "Insufficient data"}
        
        recent = df.tail(20)
        returns = recent['close'].pct_change().dropna()
        
        volatility = {
            "daily_volatility": returns.std() * 100,
            "recent_range": ((recent['high'].max() - recent['low'].min()) / recent['close'].mean()) * 100
        }
        
        return volatility
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume patterns"""
        if len(df) < 5:
            return {"error": "Insufficient data"}
        
        recent = df.tail(10)
        avg_volume = recent['volume'].mean()
        latest_volume = recent['volume'].iloc[-1]
        
        volume_analysis = {
            "volume_ratio": latest_volume / avg_volume if avg_volume > 0 else 0,
            "volume_trend": "Increasing" if latest_volume > avg_volume else "Decreasing"
        }
        
        return volume_analysis

# Import numpy for trend analysis
import numpy as np