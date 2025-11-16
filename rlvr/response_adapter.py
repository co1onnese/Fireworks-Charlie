"""
Response Adapter for Converting Structured 5-7 Section Format to Legacy Format

This module converts the new structured response format (with fundamentals, technical,
news, valuation, risk_assessment, macro, conclusion sections) to the legacy format
expected by the reward function (action, reasoning, support).
"""
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


def adapt_structured_response_to_legacy(structured_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert 5-7 section structured response to legacy format for reward function compatibility.
    
    Args:
        structured_response: New format with fundamentals, technical, news, valuation,
                           risk_assessment, macro, conclusion sections
        
    Returns:
        Legacy format: {"action": "...", "reasoning": "...", "support": "..."}
    """
    if not isinstance(structured_response, dict):
        logger.warning("Structured response is not a dictionary, returning default")
        return {
            "action": "hold",
            "reasoning": "Invalid response format",
            "support": ""
        }
    
    # Extract conclusion section
    conclusion = structured_response.get("conclusion", {})
    recommendation = conclusion.get("recommendation", "Hold")
    
    # Convert "Strong Buy" → "strong_buy", etc.
    action_map = {
        "Strong Buy": "strong_buy",
        "Buy": "buy",
        "Hold": "hold",
        "Sell": "sell",
        "Strong Sell": "strong_sell"
    }
    action = action_map.get(recommendation, "hold")
    
    # Combine reasoning from all sections
    reasoning_parts = []
    
    # Fundamentals reasoning
    if structured_response.get("fundamentals"):
        fund = structured_response["fundamentals"]
        fund_text = []
        if fund.get("balance_sheet_strength"):
            fund_text.append(f"Balance Sheet: {fund['balance_sheet_strength']}")
        if fund.get("income_performance"):
            fund_text.append(f"Income: {fund['income_performance']}")
        if fund.get("cash_flow"):
            fund_text.append(f"Cash Flow: {fund['cash_flow']}")
        if fund_text:
            reasoning_parts.append("Fundamentals: " + " | ".join(fund_text))
    
    # Technical reasoning
    if structured_response.get("technical"):
        tech = structured_response["technical"]
        tech_text = []
        if tech.get("price_action"):
            tech_text.append(f"Price Action: {tech['price_action']}")
        if tech.get("momentum"):
            tech_text.append(f"Momentum: {tech['momentum']}")
        if tech_text:
            reasoning_parts.append("Technical: " + " | ".join(tech_text))
    
    # News reasoning
    if structured_response.get("news"):
        news = structured_response["news"]
        news_text = []
        if news.get("sentiment_summary"):
            news_text.append(f"Sentiment: {news['sentiment_summary']}")
        if news.get("recent_3_days"):
            news_text.append(f"Recent News: {news['recent_3_days'][:200]}...")  # Truncate
        if news_text:
            reasoning_parts.append("News: " + " | ".join(news_text))
    
    # Valuation reasoning
    if structured_response.get("valuation"):
        val = structured_response["valuation"]
        if val.get("assessment"):
            reasoning_parts.append(f"Valuation: {val['assessment']}")
    
    # Risk reasoning
    if structured_response.get("risk_assessment"):
        risk = structured_response["risk_assessment"]
        if risk.get("ticker_specific_risks"):
            reasoning_parts.append(f"Risks: {risk['ticker_specific_risks'][:200]}...")  # Truncate
    
    # Macro reasoning
    if structured_response.get("macro"):
        macro = structured_response["macro"]
        if macro.get("impact"):
            reasoning_parts.append(f"Macro: {macro['impact'][:200]}...")  # Truncate
    
    # Use conclusion reasoning if available, otherwise combine all parts
    if conclusion.get("reasoning"):
        reasoning = conclusion["reasoning"]
        if reasoning_parts:
            reasoning = reasoning + "\n\nAdditional Analysis:\n" + "\n".join(reasoning_parts)
    else:
        reasoning = "\n\n".join(reasoning_parts) if reasoning_parts else "No detailed reasoning provided"
    
    # Extract support from conclusion
    support_parts = []
    if conclusion.get("reasoning"):
        support_parts.append(conclusion["reasoning"])
    if conclusion.get("confidence") is not None:
        support_parts.append(f"Confidence: {conclusion['confidence']:.2f}")
    if conclusion.get("target_price"):
        support_parts.append(f"Target Price: {conclusion['target_price']}")
    if conclusion.get("time_horizon"):
        support_parts.append(f"Time Horizon: {conclusion['time_horizon']}")
    
    # Add key metrics as support
    if structured_response.get("fundamentals", {}).get("key_metrics"):
        metrics = structured_response["fundamentals"]["key_metrics"]
        metric_strs = []
        for key, value in metrics.items():
            if value is not None:
                metric_strs.append(f"{key}: {value}")
        if metric_strs:
            support_parts.append("Key Metrics: " + ", ".join(metric_strs))
    
    support = "\n".join(support_parts) if support_parts else ""
    
    return {
        "action": action,
        "reasoning": reasoning,
        "support": support
    }


def validate_structured_response(structured_response: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that structured response has required sections and correct format.
    
    Args:
        structured_response: Response dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(structured_response, dict):
        return False, ["Response is not a dictionary"]
    
    # Check required sections
    required_sections = ["fundamentals", "technical", "news", "valuation", "risk_assessment", "macro", "conclusion"]
    for section in required_sections:
        if section not in structured_response:
            errors.append(f"Missing required section: {section}")
    
    # Validate conclusion.recommendation
    conclusion = structured_response.get("conclusion", {})
    recommendation = conclusion.get("recommendation")
    valid_recommendations = ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]
    
    if not recommendation:
        errors.append("Missing conclusion.recommendation field")
    elif recommendation not in valid_recommendations:
        errors.append(f"Invalid recommendation '{recommendation}'. Must be one of: {valid_recommendations}")
    
    return len(errors) == 0, errors
