"""
XML thesis generator with validation and backup functionality
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
import shutil
from datetime import datetime
import logging
from typing import Dict, Any, Optional
import os

from utils.xml_validator import XMLValidator

logger = logging.getLogger(__name__)

class XMLThesisGenerator:
    """Generates and manages XML thesis files with validation and backup"""
    
    def __init__(self, output_dir: str):
        """
        Initialize XML generator
        
        Args:
            output_dir: Directory for thesis XML files
        """
        self.output_dir = Path(output_dir)
        self.backup_dir = self.output_dir / "backups"
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = XMLValidator()
        
        logger.info(f"XMLThesisGenerator initialized with output dir: {self.output_dir}")
    
    def append_thesis(self, 
                     ticker: str, 
                     as_of_date: str, 
                     thesis_data: Dict[str, Any]) -> bool:
        """
        Append a new thesis to the ticker's XML file
        
        Args:
            ticker: Stock ticker symbol
            as_of_date: Date of the thesis (YYYY-MM-DD format)
            thesis_data: Dictionary with reasoning, action, and support
            
        Returns:
            True if successful, False otherwise
        """
        xml_file = self.output_dir / f"{ticker}_theses.xml"
        
        try:
            # Validate thesis data
            thesis_entry = {
                "as-of-date": as_of_date,
                "reasoning": thesis_data.get("reasoning", ""),
                "action": thesis_data.get("action", "error"),
                "support": thesis_data.get("support", "")
            }
            
            is_valid, error_msg = self.validator.validate_thesis_entry(thesis_entry)
            if not is_valid:
                logger.error(f"Invalid thesis data: {error_msg}")
                # Create error entry
                thesis_entry = self._create_error_entry(as_of_date, f"Validation error: {error_msg}")
            
            # Create backup if file exists
            if xml_file.exists():
                if not self._create_backup(xml_file):
                    logger.warning("Failed to create backup, proceeding anyway")
            
            # Generate or update XML
            if not xml_file.exists():
                success = self._create_new_xml(ticker, thesis_entry)
            else:
                success = self._append_to_xml(xml_file, thesis_entry)
            
            if success:
                # Validate the updated file
                is_valid, error_msg = self.validator.validate_xml_file(xml_file)
                if not is_valid:
                    logger.error(f"XML validation failed after update: {error_msg}")
                    # Restore from backup
                    if self._restore_backup(xml_file):
                        logger.info("Successfully restored from backup")
                        return False
                    else:
                        logger.error("Failed to restore from backup!")
                        return False
            
            logger.info(f"Successfully appended thesis for {ticker} on {as_of_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error appending thesis for {ticker}: {e}")
            # Try to restore backup if something went wrong
            if xml_file.exists():
                self._restore_backup(xml_file)
            return False
    
    def _create_new_xml(self, ticker: str, thesis_entry: Dict[str, Any]) -> bool:
        """
        Create a new XML file with the first thesis entry
        
        Args:
            ticker: Stock ticker symbol
            thesis_entry: Thesis data dictionary
            
        Returns:
            True if successful
        """
        try:
            # Create root element
            root = ET.Element("stock-theses")
            root.set("ticker", ticker)
            root.set("generated-by", "Trainer-Charlie")
            root.set("version", "1.0")
            
            # Add thesis element
            thesis_elem = self._create_thesis_element(thesis_entry)
            root.append(thesis_elem)
            
            # Write to file with proper formatting
            xml_str = self._prettify_xml(root)
            xml_file = self.output_dir / f"{ticker}_theses.xml"
            
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(xml_str)
            
            logger.info(f"Created new XML file for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating new XML: {e}")
            return False
    
    def _append_to_xml(self, xml_file: Path, thesis_entry: Dict[str, Any]) -> bool:
        """
        Append thesis to existing XML file
        
        Args:
            xml_file: Path to existing XML file
            thesis_entry: Thesis data dictionary
            
        Returns:
            True if successful
        """
        try:
            # Parse existing XML
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Check if thesis for this date already exists
            as_of_date = thesis_entry["as-of-date"]
            existing = root.find(f".//thesis[as-of-date='{as_of_date}']")
            
            if existing is not None:
                logger.info(f"Overwriting existing thesis for {as_of_date}")
                root.remove(existing)
            
            # Add new thesis
            thesis_elem = self._create_thesis_element(thesis_entry)
            root.append(thesis_elem)
            
            # Write back with proper formatting
            xml_str = self._prettify_xml(root)
            
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(xml_str)
            
            return True
            
        except Exception as e:
            logger.error(f"Error appending to XML: {e}")
            return False
    
    def _create_thesis_element(self, thesis_entry: Dict[str, Any]) -> ET.Element:
        """
        Create a thesis XML element
        
        Args:
            thesis_entry: Thesis data dictionary
            
        Returns:
            XML Element for thesis
        """
        thesis = ET.Element("thesis")
        
        # Add child elements
        date_elem = ET.SubElement(thesis, "as-of-date")
        date_elem.text = thesis_entry["as-of-date"]
        
        reasoning_elem = ET.SubElement(thesis, "reasoning")
        reasoning_elem.text = thesis_entry["reasoning"]
        
        action_elem = ET.SubElement(thesis, "action")
        action_elem.text = thesis_entry["action"]
        
        support_elem = ET.SubElement(thesis, "support")
        support_elem.text = thesis_entry["support"]
        
        return thesis
    
    def _create_error_entry(self, as_of_date: str, error_message: str) -> Dict[str, Any]:
        """
        Create an error thesis entry
        
        Args:
            as_of_date: Date of the failed thesis
            error_message: Error description
            
        Returns:
            Error thesis dictionary
        """
        return {
            "as-of-date": as_of_date,
            "reasoning": f"ERROR: {error_message}",
            "action": "error",
            "support": "Failed to generate thesis due to error"
        }
    
    def _create_backup(self, xml_file: Path) -> bool:
        """
        Create a backup of the XML file
        
        Args:
            xml_file: Path to XML file to backup
            
        Returns:
            True if successful
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{xml_file.stem}_backup_{timestamp}.xml"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(xml_file, backup_path)
            
            # Also maintain a "last good" backup
            last_good_path = self.backup_dir / f"{xml_file.stem}_last_good.xml"
            shutil.copy2(xml_file, last_good_path)
            
            logger.debug(f"Created backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def _restore_backup(self, xml_file: Path) -> bool:
        """
        Restore XML file from last good backup
        
        Args:
            xml_file: Path to XML file to restore
            
        Returns:
            True if successful
        """
        try:
            last_good_path = self.backup_dir / f"{xml_file.stem}_last_good.xml"
            
            if not last_good_path.exists():
                logger.error(f"No backup found for {xml_file.name}")
                return False
            
            shutil.copy2(last_good_path, xml_file)
            logger.info(f"Restored {xml_file.name} from backup")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """
        Return a pretty-printed XML string for the Element
        
        Args:
            elem: XML Element
            
        Returns:
            Formatted XML string
        """
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        
        # Remove the XML declaration as we'll add it separately
        pretty_xml = reparsed.documentElement.toprettyxml(indent="  ")
        
        # Remove extra blank lines
        lines = pretty_xml.split('\n')
        return '\n'.join(line for line in lines if line.strip())
    
    def get_thesis_count(self, ticker: str) -> int:
        """
        Get the number of theses for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Number of thesis entries
        """
        xml_file = self.output_dir / f"{ticker}_theses.xml"
        
        if not xml_file.exists():
            return 0
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            return len(root.findall("thesis"))
        except Exception as e:
            logger.error(f"Error counting theses: {e}")
            return 0
    
    def get_latest_thesis(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent thesis for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Latest thesis data or None
        """
        xml_file = self.output_dir / f"{ticker}_theses.xml"
        
        if not xml_file.exists():
            return None
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Get all theses and sort by date
            theses = []
            for thesis_elem in root.findall("thesis"):
                thesis_data = {
                    "as-of-date": thesis_elem.find("as-of-date").text,
                    "reasoning": thesis_elem.find("reasoning").text,
                    "action": thesis_elem.find("action").text,
                    "support": thesis_elem.find("support").text,
                }
                theses.append(thesis_data)
            
            if not theses:
                return None
            
            # Sort by date and return latest
            theses.sort(key=lambda x: x["as-of-date"], reverse=True)
            return theses[0]
            
        except Exception as e:
            logger.error(f"Error getting latest thesis: {e}")
            return None