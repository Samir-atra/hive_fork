"""HR Onboarding Orchestrator - Entry point for CLI execution."""

from .agent import default_agent

if __name__ == "__main__":
    import asyncio

    async def main():
        result = await default_agent.run(
            {
                "candidate_name": "John Doe",
                "candidate_email": "john.doe@example.com",
                "position": "Software Engineer",
                "department": "Engineering",
                "start_date": "2024-02-01",
                "envelope_id": "abc123",
            }
        )
        print(f"Result: {result}")

    asyncio.run(main())
