# API Service Discovery Approach

## Overview

This document outlines the comprehensive service discovery architecture implemented for the Azure OpenAI Agents banking application. The solution addresses the critical requirements for dynamic service discovery, health monitoring, load balancing, and failover strategies to ensure robust and resilient API communication.

## Architecture

### Service Discovery Mechanism

The application implements a hybrid service discovery approach that combines:

1. **Configuration-based Discovery**: Initial service endpoints loaded from configuration
2. **Health-based Selection**: Dynamic endpoint selection based on health status
3. **Failover Management**: Automatic failover when primary endpoints become unavailable
4. **Load Balancing**: Distribution of requests across healthy endpoints

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
├─────────────────────────────────────────────────────────────┤
│                Service Discovery Client                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Endpoint Manager│  │  Health Monitor │  │Load Balancer │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Service Registry                         │
│              (Configuration + Runtime State)               │
├─────────────────────────────────────────────────────────────┤
│                  Azure Services Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Azure OpenAI   │  │   Azure APIM    │  │  Backup      │ │
│  │   (Primary)     │  │   (Gateway)     │  │ Endpoints    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Service Discovery Implementation

### Endpoint Configuration

Services are configured with multiple endpoints to support redundancy:

```python
# Service endpoints configuration
SERVICE_ENDPOINTS = {
    "azure_openai": [
        {
            "name": "primary",
            "endpoint": "https://primary.openai.azure.com",
            "api_key": "${AZURE_OPENAI_API_KEY}",
            "priority": 1,
            "health_check_url": "/models"
        },
        {
            "name": "secondary", 
            "endpoint": "https://secondary.openai.azure.com",
            "api_key": "${AZURE_OPENAI_API_KEY_SECONDARY}",
            "priority": 2,
            "health_check_url": "/models"
        }
    ],
    "azure_apim": [
        {
            "name": "apim_gateway",
            "endpoint": "https://api.company.com/openai",
            "api_key": "${AZURE_APIM_SUBSCRIPTION_KEY}",
            "priority": 1,
            "health_check_url": "/health"
        }
    ]
}
```

### Health Check Configuration

Comprehensive health monitoring ensures only healthy endpoints receive traffic:

```yaml
health_checks:
  interval: 30s              # Health check frequency
  timeout: 10s               # Request timeout
  retries: 3                 # Retry attempts
  failure_threshold: 3       # Failures before marking unhealthy
  success_threshold: 2       # Successes before marking healthy
  
  checks:
    - name: endpoint_availability
      type: http_get
      path: /models
      expected_status: [200, 401]  # 401 is acceptable (auth required)
      
    - name: response_time
      type: latency
      threshold: 5000ms
      
    - name: api_quota
      type: custom
      function: check_api_quota
```

## Load Balancing Strategy

### Load Balancing Algorithms

1. **Priority-based**: Routes to highest priority healthy endpoint
2. **Round-robin**: Distributes requests evenly across healthy endpoints
3. **Least-connections**: Routes to endpoint with fewest active connections
4. **Weighted**: Distributes based on endpoint capacity weights

### Configuration Example

```python
load_balancer_config = {
    "algorithm": "priority_with_fallback",
    "sticky_sessions": False,
    "connection_pooling": True,
    "max_connections_per_endpoint": 100,
    "request_timeout": 30,
    "retry_policy": {
        "max_retries": 3,
        "backoff_strategy": "exponential",
        "retry_codes": [500, 502, 503, 504, 429]
    }
}
```

## Failover Strategy

### Failover Mechanisms

1. **Automatic Failover**: Immediate switch to backup endpoints on failure
2. **Circuit Breaker**: Prevents cascade failures by temporarily isolating failed services
3. **Gradual Recovery**: Slowly reintroduces recovered endpoints to traffic

### Circuit Breaker Configuration

```python
circuit_breaker = {
    "failure_threshold": 5,      # Failures before opening circuit
    "recovery_timeout": 60,      # Seconds before attempting recovery
    "success_threshold": 3,      # Successes needed to close circuit
    "half_open_max_calls": 5     # Max calls in half-open state
}
```

## API Gateway Integration

### Azure API Management (APIM) Design

The application integrates with Azure APIM for additional service management:

```yaml
apim_configuration:
  policies:
    - name: rate_limiting
      requests_per_minute: 1000
      
    - name: authentication
      type: subscription_key
      header: "Ocp-Apim-Subscription-Key"
      
    - name: caching
      duration: 300  # 5 minutes
      vary_by_header: ["Authorization"]
      
    - name: retry_policy
      count: 3
      interval: 2
      delta: 1
```

### Gateway Benefits

- **Centralized Authentication**: Single point for API key management
- **Rate Limiting**: Prevents API quota exhaustion
- **Caching**: Reduces redundant requests
- **Monitoring**: Comprehensive request/response logging
- **Transformation**: Request/response modification capabilities

## Service Communication Patterns

