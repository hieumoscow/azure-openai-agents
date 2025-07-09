# Security Documentation - Banking Agents Demo

## Overview

This document outlines the security measures implemented in the Banking Agents Demo to meet compliance control C9262 requirements. The system implements comprehensive authentication mechanisms, authorization policies, and security controls to protect sensitive banking data and operations.

## Authentication Mechanisms

### API Key Authentication

The system uses API key-based authentication for all banking operations:

- **API Keys**: Securely hashed using SHA-256 before storage
- **Key Validation**: All requests must include a valid API key
- **User Mapping**: Each API key is mapped to a specific user account

#### Default API Keys (Development Only)

⚠️ **WARNING**: Change these keys in production!

- Admin: `admin-key-12345`
- Teller: `teller-key-12345`
- Customer: `customer-key-12345`

#### Production Configuration

Set these environment variables with secure, randomly generated keys:

```bash
ADMIN_API_KEY=your-secure-admin-key-here
TELLER_API_KEY=your-secure-teller-key-here
CUSTOMER_API_KEY=your-secure-customer-key-here
```

### Session Token Authentication

For extended sessions, the system supports token-based authentication:

- **Token Generation**: SHA-256 hashed tokens with configurable expiration
- **Session Management**: Automatic cleanup of expired tokens
- **Token Refresh**: Tokens can be refreshed before expiration

## Authorization Policies

### Role-Based Access Control (RBAC)

The system implements three user roles with distinct permissions:

#### Admin Role (`admin`)
- **Permissions**: Full system access
- **Account Access**: All accounts
- **Functions**: All banking operations + administrative functions
- **Use Case**: System administrators, compliance officers

#### Teller Role (`teller`)
- **Permissions**: Customer service operations
- **Account Access**: Assigned accounts only
- **Functions**: Account balance checks, loan calculations, investment calculations
- **Use Case**: Bank tellers, customer service representatives

#### Customer Role (`customer`)
- **Permissions**: Self-service operations
- **Account Access**: Own accounts only
- **Functions**: Account balance checks only
- **Use Case**: Bank customers accessing their own accounts

### Account-Level Authorization

- **Account Ownership**: Users can only access accounts they own or are assigned to
- **Access Control Lists**: Each user has a list of permitted account IDs
- **Admin Override**: Admin users can access any account for compliance purposes

## Input Validation and Security Controls

### Data Sanitization

All user inputs are validated and sanitized:

- **Account IDs**: Must be 4-12 digits, non-digits are stripped
- **Monetary Amounts**: Validated as positive numbers with 2 decimal places
- **Interest Rates**: Must be 0-100%, validated as percentages
- **Years**: Must be 1-50 years for loans and investments

### Business Logic Validation

- **Amount Limits**: Maximum transaction amount of $1 billion
- **Rate Limits**: Interest rates between 0-100%
- **Term Limits**: Loan/investment terms between 1-50 years

### Security Logging and Audit Trail

All security-sensitive operations are logged with:

- **Timestamp**: When the operation occurred
- **User Information**: Username and role
- **Operation Details**: What was accessed or calculated
- **Access Results**: Whether access was granted or denied

#### Log Examples

```
2024-01-15 10:30:25 - SECURITY - INFO - User authenticated: john_doe (customer)
2024-01-15 10:30:26 - SECURITY - INFO - Account balance checked - User: john_doe (customer), Account: 1234, Balance: $5432.10
2024-01-15 10:31:15 - SECURITY - WARNING - Authorization denied: User john_doe (customer) attempted to access account 5678
```

## Secure Configuration

### Environment Variables

#### Required for Security

```bash
# User API Keys (use secure random strings in production)
ADMIN_API_KEY=your-secure-admin-key
TELLER_API_KEY=your-secure-teller-key  
CUSTOMER_API_KEY=your-secure-customer-key

# Environment indicator
ENVIRONMENT=production  # or development
```

#### Required for Azure OpenAI

```bash
# Azure OpenAI Direct Connection
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_ENDPOINT=https://your-aoai.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# OR Azure API Management Connection
AZURE_APIM_OPENAI_SUBSCRIPTION_KEY=your-apim-key
AZURE_APIM_OPENAI_API_VERSION=2024-08-01-preview
AZURE_APIM_OPENAI_ENDPOINT=https://your-apim.azure-api.net/suffix/api/
AZURE_APIM_OPENAI_DEPLOYMENT=gpt-4o
```

