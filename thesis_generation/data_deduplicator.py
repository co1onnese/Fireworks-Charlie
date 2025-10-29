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
                report_date = fund_data.get("report_date")
                
                if ticker not in self.seen_fundamentals or report_date > self.seen_fundamentals[ticker]:
                    deduped_day["fundamentals"] = fund_data
                    self.seen_fundamentals[ticker] = report_date
                    logger.debug(f"Including fundamentals for {ticker} from {report_date}")
            
            # Deduplicate news - check content hash
            if day_data.get("news"):
                for article in day_data["news"]:
                    news_hash = self._compute_news_hash(article)
                    if news_hash not in self.seen_news_hashes:
                        deduped_day["news"].append(article)
                        self.seen_news_hashes.add(news_hash)
                
                if deduped_day["news"]:
                    logger.debug(f"Including {len(deduped_day['news'])} unique news items for {day_data['date']}")
            
            # Deduplicate macro features - only include if values changed
            if day_data.get("macro_features"):
                macro_data = day_data["macro_features"]
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