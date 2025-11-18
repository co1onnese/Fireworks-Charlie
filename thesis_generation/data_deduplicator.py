"""
Data deduplication utilities for cumulative prompt building
"""
import hashlib
from typing import List, Dict, Any, Set, Tuple
from datetime import date
import logging

logger = logging.getLogger(__name__)

class DataDeduplicator:
    """Handles deduplication of repetitive data across cumulative prompts"""
    
    def __init__(self):
        """Initialize deduplicator with tracking sets"""
        self.seen_news_hashes: Set[str] = set()
        self.seen_macro_states: Dict[str, Tuple[date, Any]] = {}  # series_id -> (date, value)
        self.seen_fundamentals: Dict[str, date] = {}  # ticker -> last_report_date
        
    def reset(self):
        """Reset deduplication state for a new ticker"""
        self.seen_news_hashes.clear()
        self.seen_macro_states.clear()
        self.seen_fundamentals.clear()
        logger.debug("Deduplicator state reset")
    
    def deduplicate_cumulative_data(self, 
                                  ticker: str,
                                  all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate data while preserving chronological order
        
        Args:
            ticker: Stock ticker for context
            all_data: List of daily data dictionaries
            
        Returns:
            Deduplicated data list
        """
        deduplicated_data = []
        
        for day_data in all_data:
            # CRITICAL: Ensure day_data is a dict before accessing it
            if not isinstance(day_data, dict):
                logger.error(f"day_data is not a dict in deduplicate_cumulative_data: {type(day_data)}")
                continue
            
            deduped_day = {
                "date": day_data["date"],
                "technical": day_data.get("technical", []),  # Always include all technical data
                "fundamentals": None,
                "news": [],
                "macro_features": None,
                "insider_transactions": day_data.get("insider_transactions", []),  # Include if present
            }
            
            # Deduplicate fundamentals - only include if newer than last seen
            if day_data.get("fundamentals"):
                fund_data = day_data["fundamentals"]
                # Ensure fund_data is a dict before calling .get()
                if not isinstance(fund_data, dict):
                    logger.error(f"fund_data is not a dict in deduplicate_cumulative_data: {type(fund_data)}")
                    continue
                report_date = fund_data.get("report_date")
                
                if ticker not in self.seen_fundamentals or report_date > self.seen_fundamentals[ticker]:
                    deduped_day["fundamentals"] = fund_data
                    self.seen_fundamentals[ticker] = report_date
                    logger.debug(f"Including fundamentals for {ticker} from {report_date}")
            
            # Deduplicate news - handle new structure with recent/older articles
            if day_data.get("news"):
                news_data = day_data["news"]

                # Handle new structured format (dict with recent_articles + older_articles)
                if isinstance(news_data, dict):
                    deduped_recent = []
                    deduped_older = []

                    # Deduplicate recent articles
                    recent_articles = news_data.get("recent_articles", [])
                    if not isinstance(recent_articles, list):
                        logger.error(f"recent_articles is not a list: {type(recent_articles)}")
                        recent_articles = []
                    for article in recent_articles:
                        news_hash = self._compute_news_hash(article)
                        if news_hash not in self.seen_news_hashes:
                            deduped_recent.append(article)
                            self.seen_news_hashes.add(news_hash)

                    # Deduplicate older articles
                    older_articles = news_data.get("older_articles", [])
                    if not isinstance(older_articles, list):
                        logger.error(f"older_articles is not a list: {type(older_articles)}")
                        older_articles = []
                    for article in older_articles:
                        news_hash = self._compute_news_hash(article)
                        if news_hash not in self.seen_news_hashes:
                            deduped_older.append(article)
                            self.seen_news_hashes.add(news_hash)

                    # Store in new format
                    deduped_day["news"] = {
                        "recent_articles": deduped_recent,
                        "older_articles": deduped_older,
                        "recent_dates": news_data.get("recent_dates", [])
                    }

                    total_deduped = len(deduped_recent) + len(deduped_older)
                    if total_deduped > 0:
                        logger.debug(
                            f"Including {total_deduped} unique news items "
                            f"({len(deduped_recent)} recent, {len(deduped_older)} older) "
                            f"for {day_data['date']}"
                        )
                else:
                    # Legacy format (list of articles) - keep for backward compatibility
                    deduped_day["news"] = []
                    for article in news_data:
                        news_hash = self._compute_news_hash(article)
                        if news_hash not in self.seen_news_hashes:
                            deduped_day["news"].append(article)
                            self.seen_news_hashes.add(news_hash)

                    if deduped_day["news"]:
                        logger.debug(f"Including {len(deduped_day['news'])} unique news items for {day_data['date']}")
            
            # Deduplicate macro features - only include if values changed
            if day_data.get("macro_features"):
                macro_data = day_data["macro_features"]
                # Ensure macro_data is a dict before calling .get()
                if not isinstance(macro_data, dict):
                    logger.error(f"macro_data is not a dict in deduplicate_cumulative_data: {type(macro_data)}")
                    continue
                macro_date = macro_data.get("date")
                
                # Check each macro indicator for changes
                changed_indicators = {}
                for key, value in macro_data.items():
                    if key == "date":
                        continue
                    
                    if key not in self.seen_macro_states:
                        # First time seeing this indicator
                        changed_indicators[key] = value
                        self.seen_macro_states[key] = (macro_date, value)
                    else:
                        # Check if value changed
                        last_date, last_value = self.seen_macro_states[key]
                        if value != last_value and macro_date > last_date:
                            changed_indicators[key] = value
                            self.seen_macro_states[key] = (macro_date, value)
                
                if changed_indicators:
                    deduped_day["macro_features"] = {
                        "date": macro_date,
                        **changed_indicators
                    }
                    logger.debug(f"Including {len(changed_indicators)} changed macro indicators for {macro_date}")
            
            deduplicated_data.append(deduped_day)
        
        return deduplicated_data
    
    def _compute_news_hash(self, article: Dict[str, Any]) -> str:
        """
        Compute hash for news article to detect duplicates
        
        Args:
            article: News article dictionary
            
        Returns:
            SHA256 hash of article content
        """
        # Create a canonical representation of the article
        canonical = f"{article.get('headline', '')}|{article.get('published_at', '')}|{article.get('summary', '')}"
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def get_deduplication_stats(self) -> Dict[str, int]:
        """Get statistics about deduplication"""
        return {
            "unique_news_items": len(self.seen_news_hashes),
            "tracked_fundamentals": len(self.seen_fundamentals),
            "tracked_macro_indicators": len(self.seen_macro_states),
        }