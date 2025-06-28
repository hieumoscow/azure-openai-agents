# Banking Agents Demo

This project demonstrates the use of OpenAI's Agents framework to create a set of banking-themed conversational agents that can assist users with various banking-related inquiries. The application now includes comprehensive **Service Discovery** capabilities for robust, highly-available API communication.

## Features

- **Banking Assistant**: A general assistant for banking inquiries that can check account balances
- **Loan Specialist**: An agent focused on helping customers understand loan options and calculate payments
- **Investment Specialist**: An agent that assists customers with investment options and portfolio management
- **Customer Service Agent**: Handles general inquiries and directs customers to specialists as needed
- **Service Discovery**: Advanced endpoint management with health monitoring, load balancing, and automatic failover

## Service Discovery Architecture

This application implements a comprehensive service discovery solution that addresses enterprise requirements for:

✅ **Service discovery mechanism documented and implemented**  
✅ **Uses service registry and health-based discovery**  
✅ **Includes comprehensive health check configuration**  
✅ **Documents load balancing and failover strategy**  

### Key Service Discovery Features

- **Multi-endpoint Configuration**: Support for primary, secondary, and backup Azure OpenAI endpoints
- **Health Monitoring**: Continuous health checking with configurable intervals and thresholds
- **Load Balancing**: Multiple algorithms including priority-based, round-robin, and weighted distribution
- **Automatic Failover**: Circuit breaker pattern with automatic endpoint recovery
- **APIM Integration**: Full support for Azure API Management gateway endpoints
- **Runtime Configuration**: Update endpoints and configuration without service restarts

For detailed information about the service discovery architecture, see [Service Discovery Documentation](docs/SERVICE_DISCOVERY.md).

## Agent Handoff System

The demo showcases the handoff functionality between agents:
- The Customer Service Agent can hand off conversations to the Loan Specialist or Investment Specialist based on the user's needs
- Each specialist has specific tools and knowledge to better assist with domain-specific questions

## Tools

The agents have access to the following tools:
- `check_account_balance`: Retrieves the balance for a given account number
- `calculate_loan_payment`: Calculates monthly payments for a loan based on principal, interest rate, and term

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on the `.env.sample` template and add your Azure OpenAI API credentials
4. Run the demo:
   ```
   python main.py
   ```

## Environment Variables

The application supports multiple methods of connecting to Azure OpenAI with enhanced service discovery capabilities:

### Service Discovery Configuration

Enable service discovery for automatic endpoint management, health monitoring, and failover:

```bash
# Enable service discovery (recommended for production)
SERVICE_DISCOVERY_ENABLED=true

# Health check configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_FAILURE_THRESHOLD=3
HEALTH_CHECK_SUCCESS_THRESHOLD=2

# Load balancer configuration
LOAD_BALANCER_ALGORITHM=priority_with_fallback
LOAD_BALANCER_TIMEOUT=30
LOAD_BALANCER_MAX_RETRIES=3

# Circuit breaker configuration
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=3
```

### Primary Azure OpenAI Connection

