from __future__ import annotations
import logging
import os
import asyncio
from dotenv import load_dotenv

from openai import AsyncAzureOpenAI
from agents import Agent, HandoffInputData, Runner, function_tool, handoff, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key, add_trace_processor
from agents.tracing.processors import ConsoleSpanExporter, BatchTraceProcessor
from agents.extensions import handoff_filters
import logfire

# Import service discovery components
from service_discovery_client import (
    create_service_discovery_client, 
    create_fallback_client,
    check_service_health
)

# logging.basicConfig(level=logging.INFO, 
#                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# https://github.com/openai/openai-agents-python/pull/61/files

load_dotenv()

# Global client variable
openai_client = None

async def initialize_openai_client():
    """Initialize OpenAI client with service discovery or fallback to traditional approach"""
    global openai_client
    
    try:
        # Try to create service discovery-enabled client
        if os.getenv("SERVICE_DISCOVERY_ENABLED", "false").lower() == "true":
            logger.info("Initializing OpenAI client with service discovery...")
            sd_client = await create_service_discovery_client("azure_openai")
            
            if sd_client:
                openai_client = sd_client
                logger.info("Service discovery client initialized successfully")
                
                # Log service health status
                try:
                    health_status = await check_service_health("azure_openai")
                    logger.info(f"Azure OpenAI service health: {health_status['healthy_endpoints']}/{health_status['total_endpoints']} endpoints healthy")
                except Exception as e:
                    logger.warning(f"Could not check service health: {e}")
                
                set_default_openai_client(openai_client)
                return
        
        # Fallback to traditional client creation
        logger.info("Using traditional OpenAI client configuration...")
        openai_client = await create_fallback_client()
        set_default_openai_client(openai_client)
        logger.info("Traditional OpenAI client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        # Final fallback - create basic client with environment variables
        logger.info("Using basic fallback client...")
        openai_client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )
        set_default_openai_client(openai_client)

os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]= "http://0.0.0.0:4318/v1/traces"

# Set the API key for trace export
set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
# Set up console tracing
# console_exporter = ConsoleSpanExporter()
# console_processor = BatchTraceProcessor(console_exporter)
# add_trace_processor(console_processor)
set_tracing_disabled(False)

# Configure logfire
logfire.configure(
    service_name='banking-agent-service',
    send_to_logfire=False,
    distributed_tracing=True
)
logfire.instrument_openai_agents()

@function_tool
def check_account_balance(account_id: str) -> float:
    """Check the balance of a bank account."""
    # This is a mock function - in a real application, this would query a database
    balances = {
        "1234": 5432.10,
        "5678": 10245.33,
        "9012": 750.25,
        "default": 1000.00
    }
    return balances.get(account_id, balances["default"])


@function_tool
def calculate_loan_payment(principal: float, interest_rate: float, years: int) -> float:
    """Calculate monthly payment for a loan."""
    # Convert annual interest rate to monthly rate and convert years to months
    monthly_rate = interest_rate / 100 / 12
    months = years * 12
    
    # Calculate monthly payment using the loan payment formula
    if monthly_rate == 0:
        return principal / months
    else:
        return principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)


@function_tool
def calculate_investment_return(principal: float, annual_return_rate: float, years: int) -> float:
    """Calculate the future value of an investment."""
    # Simple compound interest calculation
    return principal * (1 + annual_return_rate / 100) ** years


def banking_handoff_message_filter(handoff_message_data: HandoffInputData) -> HandoffInputData:
    # Remove any tool-related messages from the message history
    handoff_message_data = handoff_filters.remove_all_tools(handoff_message_data)
    
    # Keep the full conversation history for the banking specialist
    return handoff_message_data


# Banking-themed agents
general_agent = Agent(
    name="Banking Assistant",
    instructions="You are a helpful banking assistant. Be concise and professional.",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[check_account_balance],
)

