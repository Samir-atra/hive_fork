import unittest

from examples.templates.meeting_notes_agent.agent import default_agent


class TestMeetingNotesAgent(unittest.TestCase):
    def test_agent_validation(self):
        """Test that the meeting notes agent graph configuration is valid."""
        validation_result = default_agent.validate()
        self.assertTrue(
            validation_result["valid"],
            f"Agent validation failed: {validation_result.get('errors')}",
        )


if __name__ == "__main__":
    unittest.main()
