# Banking Agents Demo

This project demonstrates the use of OpenAI's Agents framework to create a set of banking-themed conversational agents that can assist users with various banking-related inquiries.

## Features

- **Banking Assistant**: A general assistant for banking inquiries that can check account balances
- **Loan Specialist**: An agent focused on helping customers understand loan options and calculate payments
- **Investment Specialist**: An agent that assists customers with investment options and portfolio management
- **Customer Service Agent**: Handles general inquiries and directs customers to specialists as needed

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

The application supports two methods of connecting to Azure OpenAI:

### Direct Azure OpenAI Connection
The following environment variables are required for direct connection:
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_API_VERSION`: API version (e.g., "2024-08-01-preview")
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT`: The model deployment name (e.g., "gpt-4o")

### Azure API Management (APIM) Connection
Alternatively, you can connect via Azure API Management with these variables:
- `AZURE_APIM_OPENAI_SUBSCRIPTION_KEY`: Your APIM subscription key
- `AZURE_APIM_OPENAI_API_VERSION`: API version for APIM
- `AZURE_APIM_OPENAI_ENDPOINT`: Your APIM endpoint URL
- `AZURE_APIM_OPENAI_DEPLOYMENT`: The model deployment name in APIM

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