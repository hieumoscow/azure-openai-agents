"""
Secure Banking Functions Module

This module provides secure versions of banking functions with proper
authentication, authorization, input validation, and audit logging.
"""

import re
import logging
from typing import Union
from agents import function_tool
from auth import (
    require_auth, require_roles, require_account_access, 
    UserRole, User, security_logger
)

# Input validation patterns
ACCOUNT_ID_PATTERN = re.compile(r'^[0-9]{4,12}$')
AMOUNT_PATTERN = re.compile(r'^\d+(\.\d{1,2})?$')


def validate_account_id(account_id: str) -> str:
    """Validate and sanitize account ID"""
    if not account_id:
        raise ValueError("Account ID is required")
    
    # Remove any non-digit characters
    sanitized = re.sub(r'[^0-9]', '', str(account_id))
    
    if not ACCOUNT_ID_PATTERN.match(sanitized):
        raise ValueError("Invalid account ID format. Must be 4-12 digits.")
    
    return sanitized


def validate_amount(amount: Union[float, int, str]) -> float:
    """Validate and sanitize monetary amount"""
    if amount is None:
        raise ValueError("Amount is required")
    
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        raise ValueError("Amount must be a valid number")
    
    if amount_float < 0:
        raise ValueError("Amount must be positive")
    
    if amount_float > 1000000000:  # 1 billion limit
        raise ValueError("Amount exceeds maximum limit")
    
    # Round to 2 decimal places
    return round(amount_float, 2)


def validate_percentage(rate: Union[float, int, str]) -> float:
    """Validate and sanitize percentage rate"""
    if rate is None:
        raise ValueError("Rate is required")
    
    try:
        rate_float = float(rate)
    except (ValueError, TypeError):
        raise ValueError("Rate must be a valid number")
    
    if rate_float < 0 or rate_float > 100:
        raise ValueError("Rate must be between 0 and 100 percent")
    
    return round(rate_float, 4)


def validate_years(years: Union[int, str]) -> int:
    """Validate loan/investment years"""
    if years is None:
        raise ValueError("Years is required")
    
    try:
        years_int = int(years)
    except (ValueError, TypeError):
        raise ValueError("Years must be a valid integer")
    
    if years_int < 1 or years_int > 50:
        raise ValueError("Years must be between 1 and 50")
    
    return years_int


@function_tool
@require_auth()
@require_account_access()
def secure_check_account_balance(account_id: str, api_key: str, current_user: User = None) -> float:
    """
    Securely check the balance of a bank account.
    
    Args:
        account_id: The account ID to check
        api_key: Authentication API key
        current_user: Authenticated user (injected by decorator)
    
    Returns:
        Account balance
    
    Raises:
        ValueError: Invalid input parameters
        AuthenticationError: Authentication failed
        AuthorizationError: Authorization failed
    """
    # Validate input
    account_id = validate_account_id(account_id)
    
    # Mock database - in production, this would query a secure database
    balances = {
        "1234": 5432.10,
        "5678": 10245.33,
        "9012": 750.25,
        "default": 1000.00
    }
    
    balance = balances.get(account_id, balances["default"])
    
    # Security audit log
    security_logger.info(
        f"Account balance checked - User: {current_user.username} "
        f"({current_user.role.value}), Account: {account_id}, "
        f"Balance: ${balance:.2f}"
    )
    
    return balance


@function_tool
@require_auth()
@require_roles(UserRole.ADMIN, UserRole.TELLER)
def secure_calculate_loan_payment(
    principal: Union[float, str], 
    interest_rate: Union[float, str], 
    years: Union[int, str],
    api_key: str,
    current_user: User = None
) -> float:
    """
    Securely calculate monthly payment for a loan.
    
    Args:
        principal: Loan principal amount
        interest_rate: Annual interest rate (percentage)
        years: Loan term in years
        api_key: Authentication API key
        current_user: Authenticated user (injected by decorator)
    
    Returns:
        Monthly payment amount
    
    Raises:
        ValueError: Invalid input parameters
        AuthenticationError: Authentication failed
        AuthorizationError: Authorization failed
    """
    # Validate inputs
    principal = validate_amount(principal)
    interest_rate = validate_percentage(interest_rate)
    years = validate_years(years)
    
    # Convert annual interest rate to monthly rate and years to months
    monthly_rate = interest_rate / 100 / 12
    months = years * 12
    
    # Calculate monthly payment using the loan payment formula
    if monthly_rate == 0:
        monthly_payment = principal / months
    else:
        monthly_payment = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
    
    # Round to 2 decimal places
    monthly_payment = round(monthly_payment, 2)
    
    # Security audit log
    security_logger.info(
        f"Loan payment calculated - User: {current_user.username} "
        f"({current_user.role.value}), Principal: ${principal:.2f}, "
        f"Rate: {interest_rate}%, Years: {years}, "
        f"Monthly Payment: ${monthly_payment:.2f}"
    )
    
    return monthly_payment


@function_tool
@require_auth()
@require_roles(UserRole.ADMIN, UserRole.TELLER)
def secure_calculate_investment_return(
    principal: Union[float, str],
    annual_return_rate: Union[float, str],
    years: Union[int, str],
    api_key: str,
    current_user: User = None
) -> float:
    """
    Securely calculate the future value of an investment.
    
    Args:
        principal: Initial investment amount
        annual_return_rate: Expected annual return rate (percentage)
        years: Investment period in years
        api_key: Authentication API key
        current_user: Authenticated user (injected by decorator)
    
    Returns:
        Future value of investment
    
    Raises:
        ValueError: Invalid input parameters
        AuthenticationError: Authentication failed
        AuthorizationError: Authorization failed
    """
    # Validate inputs
    principal = validate_amount(principal)
    annual_return_rate = validate_percentage(annual_return_rate)
    years = validate_years(years)
    
    # Simple compound interest calculation
    future_value = principal * (1 + annual_return_rate / 100) ** years
    
    # Round to 2 decimal places
    future_value = round(future_value, 2)
    
    # Security audit log
    security_logger.info(
        f"Investment return calculated - User: {current_user.username} "
        f"({current_user.role.value}), Principal: ${principal:.2f}, "
        f"Rate: {annual_return_rate}%, Years: {years}, "
        f"Future Value: ${future_value:.2f}"
    )
    
    return future_value


@function_tool
@require_auth()
@require_roles(UserRole.ADMIN)
def secure_admin_get_all_accounts(api_key: str, current_user: User = None) -> dict:
    """
    Admin function to get all account information.
    
    Args:
        api_key: Authentication API key
        current_user: Authenticated user (injected by decorator)
    
    Returns:
        Dictionary of all accounts and balances
    
    Raises:
        AuthenticationError: Authentication failed
        AuthorizationError: Authorization failed (admin only)
    """
    # Mock database - in production, this would query a secure database
    all_accounts = {
        "1234": {"balance": 5432.10, "owner": "John Doe", "type": "checking"},
        "5678": {"balance": 10245.33, "owner": "Jane Smith", "type": "savings"},
        "9012": {"balance": 750.25, "owner": "Bob Johnson", "type": "checking"}
    }
    
    # Security audit log
    security_logger.warning(
        f"Admin function accessed - User: {current_user.username} "
        f"({current_user.role.value}) retrieved all account information"
    )
    
    return all_accounts