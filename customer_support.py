
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agentspan.agents import (
    Agent,
    AgentRuntime,
    ConversationMemory,
    GuardrailResult,
    Guardrail,
    Position,
    OnFail,
    guardrail,
    tool,
    start,
    EventType,
)

load_dotenv()


# 1. Structured output
class SupportResponse(BaseModel):
    stage: str = Field(
        description="Stage like answered, refunded or rejected"
    )
    successful: bool
    message: str


# 2. Prompt injection protection
@guardrail
def check_prompt(prompt):
    """Block obvious prompt injection attacks."""

    blocked_words = [
        "forget everything",
        "ignore",
        "ignore previous",
        "system prompt",
        "jailbreak",
    ]

    clean = not any(
        phrase in prompt.lower()
        for phrase in blocked_words
    )

    return GuardrailResult(
        passed=clean,
        message="Please ask a different query, this is blocked.",
    )


# 3. Conversation memory
memory = ConversationMemory()
session_id = "customer_session_"


# 4. Mock database tool
@tool
def database_tool(order_id: str):
    """Look up order details in the database by order ID."""

    MOCK_DB = {
        "orders": {
            "1": {"status": "delivered", "total": 10.99},
            "2": {"status": "delivered", "total": 22},
            "3": {"status": "refunded", "total": 19},
        }
    }

    return MOCK_DB["orders"].get(
        order_id,
        {"error": "order not found"},
    )


# 5. Refund tool with human approval
@tool(approval_required=True)
def process_refund(amount: float, order_id: str):
    """Process a refund after human approval."""

    return f"Refunded ${amount:.2f} for order {order_id}"


# 6. Create customer support agent
customer_support_agent = Agent(
    name="customer_support",
    model="google_gemini/gemini-3.8-flash",
    instructions="""
    You are a customer support agent.

    Your responsibilities:
    1. Help customers with order-related questions.
    2. Use database_tool to check order status and details.
    3. Use process_refund when a customer requests a valid refund.
    4. Never process a refund without human approval.
    5. Return responses in the required SupportResponse format.
    """,
    tools=[
        database_tool,
        process_refund,
    ],
    memory=memory,
    output_type=SupportResponse,
    guardrails=[
        Guardrail(
            check_prompt,
            position=Position.INPUT,
            on_fail=OnFail.RAISE,
        )
    ],
)


# 7. Interactive agent execution
def run_interactive(prompt: str):

    with AgentRuntime() as runtime:

        order_id = None
        amount = None

        handle = start(
            customer_support_agent,
            prompt,
            runtime=runtime,
            session_id=session_id,
        )

        stream = handle.stream()

        for event in stream:

            if event.type == EventType.TOOL_CALL and event.args:

                if event.args.get("order_id"):
                    order_id = event.args["order_id"]

                if event.args.get("amount") is not None:
                    amount = event.args["amount"]

            elif (
                event.type == EventType.TOOL_RESULT
                and isinstance(event.result, dict)
            ):

                if event.result.get("total") is not None:
                    amount = event.result["total"]

            elif event.type == EventType.WAITING:

                if order_id is None or amount is None:
                    handle.reject("Missing order or refund amount")
                    continue

                print(
                    f"\nApproval required: refund "
                    f"${amount:.2f} for order {order_id}"
                )

                decision = input("Approve? (y/n): ").lower().strip()

                if decision == "y":
                    handle.approve()
                else:
                    handle.reject("User rejected")

        result = stream.get_result()

        output = result.output.get("result")

        print(f"\n{output}\n")

        result.print_result()


# 8. Main loop
if __name__ == "__main__":

    while True:

        prompt = input("You: ").strip()

        if prompt.lower() == "q":
            break

        if not prompt:
            continue

        try:
            run_interactive(prompt)

        except Exception as error:
            print(f"Error: {error}")
