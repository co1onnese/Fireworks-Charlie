"""
News Analysis Engine for Fireworks-Charlie
Provides comprehensive news sentiment analysis and insights
"""
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    """Advanced news analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_news(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze news data and generate insights
        
        Args:
            data: List of news data dictionaries
            
        Returns:
            Dictionary with news analysis
        """
        if not data:
            return {"error": "No news data provided"}
        
        analysis = {
            "sentiment_analysis": self._analyze_sentiment(data),
            "temporal_patterns": self._analyze_temporal_patterns(data),
            "key_themes": self._extract_key_themes(data),
            "impact_assessment": self._assess_news_impact(data),
            "coverage_analysis": self._analyze_coverage(data)
        }
        
        return analysis
    
    def generate_insights(self, data: List[Dict[str, Any]]) -> str:
        """
        Generate key news insights
        
        Args:
            data: List of news data dictionaries
            
        Returns:
            String with key news insights
        """
        if not data:
            return "No news data available"
        
        insights = []
        
        # Sentiment summary
        sentiments = [n.get('sentiment_score', 0) for n in data if n.get('sentiment_score') is not None]
        if sentiments:
            avg_sentiment = sum(sentiments) / len(sentiments)
            if avg_sentiment > 0.2:
                insights.append(f"Sentiment: Positive ({avg_sentiment:.2f})")
            elif avg_sentiment < -0.2:
                insights.append(f"Sentiment: Negative ({avg_sentiment:.2f})")
            else:
                insights.append(f"Sentiment: Neutral ({avg_sentiment:.2f})")
        
        # Volume analysis
        insights.append(f"Articles: {len(data)}")
        
        # Recent trend
        if len(data) >= 5:
            recent_sentiments = [n.get('sentiment_score', 0) for n in data[:5] if n.get('sentiment_score') is not None]
            if recent_sentiments:
                recent_avg = sum(recent_sentiments) / len(recent_sentiments)
                if recent_avg > avg_sentiment + 0.1:
                    insights.append("Trend: Improving")
                elif recent_avg < avg_sentiment - 0.1:
                    insights.append("Trend: Deteriorating")
                else:
                    insights.append("Trend: Stable")
        
        return " | ".join(insights) if insights else "Limited news data available"
    
    def _analyze_sentiment(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment patterns"""
        sentiments = [n.get('sentiment_score', 0) for n in data if n.get('sentiment_score') is not None]
        
        if not sentiments:
            return {"error": "No sentiment data available"}
        
        sentiment_analysis = {
            "average_sentiment": sum(sentiments) / len(sentiments),
            "sentiment_distribution": {
                "positive": len([s for s in sentiments if s > 0.1]),
                "negative": len([s for s in sentiments if s < -0.1]),
                "neutral": len([s for s in sentiments if -0.1 <= s <= 0.1])
            },
            "sentiment_range": {
                "min": min(sentiments),
                "max": max(sentiments)
            }
        }
        
        return sentiment_analysis
    
    def _analyze_temporal_patterns(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in news"""
        if not data:
            return {"error": "No data available"}
        
        # Group by recency
        now = datetime.now()
        recent_news = []
        older_news = []
        
        for news in data:
            pub_date = news.get('published_at')
            if isinstance(pub_date, str):
                try:
                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                except:
                    continue
            elif isinstance(pub_date, date):
                pub_date = datetime.combine(pub_date, datetime.min.time())
            
            if pub_date:
                days_ago = (now - pub_date).days
                if days_ago <= 7:
                    recent_news.append(news)
                else:
                    older_news.append(news)
        
        patterns = {
            "recent_news_count": len(recent_news),
            "older_news_count": len(older_news),
            "news_frequency": len(data) / 30 if data else 0  # Articles per day over 30 days
        }
        
        return patterns
    
    def _extract_key_themes(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key themes from news headlines"""
        headlines = [n.get('headline', '') for n in data if n.get('headline')]
        
        if not headlines:
            return {"error": "No headlines available"}
        
        # Simple keyword extraction (in a real implementation, this would be more sophisticated)
        all_words = []
        for headline in headlines:
            words = headline.lower().split()
            # Filter out common words
            filtered_words = [w for w in words if len(w) > 3 and w not in ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'will', 'said', 'more', 'than', 'were', 'what', 'when', 'where', 'which', 'while', 'would', 'could', 'should']]
            all_words.extend(filtered_words)
        
        # Count word frequency
        word_counts = Counter(all_words)
        common_words = word_counts.most_common(10)
        
        themes = {
            "common_keywords": [word for word, count in common_words],
            "keyword_frequencies": dict(common_words)
        }
        
        return themes
    
    def _assess_news_impact(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess potential impact of news on stock price"""
        if not data:
            return {"error": "No data available"}
        
        # High-impact keywords (simplified)
        high_impact_keywords = ['earnings', 'revenue', 'profit', 'loss', 'merger', 'acquisition', 'partnership', 'lawsuit', 'investigation', 'fda', 'approval', 'rejection']
        
        high_impact_articles = 0
        for news in data:
            headline = news.get('headline', '').lower()
            if any(keyword in headline for keyword in high_impact_keywords):
                high_impact_articles += 1
        
        impact_assessment = {
            "high_impact_articles": high_impact_articles,
            "impact_ratio": high_impact_articles / len(data) if data else 0,
            "overall_impact": "High" if high_impact_articles > len(data) * 0.3 else "Medium" if high_impact_articles > len(data) * 0.1 else "Low"
        }
        
        return impact_assessment
    
    def _analyze_coverage(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze news coverage patterns"""
        if not data:
            return {"error": "No data available"}
        
        # Analyze by sentiment label if available
        sentiment_labels = [n.get('sentiment_label', 'neutral') for n in data if n.get('sentiment_label')]
        label_counts = Counter(sentiment_labels)
        
        coverage_analysis = {
            "total_articles": len(data),
            "sentiment_breakdown": dict(label_counts),
            "coverage_quality": "High" if len(data) > 20 else "Medium" if len(data) > 10 else "Low"
        }
        
        return coverage_analysis