### Configuration Validation

The system validates configuration on startup:

- **API Key Security**: Ensures default keys are not used in production
- **Required Variables**: Validates all required environment variables are present
- **Connection Tests**: Can be extended to test Azure OpenAI connectivity

## Security Features

### Implemented Security Controls

✅ **Authentication**
- API key-based authentication
- Session token management
- User identity verification

✅ **Authorization**
- Role-based access control (RBAC)
- Account-level permissions
- Function-level authorization

✅ **Input Validation**
- Data type validation
- Format validation
- Business rule validation
- Input sanitization

✅ **Audit Logging**
- Security event logging
- Access attempt logging
- Operation audit trail

✅ **Configuration Security**
- Environment variable validation
- Secure default prevention
- Configuration error detection

### Error Handling

The system implements secure error handling:

- **Authentication Errors**: Generic messages to prevent information disclosure
- **Authorization Errors**: Clear messages for legitimate users
- **Validation Errors**: Specific messages to help with correct input
- **System Errors**: Logged but not exposed to users

## Usage Examples

### Customer Access

```python
# Customer checking their own account balance
balance = secure_check_account_balance(
    account_id="1234",
    api_key="customer-key-12345"
)
print(f"Balance: ${balance}")
```

### Teller Operations

```python
# Teller calculating loan payment for customer
payment = secure_calculate_loan_payment(
    principal=300000,
    interest_rate=4.5,
    years=30,
    api_key="teller-key-12345"
)
print(f"Monthly payment: ${payment}")
```

### Admin Operations

```python
# Admin accessing all account information
accounts = secure_admin_get_all_accounts(
    api_key="admin-key-12345"
)
print(f"Total accounts: {len(accounts)}")
```

## Compliance Control C9262

This implementation addresses compliance control C9262 requirements:

### Authentication Mechanisms ✅
- Multi-factor authentication via API keys
- Session management with token expiration
- User identity verification and mapping

### Authorization Policies ✅
- Role-based access control (RBAC)
- Principle of least privilege
- Account-level access controls

### Documentation ✅
- Comprehensive security documentation
- Configuration guidelines
- Usage examples and best practices

### Security Controls ✅
- Input validation and sanitization
- Audit logging and monitoring
- Secure configuration management
- Error handling and information disclosure prevention

## Best Practices

### For Developers

1. **Never hardcode credentials** in source code
2. **Always validate inputs** before processing
3. **Use the security decorators** for all sensitive functions
4. **Log security events** for audit purposes
5. **Test authorization** with different user roles

### For Operators

1. **Use strong API keys** in production (minimum 32 characters)
2. **Rotate API keys** regularly
3. **Monitor security logs** for suspicious activity
4. **Validate configuration** before deployment
5. **Use environment-specific** configurations

### For Users

1. **Keep API keys secure** and confidential
2. **Use appropriate role** for your access needs
3. **Report suspicious activity** immediately
4. **Follow data access policies**

## Security Testing

### Authentication Testing

- Test with valid API keys
- Test with invalid API keys
- Test with missing API keys
- Test with expired session tokens

### Authorization Testing

- Test role-based access controls
- Test account-level permissions
- Test privilege escalation attempts
- Test cross-account access attempts

### Input Validation Testing

- Test with invalid data types
- Test with malformed inputs
- Test with extreme values
- Test with injection attempts

## Incident Response

### Security Event Types

1. **Authentication Failures**: Invalid API key attempts
2. **Authorization Violations**: Unauthorized access attempts
3. **Input Validation Errors**: Malformed or malicious inputs
4. **Configuration Errors**: Invalid or insecure configuration

### Response Actions

1. **Log the incident** with full details
2. **Block the request** if necessary
3. **Alert administrators** for serious violations
4. **Investigate patterns** of suspicious activity

## Maintenance and Updates

### Regular Tasks

- Review and rotate API keys
- Monitor security logs
- Update security documentation
- Test security controls
- Validate configurations

### Security Updates

- Keep dependencies updated
- Review security advisories
- Test security patches
- Update documentation

This security implementation provides a robust foundation for meeting compliance requirements while maintaining usability and performance.
