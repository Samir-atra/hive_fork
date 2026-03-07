"""Runtime configuration for Revenue Recovery Agent."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Revenue Recovery Agent"
    version: str = "1.0.0"
    description: str = (
        "E-commerce revenue recovery agent that monitors abandoned carts, "
        "failed payments, and lapsed buyers, then generates and sends personalized "
        "win-back sequences with human-in-the-loop approval."
    )
    intro_message: str = (
        "Hi! I'm your revenue recovery assistant. I help you recover lost revenue "
        "from abandoned carts, failed payments, and lapsed buyers. I'll analyze your "
        "Shopify store data, segment customers, and create personalized recovery emails "
        "for your approval before sending. What recovery campaign would you like to run?"
    )


metadata = AgentMetadata()
