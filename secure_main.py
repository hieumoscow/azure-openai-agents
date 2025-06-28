"""
Secure Banking Agents Demo

This is the secure version of the banking agents demo that implements
authentication, authorization, and other security controls to meet
compliance control C9262 requirements.
"""

from __future__ import annotations
import logging
import os
import asyncio
from dotenv import load_dotenv

from openai import AsyncAzureOpenAI
from agents import Agent, HandoffInputData, Runner, handoff, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key, add_trace_processor
from agents.tracing.processors import ConsoleSpanExporter, BatchTraceProcessor
from agents.extensions import handoff_filters
import logfire

# Import security modules
from auth import validate_configuration, auth_manager, UserRole, security_logger
from secure_banking import (
    secure_check_account_balance,
    secure_calculate_loan_payment,
    secure_calculate_investment_return,
    secure_admin_get_all_accounts
)

# Load environment variables
load_dotenv()

# Validate security configuration on startup
validate_configuration()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Azure OpenAI client configuration
azure_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

azure_apim_openai_client = AsyncAzureOpenAI(
    default_headers={"Ocp-Apim-Subscription-Key": os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY")},
    api_key=os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY"),
    api_version=os.getenv("AZURE_APIM_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_APIM_OPENAI_ENDPOINT")
)

openai_client = azure_openai_client
set_default_openai_client(openai_client)

# OpenTelemetry configuration
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://0.0.0.0:4318/v1/traces"

# Set the API key for trace export
set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
set_tracing_disabled(False)

# Configure logfire
logfire.configure(
    service_name='secure-banking-agent-service',
    send_to_logfire=False,
    distributed_tracing=True
)
logfire.instrument_openai_agents()


def secure_banking_handoff_message_filter(handoff_message_data: HandoffInputData) -> HandoffInputData:
    """
    Secure handoff message filter that preserves security context
    """
    # Remove any tool-related messages from the message history
    handoff_message_data = handoff_filters.remove_all_tools(handoff_message_data)
    
    # Keep the full conversation history for the banking specialist
    return handoff_message_data


# Secure Banking-themed agents with authentication requirements
secure_general_agent = Agent(
    name="Secure Banking Assistant",
    instructions="""You are a secure banking assistant. You help customers with account inquiries.
    
    IMPORTANT SECURITY REQUIREMENTS:
    - Always request the user's API key for authentication
    - Only access accounts the user is authorized for
    - Be professional and security-conscious
    - Never share account information without proper authentication
    
    When a user asks to check their balance, ask for their account ID and API key.
    The API key is required for security and compliance.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[secure_check_account_balance],
)

secure_loan_specialist_agent = Agent(
    name="Secure Loan Specialist",
    instructions="""You are a secure loan specialist at a bank.
    
    IMPORTANT SECURITY REQUIREMENTS:
    - Always request the user's API key for authentication
    - Only authorized users (admin, teller) can use loan calculation tools
    - Be professional and explain loan options clearly
    - Follow all banking security protocols
    
    You can help calculate loan payments and provide loan information.
    Authentication is required for all loan calculations.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[secure_calculate_loan_payment],
)

secure_investment_specialist_agent = Agent(
    name="Secure Investment Specialist",
    instructions="""You are a secure investment specialist at a bank.
    
    IMPORTANT SECURITY REQUIREMENTS:
    - Always request the user's API key for authentication
    - Only authorized users (admin, teller) can use investment calculation tools
    - Be professional and explain investment concepts clearly
    - Consider risk tolerance and financial goals
    
    You can help calculate investment returns and provide investment guidance.
    Authentication is required for all investment calculations.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[secure_calculate_investment_return],
)

secure_customer_service_agent = Agent(
    name="Secure Customer Service Agent",
    instructions="""You are a secure customer service agent at a bank.
    
    IMPORTANT SECURITY REQUIREMENTS:
    - Always request the user's API key for authentication before proceeding
    - Verify user identity before providing any banking services
    - Direct users to specialists based on their needs and authorization level
    - Follow all security and compliance protocols
    
    Help customers with general inquiries and direct them to specialists when needed:
    - For loans or mortgages: handoff to the Loan Specialist
    - For investments or portfolio management: handoff to the Investment Specialist
    
    Always prioritize security and customer service.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    handoffs=[
        handoff(secure_loan_specialist_agent, input_filter=secure_banking_handoff_message_filter),
        handoff(secure_investment_specialist_agent, input_filter=secure_banking_handoff_message_filter),
    ],
    tools=[secure_check_account_balance],
)

# Admin agent with elevated privileges
secure_admin_agent = Agent(
    name="Secure Banking Administrator",
    instructions="""You are a secure banking administrator with elevated privileges.
    
    IMPORTANT SECURITY REQUIREMENTS:
    - Always request the admin API key for authentication
    - Only admin users can access administrative functions
    - Log all administrative actions
    - Be extremely careful with sensitive data
    
    You have access to all banking functions including administrative tools.
    Use your privileges responsibly and in compliance with banking regulations.""",
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[
        secure_check_account_balance,
        secure_calculate_loan_payment,
        secure_calculate_investment_return,
        secure_admin_get_all_accounts
    ],
)


async def demonstrate_security_features():
    """Demonstrate the security features of the banking system"""
    
    with trace(workflow_name="Secure Banking Demo"):
        print("\n" + "="*60)
        print("SECURE BANKING AGENTS DEMO")
        print("Security Compliance Control C9262 Implementation")
        print("="*60 + "\n")
        
        # Get API keys from environment (in production, these would come from secure user input)
        admin_key = os.getenv("ADMIN_API_KEY", "admin-key-12345")
        teller_key = os.getenv("TELLER_API_KEY", "teller-key-12345")
        customer_key = os.getenv("CUSTOMER_API_KEY", "customer-key-12345")
        
        print("Available Users and API Keys:")
        print(f"- Admin API Key: {admin_key}")
        print(f"- Teller API Key: {teller_key}")
        print(f"- Customer API Key: {customer_key}")
        print()
        
        # Demonstrate customer access
        print("1. CUSTOMER ACCESS DEMONSTRATION")
        print("-" * 40)
        
        try:
            print("Customer checking their account balance (account 1234)...")
            result = await Runner.run(
                secure_general_agent,
                input=f"Hi, I'd like to check my account balance for account 1234. My API key is {customer_key}."
            )
            print(f"Result: {result.final_output}\n")
        except Exception as e:
            print(f"Error: {e}\n")
        
        # Demonstrate unauthorized access attempt
        print("2. UNAUTHORIZED ACCESS ATTEMPT")
        print("-" * 40)
        
        try:
            print("Customer attempting to access unauthorized account (5678)...")
            result = await Runner.run(
                secure_general_agent,
                input=f"I want to check account 5678 balance. My API key is {customer_key}."
            )
            print(f"Result: {result.final_output}\n")
        except Exception as e:
            print(f"Security Error (Expected): {e}\n")
        
        # Demonstrate teller operations
        print("3. TELLER OPERATIONS DEMONSTRATION")
        print("-" * 40)
        
        try:
            print("Teller calculating loan payment...")
            result = await Runner.run(
                secure_loan_specialist_agent,
                input=f"Calculate monthly payment for a $300,000 loan at 4.5% interest for 30 years. API key: {teller_key}."
            )
            print(f"Result: {result.final_output}\n")
        except Exception as e:
            print(f"Error: {e}\n")
        
        # Demonstrate customer trying to access teller functions
        print("4. ROLE-BASED ACCESS CONTROL TEST")
        print("-" * 40)
        
        try:
            print("Customer attempting to use teller-only loan calculation...")
            result = await Runner.run(
                secure_loan_specialist_agent,
                input=f"Calculate loan payment for $200,000 at 3.5% for 25 years. API key: {customer_key}."
            )
            print(f"Result: {result.final_output}\n")
        except Exception as e:
            print(f"Authorization Error (Expected): {e}\n")
        
        # Demonstrate admin access
        print("5. ADMINISTRATOR ACCESS DEMONSTRATION")
        print("-" * 40)
        
        try:
            print("Admin accessing all account information...")
            result = await Runner.run(
                secure_admin_agent,
                input=f"Show me all account information for audit purposes. API key: {admin_key}."
            )
            print(f"Result: {result.final_output}\n")
        except Exception as e:
            print(f"Error: {e}\n")
        
        # Demonstrate input validation
        print("6. INPUT VALIDATION DEMONSTRATION")
        print("-" * 40)
        
        try:
            print("Testing invalid account ID format...")
            result = await Runner.run(
                secure_general_agent,
                input=f"Check balance for account 'invalid-account-id'. API key: {customer_key}."
            )
            print(f"Result: {result.final_output}\n")
        except Exception as e:
            print(f"Validation Error (Expected): {e}\n")
        
        print("SECURITY DEMONSTRATION COMPLETE")
        print("="*60)
        print("Security Features Demonstrated:")
        print("✓ API Key Authentication")
        print("✓ Role-Based Access Control")
        print("✓ Account-Level Authorization")
        print("✓ Input Validation")
        print("✓ Security Audit Logging")
        print("✓ Error Handling")
        print("="*60 + "\n")


async def interactive_secure_demo():
    """Interactive demonstration allowing user to test security features"""
    
    print("\n" + "="*60)
    print("INTERACTIVE SECURE BANKING DEMO")
    print("="*60 + "\n")
    
    print("Available API Keys:")
    print(f"- Admin: {os.getenv('ADMIN_API_KEY', 'admin-key-12345')}")
    print(f"- Teller: {os.getenv('TELLER_API_KEY', 'teller-key-12345')}")
    print(f"- Customer: {os.getenv('CUSTOMER_API_KEY', 'customer-key-12345')}")
    print()
    
    print("Available Agents:")
    print("1. Secure Customer Service Agent")
    print("2. Secure Banking Assistant")
    print("3. Secure Loan Specialist")
    print("4. Secure Investment Specialist")
    print("5. Secure Admin Agent")
    print()
    
    agents = {
        "1": secure_customer_service_agent,
        "2": secure_general_agent,
        "3": secure_loan_specialist_agent,
        "4": secure_investment_specialist_agent,
        "5": secure_admin_agent
    }
    
    while True:
        try:
            agent_choice = input("Select agent (1-5) or 'q' to quit: ").strip()
            
            if agent_choice.lower() == 'q':
                break
            
            if agent_choice not in agents:
                print("Invalid choice. Please select 1-5 or 'q'.")
                continue
            
            selected_agent = agents[agent_choice]
            print(f"\nSelected: {selected_agent.name}")
            
            user_input = input("Enter your message (include API key for authentication): ")
            
            if not user_input.strip():
                print("Please enter a message.")
                continue
            
            print("\nProcessing...")
            
            result = await Runner.run(selected_agent, input=user_input)
            print(f"\nAgent Response: {result.final_output}\n")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")
            print("-" * 60)


async def main():
    """Main function with options for different demo modes"""
    
    print("Secure Banking Agents Demo")
    print("Compliance Control C9262 Implementation\n")
    
    print("Select demo mode:")
    print("1. Automated Security Features Demo")
    print("2. Interactive Demo")
    print("3. Both")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice in ["1", "3"]:
        await demonstrate_security_features()
    
    if choice in ["2", "3"]:
        await interactive_secure_demo()
    
    if choice not in ["1", "2", "3"]:
        print("Invalid choice. Running automated demo...")
        await demonstrate_security_features()


if __name__ == "__main__":
    asyncio.run(main())