loan_specialist_agent = Agent(
    name="Loan Specialist",
    instructions="""You are a loan specialist at a bank. 
    Focus on helping customers understand loan options, calculate payments, and assess affordability.
    Always ask for income information to provide personalized advice.
    Be professional, thorough, and explain financial terms clearly.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[calculate_loan_payment],
)

investment_specialist_agent = Agent(
    name="Investment Specialist",
    instructions="""You are an investment specialist at a bank.
    Help customers understand investment options, risk profiles, and portfolio diversification.
    Always consider the customer's financial goals and risk tolerance.
    Be professional and explain investment concepts in clear terms.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[calculate_investment_return],
)

customer_service_agent = Agent(
    name="Customer Service Agent",
    instructions="""You are a customer service agent at a bank.
    Help customers with general inquiries and direct them to specialists when needed.
    If the customer asks about loans or mortgages, handoff to the Loan Specialist.
    If the customer asks about investments or portfolio management, handoff to the Investment Specialist.
    Be professional, friendly, and helpful.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    handoffs=[
        handoff(loan_specialist_agent, input_filter=banking_handoff_message_filter),
        handoff(investment_specialist_agent, input_filter=banking_handoff_message_filter),
    ],
    tools=[check_account_balance],
)


async def main():
    # Initialize OpenAI client with service discovery
    await initialize_openai_client()
    
    # Trace the entire run as a single workflow
    with trace(workflow_name="Banking Assistant Demo"):
        print("\n=== Banking Assistant Demo ===\n")
        
        # Log current endpoint information if using service discovery
        if hasattr(openai_client, 'get_current_endpoint_info'):
            endpoint_info = openai_client.get_current_endpoint_info()
            if endpoint_info:
                print(f"Using endpoint: {endpoint_info['name']} ({endpoint_info['endpoint']}) - Status: {endpoint_info['status']}")
        
        # 1. Send a regular message to the general agent
        print("Step 1: Initial greeting")
        result = await Runner.run(general_agent, input="Hi, I'd like to check my account balance.")
        print(f"\nResponse: {result.final_output}\n")

        # 2. Check account balance with customer service
        print("\nStep 2: Checking account balance")
        result = await Runner.run(
            customer_service_agent,
            input=result.to_input_list()
            + [{"content": "Can you check the balance for account 1234?", "role": "user"}],
        )
        print(f"\nResponse: {result.final_output}\n")

        # 3. Ask about loans (should trigger handoff to loan specialist)
        print("\nStep 3: Loan inquiry (should trigger handoff to loan specialist)")
        result = await Runner.run(
            customer_service_agent,
            input=result.to_input_list()
            + [
                {
                    "content": "I'm interested in taking out a mortgage loan. Can you help me understand my options?",
                    "role": "user",
                }
            ],
        )
        print(f"\nResponse: {result.final_output}\n")

        # 4. Ask the loan specialist about payment calculations
        print("\nStep 4: Loan payment calculation")
        result = await Runner.run(
            customer_service_agent,
            input=result.to_input_list()
            + [
                {
                    "content": "If I borrow $300,000 at 4.5% interest for 30 years, what would my monthly payment be?",
                    "role": "user",
                }
            ],
        )
        print(f"\nResponse: {result.final_output}\n")
        
        # 5. Start a new conversation about investments (should trigger handoff to investment specialist)
        print("\nStep 5: Investment inquiry (should trigger handoff to investment specialist)")
        result = await Runner.run(
            customer_service_agent,
            input=[{"content": "I'm interested in investing some money. What options do you recommend?", "role": "user"}],
        )
        print(f"\nResponse: {result.final_output}\n")
        
        # 6. Ask about investment returns
        print("\nStep 6: Investment return calculation")
        result = await Runner.run(
            customer_service_agent,
            input=result.to_input_list()
            + [
                {
                    "content": "If I invest $50,000 with an expected 7% annual return, how much would I have after 10 years?",
                    "role": "user",
                }
            ],
        )
        print(f"\nResponse: {result.final_output}\n")

    print("\n=== Demo Complete ===\n")
    
    # Cleanup service discovery if used
    if hasattr(openai_client, 'service_discovery'):
        try:
            await openai_client.service_discovery.shutdown()
            logger.info("Service discovery shutdown completed")
        except Exception as e:
            logger.error(f"Error during service discovery shutdown: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())