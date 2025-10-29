"""
Checkpoint management for pipeline state persistence
"""
import json
import pickle
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class CheckpointManager:
    """Manages checkpoints for pipeline state recovery"""
    
    def __init__(self, checkpoint_dir: str):
        """
        Initialize checkpoint manager
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"CheckpointManager initialized with dir: {self.checkpoint_dir}")
    
    def save_checkpoint(self, 
                       ticker: str, 
                       processed_date: date,
                       cumulative_data: List[Dict[str, Any]],
                       metadata: Dict[str, Any] = None) -> bool:
        """
        Save checkpoint for a ticker after processing a date
        
        Args:
            ticker: Stock ticker symbol
            processed_date: Last successfully processed date
            cumulative_data: All data collected up to this date
            metadata: Additional metadata to save
            
        Returns:
            True if successful
        """
        checkpoint_file = self._get_checkpoint_path(ticker)
        
        checkpoint_data = {
            "ticker": ticker,
            "last_processed_date": processed_date.isoformat(),
            "cumulative_data_count": len(cumulative_data),
            "metadata": metadata or {},
            "saved_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        try:
            # Save checkpoint metadata as JSON
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            # Save cumulative data as pickle (more efficient for large data)
            data_file = self._get_data_path(ticker)
            with open(data_file, 'wb') as f:
                pickle.dump(cumulative_data, f)
            
            logger.debug(f"Saved checkpoint for {ticker} at {processed_date}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {ticker}: {e}")
            return False
    
    def load_checkpoint(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Checkpoint data including cumulative_data, or None if not found
        """
        checkpoint_file = self._get_checkpoint_path(ticker)
        data_file = self._get_data_path(ticker)
        
        if not checkpoint_file.exists() or not data_file.exists():
            logger.debug(f"No checkpoint found for {ticker}")
            return None
        
        try:
            # Load checkpoint metadata
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            # Load cumulative data
            with open(data_file, 'rb') as f:
                cumulative_data = pickle.load(f)
            
            checkpoint_data["cumulative_data"] = cumulative_data
            
            logger.info(
                f"Loaded checkpoint for {ticker}: "
                f"last_date={checkpoint_data['last_processed_date']}, "
                f"data_count={len(cumulative_data)}"
            )
            
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint for {ticker}: {e}")
            return None
    
    def get_last_processed_date(self, ticker: str) -> Optional[date]:
        """
        Get the last successfully processed date for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Last processed date or None
        """
        checkpoint = self.load_checkpoint(ticker)
        if checkpoint:
            try:
                return date.fromisoformat(checkpoint["last_processed_date"])
            except Exception as e:
                logger.error(f"Error parsing last processed date: {e}")
        return None
    
    def delete_checkpoint(self, ticker: str) -> bool:
        """
        Delete checkpoint for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if successful
        """
        try:
            checkpoint_file = self._get_checkpoint_path(ticker)
            data_file = self._get_data_path(ticker)
            
            if checkpoint_file.exists():
                checkpoint_file.unlink()
            if data_file.exists():
                data_file.unlink()
            
            logger.info(f"Deleted checkpoint for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete checkpoint for {ticker}: {e}")
            return False
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints
        
        Returns:
            List of checkpoint summaries
        """
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("*_checkpoint.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                
                checkpoints.append({
                    "ticker": data["ticker"],
                    "last_processed_date": data["last_processed_date"],
                    "saved_at": data["saved_at"],
                    "data_count": data["cumulative_data_count"]
                })
            except Exception as e:
                logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")
        
        return sorted(checkpoints, key=lambda x: x["ticker"])
    
    def clean_old_checkpoints(self, days_to_keep: int = 7) -> int:
        """
        Clean checkpoints older than specified days
        
        Args:
            days_to_keep: Number of days to keep checkpoints
            
        Returns:
            Number of checkpoints deleted
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for checkpoint_file in self.checkpoint_dir.glob("*_checkpoint.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                
                saved_at = datetime.fromisoformat(data["saved_at"])
                if saved_at < cutoff_date:
                    ticker = data["ticker"]
                    if self.delete_checkpoint(ticker):
                        deleted_count += 1
                        
            except Exception as e:
                logger.warning(f"Error processing checkpoint {checkpoint_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned {deleted_count} old checkpoints")
        
        return deleted_count
    
    def _get_checkpoint_path(self, ticker: str) -> Path:
        """Get path for checkpoint metadata file"""
        return self.checkpoint_dir / f"{ticker}_checkpoint.json"
    
    def _get_data_path(self, ticker: str) -> Path:
        """Get path for checkpoint data file"""
        return self.checkpoint_dir / f"{ticker}_data.pkl"