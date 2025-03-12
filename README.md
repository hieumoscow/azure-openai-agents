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

## Sample Conversation Flow

1. User asks a general banking question
2. If the question is about loans, the conversation is handed off to the Loan Specialist
3. The Loan Specialist can calculate loan payments and provide detailed loan information
4. If the question is about investments, the conversation is handed off to the Investment Specialist

## License

This project is for demonstration purposes only.
