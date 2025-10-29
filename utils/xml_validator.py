"""
XML validation utilities for thesis files
"""
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class XMLValidator:
    """Validates XML thesis files"""
    
    @staticmethod
    def validate_xml_file(xml_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate an XML file for well-formedness and required structure
        
        Args:
            xml_path: Path to XML file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file exists
            if not xml_path.exists():
                return False, f"File not found: {xml_path}"
            
            # Parse XML
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Check root element
            if root.tag != "stock-theses":
                return False, f"Root element must be 'stock-theses', found '{root.tag}'"
            
            # Check required attributes
            if "ticker" not in root.attrib:
                return False, "Root element missing 'ticker' attribute"
            
            # Validate each thesis entry
            thesis_count = 0
            for thesis in root.findall("thesis"):
                thesis_count += 1
                
                # Check required child elements
                required_elements = ["as-of-date", "reasoning", "action", "support"]
                for elem_name in required_elements:
                    elem = thesis.find(elem_name)
                    if elem is None:
                        return False, f"Thesis {thesis_count} missing required element '{elem_name}'"
                    if not elem.text or not elem.text.strip():
                        return False, f"Thesis {thesis_count} has empty '{elem_name}' element"
                
                # Validate action value
                action = thesis.find("action").text.strip().lower()
                valid_actions = ["strong_buy", "buy", "hold", "sell", "strong_sell", "error"]
                if action not in valid_actions:
                    return False, f"Thesis {thesis_count} has invalid action '{action}'"
            
            if thesis_count == 0:
                return False, "XML file contains no thesis entries"
            
            logger.debug(f"XML validation successful: {thesis_count} theses found in {xml_path}")
            return True, None
            
        except ET.ParseError as e:
            return False, f"XML parsing error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def validate_thesis_entry(thesis_dict: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate a thesis dictionary before XML serialization
        
        Args:
            thesis_dict: Dictionary with thesis data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["as-of-date", "reasoning", "action", "support"]
        
        for field in required_fields:
            if field not in thesis_dict:
                return False, f"Missing required field '{field}'"
            if not thesis_dict[field]:
                return False, f"Empty value for field '{field}'"
        
        # Validate action
        action = thesis_dict["action"].lower()
        valid_actions = ["strong_buy", "buy", "hold", "sell", "strong_sell", "error"]
        if action not in valid_actions:
            return False, f"Invalid action '{action}'"
        
        return True, None
    
    @staticmethod
    def format_xml_string(xml_string: str) -> str:
        """
        Format XML string with proper indentation
        
        Args:
            xml_string: Raw XML string
            
        Returns:
            Formatted XML string
        """
        try:
            # Parse and reformat
            root = ET.fromstring(xml_string)
            return XMLValidator._prettify_element(root)
        except Exception as e:
            logger.warning(f"Failed to format XML: {e}")
            return xml_string
    
    @staticmethod
    def _prettify_element(elem: ET.Element, level: int = 0) -> str:
        """
        Recursively add indentation to XML elements
        
        Args:
            elem: XML element
            level: Current indentation level
            
        Returns:
            Formatted XML string
        """
        indent = "  "
        result = f"{indent * level}<{elem.tag}"
        
        # Add attributes
        for key, value in elem.attrib.items():
            result += f' {key}="{value}"'
        
        # Handle text content and children
        if elem.text and elem.text.strip():
            result += f">{elem.text.strip()}"
            if len(elem) > 0:
                result += "\n"
                for child in elem:
                    result += XMLValidator._prettify_element(child, level + 1)
                result += f"{indent * level}"
            result += f"</{elem.tag}>\n"
        elif len(elem) > 0:
            result += ">\n"
            for child in elem:
                result += XMLValidator._prettify_element(child, level + 1)
            result += f"{indent * level}</{elem.tag}>\n"
        else:
            result += f"></{elem.tag}>\n"
        
        return result