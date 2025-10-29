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


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles date and datetime objects"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

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
                json.dump(checkpoint_data, f, indent=2, cls=DateTimeEncoder)
            
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
    
    def save_rlvr_checkpoint(self, 
                            ticker: str, 
                            processed_date: date,
                            cumulative_data: List[Dict[str, Any]],
                            prompts: List[Dict[str, Any]] = None,
                            metadata: Dict[str, Any] = None) -> bool:
        """
        Save RLVR checkpoint with prompt storage
        
        Args:
            ticker: Stock ticker symbol
            processed_date: Last successfully processed date
            cumulative_data: All data collected up to this date
            prompts: List of prompt data for RLVR training
            metadata: Additional metadata to save
            
        Returns:
            True if successful
        """
        checkpoint_file = self._get_checkpoint_path(ticker)
        
        checkpoint_data = {
            "ticker": ticker,
            "last_processed_date": processed_date.isoformat(),
            "cumulative_data_count": len(cumulative_data),
            "prompts": prompts or [],
            "prompt_count": len(prompts) if prompts else 0,
            "metadata": metadata or {},
            "saved_at": datetime.utcnow().isoformat(),
            "version": "2.0",  # RLVR version
            "mode": "rlvr"
        }
        
        try:
            # Save checkpoint metadata as JSON
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, cls=DateTimeEncoder)

            # Save cumulative data as pickle (more efficient for large data)
            data_file = self._get_data_path(ticker)
            with open(data_file, 'wb') as f:
                pickle.dump(cumulative_data, f)

            # Save prompts as JSON (for RLVR training)
            if prompts:
                prompts_file = self._get_prompts_path(ticker)
                with open(prompts_file, 'w') as f:
                    json.dump(prompts, f, indent=2, cls=DateTimeEncoder)
            
            logger.debug(f"Saved RLVR checkpoint for {ticker} at {processed_date}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save RLVR checkpoint for {ticker}: {e}")
            return False
    
    def load_rlvr_checkpoint(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Load RLVR checkpoint with prompt data
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Checkpoint data with prompts or None if not found
        """
        checkpoint_file = self._get_checkpoint_path(ticker)
        
        if not checkpoint_file.exists():
            return None
        
        try:
            # Load checkpoint metadata
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            # Check if it's an RLVR checkpoint
            if checkpoint_data.get("mode") != "rlvr":
                logger.warning(f"Checkpoint for {ticker} is not RLVR format")
                return None
            
            # Load cumulative data
            data_file = self._get_data_path(ticker)
            if data_file.exists():
                with open(data_file, 'rb') as f:
                    cumulative_data = pickle.load(f)
                checkpoint_data["cumulative_data"] = cumulative_data
            
            # Load prompts if available
            prompts_file = self._get_prompts_path(ticker)
            if prompts_file.exists():
                with open(prompts_file, 'r') as f:
                    prompts = json.load(f)
                checkpoint_data["prompts"] = prompts
            
            logger.debug(f"Loaded RLVR checkpoint for {ticker}")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"Failed to load RLVR checkpoint for {ticker}: {e}")
            return None
    
    def add_prompt_to_checkpoint(self,
                                ticker: str,
                                date: str,
                                system_prompt: str,
                                user_prompt: str,
                                assistant_response: Dict[str, Any] = None) -> bool:
        """
        Add a prompt to existing RLVR checkpoint

        Args:
            ticker: Stock ticker symbol
            date: Date of the prompt
            system_prompt: System prompt text
            user_prompt: User prompt text
            assistant_response: Assistant response (if available)

        Returns:
            True if successful
        """
        checkpoint_data = self.load_rlvr_checkpoint(ticker)
        if not checkpoint_data:
            logger.error(f"No RLVR checkpoint found for {ticker}")
            return False

        # Add new prompt
        prompt_data = {
            "date": date,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "assistant_response": assistant_response,
            "created_at": datetime.utcnow().isoformat()
        }

        if "prompts" not in checkpoint_data:
            checkpoint_data["prompts"] = []

        checkpoint_data["prompts"].append(prompt_data)
        checkpoint_data["prompt_count"] = len(checkpoint_data["prompts"])

        # Create JSON-serializable version (exclude cumulative_data which has date objects)
        checkpoint_json = {
            "ticker": checkpoint_data["ticker"],
            "last_processed_date": checkpoint_data["last_processed_date"],
            "cumulative_data_count": checkpoint_data.get("cumulative_data_count", 0),
            "prompts": checkpoint_data["prompts"],
            "prompt_count": checkpoint_data["prompt_count"],
            "metadata": checkpoint_data.get("metadata", {}),
            "saved_at": datetime.utcnow().isoformat(),
            "version": checkpoint_data.get("version", "2.0"),
            "mode": checkpoint_data.get("mode", "rlvr")
        }

        # Save updated checkpoint metadata (without cumulative_data)
        checkpoint_file = self._get_checkpoint_path(ticker)
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_json, f, indent=2, cls=DateTimeEncoder)

        # Save updated prompts separately
        prompts_file = self._get_prompts_path(ticker)
        with open(prompts_file, 'w') as f:
            json.dump(checkpoint_data["prompts"], f, indent=2, cls=DateTimeEncoder)

        logger.debug(f"Added prompt for {ticker} on {date}")
        return True
    
    def get_prompts_for_date_range(self, 
                                  ticker: str, 
                                  start_date: str, 
                                  end_date: str) -> List[Dict[str, Any]]:
        """
        Get prompts for a specific date range
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of prompt data for the date range
        """
        checkpoint_data = self.load_rlvr_checkpoint(ticker)
        if not checkpoint_data or "prompts" not in checkpoint_data:
            return []
        
        prompts = checkpoint_data["prompts"]
        filtered_prompts = []
        
        for prompt in prompts:
            prompt_date = prompt.get("date", "")
            if start_date <= prompt_date <= end_date:
                filtered_prompts.append(prompt)
        
        return filtered_prompts
    
    def _get_prompts_path(self, ticker: str) -> Path:
        """Get path for prompts file"""
        return self.checkpoint_dir / f"{ticker}_prompts.json"