### Retry Patterns

```python
retry_config = {
    "max_attempts": 3,
    "base_delay": 1.0,          # Initial delay in seconds
    "max_delay": 60.0,          # Maximum delay between retries
    "exponential_base": 2,      # Exponential backoff multiplier
    "jitter": True              # Add randomness to prevent thundering herd
}
```

### Timeout Configuration

```python
timeout_config = {
    "connection_timeout": 10,    # Seconds to establish connection
    "read_timeout": 30,         # Seconds to read response
    "total_timeout": 45,        # Total request timeout
    "keepalive_timeout": 600    # Connection keep-alive duration
}
```

## Monitoring and Observability

### Health Metrics

- **Endpoint Availability**: Up/down status of each endpoint
- **Response Time**: Latency measurements per endpoint
- **Error Rates**: Failed request percentage
- **Throughput**: Requests per second per endpoint

### Alerting

```yaml
alerts:
  - name: endpoint_down
    condition: endpoint_health == false
    duration: 2m
    
  - name: high_error_rate
    condition: error_rate > 5%
    duration: 5m
    
  - name: slow_response
    condition: avg_response_time > 10s
    duration: 3m
```

## Configuration Management

### Environment-based Configuration

```bash
# Primary Azure OpenAI Configuration
AZURE_OPENAI_PRIMARY_ENDPOINT=https://primary.openai.azure.com
AZURE_OPENAI_PRIMARY_KEY=your_primary_key
AZURE_OPENAI_PRIMARY_DEPLOYMENT=gpt-4o

# Secondary Azure OpenAI Configuration  
AZURE_OPENAI_SECONDARY_ENDPOINT=https://secondary.openai.azure.com
AZURE_OPENAI_SECONDARY_KEY=your_secondary_key
AZURE_OPENAI_SECONDARY_DEPLOYMENT=gpt-4o

# APIM Configuration
AZURE_APIM_ENDPOINT=https://api.company.com/openai
AZURE_APIM_SUBSCRIPTION_KEY=your_apim_key

# Service Discovery Configuration
SERVICE_DISCOVERY_ENABLED=true
HEALTH_CHECK_INTERVAL=30
LOAD_BALANCER_ALGORITHM=priority_with_fallback
CIRCUIT_BREAKER_ENABLED=true
```

### Runtime Configuration

Services can be reconfigured at runtime without restarts:

```python
# Update endpoint configuration
service_discovery.update_endpoint("azure_openai", "primary", {
    "endpoint": "https://new-primary.openai.azure.com",
    "priority": 1
})

# Temporarily disable endpoint
service_discovery.disable_endpoint("azure_openai", "secondary")

# Update health check interval
service_discovery.configure_health_checks(interval=60)
```

## Security Considerations

### API Key Management

- **Key Rotation**: Automatic rotation of API keys
- **Least Privilege**: Minimal required permissions per endpoint
- **Secure Storage**: Keys stored in Azure Key Vault or similar
- **Audit Logging**: All key usage logged and monitored

### Network Security

- **TLS Encryption**: All communication over HTTPS
- **Network Isolation**: Endpoints accessible only from authorized networks
- **IP Whitelisting**: Restrict access to known IP ranges
- **Certificate Validation**: Verify SSL certificates for all endpoints

## Best Practices

### Development Guidelines

1. **Always configure multiple endpoints** for production workloads
2. **Implement comprehensive health checks** for all external dependencies
3. **Use exponential backoff** for retry mechanisms
4. **Monitor and alert** on service discovery metrics
5. **Test failover scenarios** regularly
6. **Document endpoint dependencies** and their criticality

### Deployment Considerations

1. **Gradual Rollout**: Deploy service discovery changes incrementally
2. **Blue-Green Deployment**: Maintain separate endpoint sets for deployments
3. **Canary Testing**: Test new endpoints with limited traffic first
4. **Rollback Plan**: Maintain ability to quickly revert to previous configuration

## Implementation Examples

See the following files for implementation details:

- `service_discovery.py`: Core service discovery implementation
- `health_monitor.py`: Health checking functionality
- `load_balancer.py`: Load balancing and failover logic
- `config/service_endpoints.yaml`: Endpoint configuration examples

## Troubleshooting

### Common Issues

1. **All endpoints marked unhealthy**: Check network connectivity and API keys
2. **High latency**: Review load balancing algorithm and endpoint locations
3. **Frequent failovers**: Investigate endpoint stability and health check sensitivity
4. **Authentication failures**: Verify API keys and subscription status

### Debug Commands

```bash
# Check endpoint health status
python -m service_discovery health-status

# Test endpoint connectivity
python -m service_discovery test-endpoint azure_openai primary

# View current configuration
python -m service_discovery show-config

# Enable debug logging
export LOG_LEVEL=DEBUG
```

This service discovery approach ensures high availability, optimal performance, and robust error handling for the Azure OpenAI Agents application.