"""Registry for mapping natural language intents to agent templates."""

import re


class AgentTemplateRegistry:
    """Registry for agent templates with intent matching capabilities.

    Provides an Intent-to-Template Matcher with Semantic Keyword Matching
    for Agent Selection from registered agent templates.
    """

    def __init__(self):
        self.templates = {}

    def register(self, name: str, keywords: list[str], regex: list[str]) -> None:
        """Register a new template with keywords and regex patterns for intent matching.

        Args:
            name: The name of the template.
            keywords: List of single-word keywords.
            regex: List of regex patterns.
        """
        self.templates[name] = {"keywords": keywords, "regex": regex}

    @classmethod
    def register_defaults(cls) -> "AgentTemplateRegistry":
        """Instantiate a registry and pre-register the 11 common agent templates.

        Returns:
            An instance of AgentTemplateRegistry populated with default templates.
        """
        registry = cls()

        registry.register(
            "competitive_intel_agent",
            ["competitor", "market", "intelligence", "analysis", "compare"],
            [r"(?i)\bcompetitor\s*analysis\b", r"(?i)\bmarket\s*research\b"],
        )
        registry.register(
            "deep_research_agent",
            ["research", "investigate", "study", "report", "findings"],
            [r"(?i)\bdeep\s*research\b", r"(?i)\binvestigate\s*thoroughly\b"],
        )
        registry.register(
            "email_inbox_management",
            ["inbox", "email", "manage", "organize", "sort", "clean"],
            [r"(?i)\binbox\s*management\b", r"(?i)\borganize\s*emails?\b"],
        )
        registry.register(
            "email_reply_agent",
            ["reply", "respond", "email", "draft", "response"],
            [r"(?i)\breply\s*to\s*emails?\b", r"(?i)\bdraft\s*response\b"],
        )
        registry.register(
            "job_hunter",
            ["job", "resume", "apply", "hunter", "career", "search"],
            [r"(?i)\bjob\s*search\b", r"(?i)\bfind\s*jobs?\b"],
        )
        registry.register(
            "local_business_extractor",
            ["local", "business", "extract", "scrape", "maps", "contact"],
            [r"(?i)\blocal\s*businesses\b", r"(?i)\bgoogle\s*maps\b"],
        )
        registry.register(
            "meeting_scheduler",
            ["meeting", "schedule", "calendar", "invite", "book"],
            [r"(?i)\bschedule\s*meetings?\b", r"(?i)\bbook\s*calendar\b"],
        )
        registry.register(
            "sdr_agent",
            ["sales", "leads", "sdr", "outreach", "prospect"],
            [r"(?i)\bsales\s*outreach\b", r"(?i)\blead\s*generation\b"],
        )
        registry.register(
            "tech_news_reporter",
            ["tech", "news", "technology", "reporter", "latest"],
            [r"(?i)\btech(nology)?\s*news\b", r"(?i)\blatest\s*tech\b"],
        )
        registry.register(
            "twitter_news_agent",
            ["twitter", "news", "tweet", "social", "trend"],
            [r"(?i)\btwitter\s*trends?\b", r"(?i)\bsocial\s*media\s*news\b"],
        )
        registry.register(
            "vulnerability_assessment",
            ["vulnerability", "security", "assessment", "audit", "scan"],
            [r"(?i)\bsecurity\s*scan\b", r"(?i)\bvulnerability\s*assessment\b"],
        )

        return registry

    def match_intent(self, intent: str) -> list[tuple[str, float]]:
        """Matches a user intent string to templates and returns a ranked list.

        Args:
            intent: The natural language intent from the user.

        Returns:
            A list of tuples containing the template name and its matching score,
            sorted in descending order by score.
        """
        if not intent or not intent.strip():
            return [(name, 0.0) for name in self.templates]

        intent_lower = intent.lower()
        words = set(re.findall(r"\b\w+\b", intent_lower))

        results = []

        for name, data in self.templates.items():
            score = 0.0

            # Keyword matching (1.0 point per matching keyword)
            for kw in data["keywords"]:
                if kw.lower() in words:
                    score += 1.0

            # Regex matching (2.0 points per matching regex)
            for pattern in data["regex"]:
                if re.search(pattern, intent_lower):
                    score += 2.0

            results.append((name, score))

        # Sort by score descending, then alphabetically by name to ensure stable sorting
        results.sort(key=lambda x: (-x[1], x[0]))

        return results