**Primary endpoint** (highest priority):
- `AZURE_OPENAI_API_KEY`: Your primary Azure OpenAI API key
- `AZURE_OPENAI_API_VERSION`: API version (e.g., "2024-08-01-preview")
- `AZURE_OPENAI_ENDPOINT`: Your primary Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT`: The model deployment name (e.g., "gpt-4o")

### Secondary Azure OpenAI Endpoints (for Failover)

**Secondary endpoint** (backup):
- `AZURE_OPENAI_SECONDARY_ENDPOINT`: Your secondary Azure OpenAI endpoint URL
- `AZURE_OPENAI_SECONDARY_KEY`: Your secondary Azure OpenAI API key
- `AZURE_OPENAI_SECONDARY_DEPLOYMENT`: Secondary model deployment name

**Backup endpoint** (tertiary):
- `AZURE_OPENAI_BACKUP_ENDPOINT`: Your backup Azure OpenAI endpoint URL
- `AZURE_OPENAI_BACKUP_KEY`: Your backup Azure OpenAI API key
- `AZURE_OPENAI_BACKUP_DEPLOYMENT`: Backup model deployment name

### Azure API Management (APIM) Connection

**Primary APIM Gateway**:
- `AZURE_APIM_OPENAI_SUBSCRIPTION_KEY`: Your primary APIM subscription key
- `AZURE_APIM_OPENAI_API_VERSION`: API version for APIM
- `AZURE_APIM_OPENAI_ENDPOINT`: Your primary APIM endpoint URL
- `AZURE_APIM_OPENAI_DEPLOYMENT`: The model deployment name in APIM

**Secondary APIM Gateway** (for failover):
- `AZURE_APIM_SECONDARY_SUBSCRIPTION_KEY`: Your secondary APIM subscription key
- `AZURE_APIM_SECONDARY_ENDPOINT`: Your secondary APIM endpoint URL

### Legacy Configuration (Direct Connection)

For backward compatibility, direct single-endpoint configuration is still supported:
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_API_VERSION`: API version
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT`: The model deployment name

## Service Discovery Usage

### Basic Usage

The application automatically uses service discovery when `SERVICE_DISCOVERY_ENABLED=true`. The system will:

1. **Load all configured endpoints** from environment variables
2. **Start health monitoring** for each endpoint
3. **Select the best available endpoint** based on health and priority
4. **Automatically failover** if the current endpoint becomes unhealthy
5. **Continuously monitor** and recover endpoints as they become available

### Health Monitoring

Check the health status of all configured endpoints:

```bash
python -m service_discovery_client health-status azure_openai
```

Test connectivity to a specific endpoint:

```bash
python -m service_discovery_client test-endpoint azure_openai primary
```

View current configuration:

```bash
python -m service_discovery_client show-config
```

### Load Balancing Algorithms

Configure the load balancing strategy with `LOAD_BALANCER_ALGORITHM`:

- **priority_with_fallback**: Routes to highest priority healthy endpoint (recommended)
- **round_robin**: Distributes requests evenly across healthy endpoints
- **least_connections**: Routes to endpoint with fewest active connections
- **weighted**: Distributes based on endpoint capacity weights

### Circuit Breaker

The circuit breaker pattern prevents cascade failures:

- **Closed**: Normal operation, requests flow through
- **Open**: Endpoint marked as failed, requests routed to other endpoints
- **Half-Open**: Testing endpoint recovery with limited requests

## Known Issues

Note that at the time of writing this article, there is an ongoing bug where OpenAI Agent SDK is fetching the old `input_tokens`, `output_tokens` instead of the new `prompt_tokens` & `completion_tokens` returned by newer ChatCompletion APIs. 

Thus you would need to manually update in `agents/run.py` file to make this work per:
- https://github.com/openai/openai-agents-python/pull/65/files
- https://github.com/openai/openai-agents-python/pull/61/files

The change involves replacing:
```python
input_tokens=event.response.usage.input_tokens,
output_tokens=event.response.usage.output_tokens,
```

With:
```python
input_tokens=event.response.usage.prompt_tokens,
output_tokens=event.response.usage.completion_tokens,
```

## Sample Conversation Flow

1. User asks a general banking question
2. If the question is about loans, the conversation is handed off to the Loan Specialist
3. The Loan Specialist can calculate loan payments and provide detailed loan information
4. If the question is about investments, the conversation is handed off to the Investment Specialist


## Monitoring with Application Insights

![OpenAIAgentsSDKAppInsights](./assets/OpenAIAgentsSDKAppInsights.gif)

A detailed blog post about monitoring the OpenAI Agents SDK with Application Insights has been published on the Microsoft Tech Community:

- [Monitoring OpenAI Agents SDK with Application Insights](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/monitoring-openai-agents-sdk-with-application-insights/4393949)

The blog post covers:
- How to use the Pydantic Logfire SDK to instrument OpenAI Agents
- Setting up the OpenTelemetry Collector to forward telemetry to Azure Application Insights
- Auto-instrumentation options for AKS and Azure Container Apps
- Known issues and workarounds for span name display in Application Insights

### Implementation Details

This repository contains a working example of the concepts discussed in the blog post. Key implementation highlights:

- **Logfire Integration**: The `main.py` file demonstrates how to configure Logfire for OpenAI Agents instrumentation with the following code:
  ```python
  # Configure logfire
  logfire.configure(
      service_name='banking-agent-service',
      send_to_logfire=False,
      distributed_tracing=True
  )
  logfire.instrument_openai_agents()
  ```

- **OpenTelemetry Configuration**: The `otel-collector-config.yaml` file shows how to set up an OpenTelemetry Collector to forward traces to Azure Application Insights:
  ```yaml
  receivers:
    otlp:
      protocols:
        http:
          endpoint: "0.0.0.0:4318"
  exporters:
    azuremonitor:
      connection_string: ""  # Add your Application Insights connection string here
  service:
    pipelines:
      traces:
        receivers: [otlp]
        exporters: [azuremonitor]
  ```

- **Span Name Fix**: The `fixed_openai_agents.py` file contains a workaround for the span name display issue in Application Insights, ensuring that spans show meaningful names instead of message templates.

To fully implement monitoring in your own projects, refer to the blog post for detailed instructions and best practices.

## License

This project is for demonstration purposes only.