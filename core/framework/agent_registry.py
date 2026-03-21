import re


class AgentTemplateRegistry:
    """Registry for agent templates with intent matching capabilities.

    Provides an Intent-to-Template Matcher with Semantic Keyword Matching
    for Agent Selection from the 11 pre-registered common agent templates.
    """

    def __init__(self):
        # 11 pre-registered templates with their matching keywords and regex patterns
        self.templates = {
            "competitive_intel_agent": {
                "keywords": ["competitor", "market", "intelligence", "analysis", "compare"],
                "regex": [r"(?i)\bcompetitor\s*analysis\b", r"(?i)\bmarket\s*research\b"],
            },
            "deep_research_agent": {
                "keywords": ["research", "investigate", "study", "report", "findings"],
                "regex": [r"(?i)\bdeep\s*research\b", r"(?i)\binvestigate\s*thoroughly\b"],
            },
            "email_inbox_management": {
                "keywords": ["inbox", "email", "manage", "organize", "sort", "clean"],
                "regex": [r"(?i)\binbox\s*management\b", r"(?i)\borganize\s*emails?\b"],
            },
            "email_reply_agent": {
                "keywords": ["reply", "respond", "email", "draft", "response"],
                "regex": [r"(?i)\breply\s*to\s*emails?\b", r"(?i)\bdraft\s*response\b"],
            },
            "job_hunter": {
                "keywords": ["job", "resume", "apply", "hunter", "career", "search"],
                "regex": [r"(?i)\bjob\s*search\b", r"(?i)\bfind\s*jobs?\b"],
            },
            "local_business_extractor": {
                "keywords": ["local", "business", "extract", "scrape", "maps", "contact"],
                "regex": [r"(?i)\blocal\s*businesses\b", r"(?i)\bgoogle\s*maps\b"],
            },
            "meeting_scheduler": {
                "keywords": ["meeting", "schedule", "calendar", "invite", "book"],
                "regex": [r"(?i)\bschedule\s*meetings?\b", r"(?i)\bbook\s*calendar\b"],
            },
            "sdr_agent": {
                "keywords": ["sales", "leads", "sdr", "outreach", "prospect"],
                "regex": [r"(?i)\bsales\s*outreach\b", r"(?i)\blead\s*generation\b"],
            },
            "tech_news_reporter": {
                "keywords": ["tech", "news", "technology", "reporter", "latest"],
                "regex": [r"(?i)\btech(nology)?\s*news\b", r"(?i)\blatest\s*tech\b"],
            },
            "twitter_news_agent": {
                "keywords": ["twitter", "news", "tweet", "social", "trend"],
                "regex": [r"(?i)\btwitter\s*trends?\b", r"(?i)\bsocial\s*media\s*news\b"],
            },
            "vulnerability_assessment": {
                "keywords": ["vulnerability", "security", "assessment", "audit", "scan"],
                "regex": [r"(?i)\bsecurity\s*scan\b", r"(?i)\bvulnerability\s*assessment\b"],
            },
        }

    def match_intent(self, intent: str) -> list[tuple[str, float]]:
        """Matches a user intent string to templates and returns a ranked list.

        Args:
            intent: The natural language intent from the user.

        Returns:
            A list of tuples containing the template name and its matching score,
            sorted in descending order by score.
        """
        if not intent or not intent.strip():
            return [(name, 0.0) for name in self.templates.keys()]

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
