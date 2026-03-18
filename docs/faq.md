<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What LLM providers does Hive support?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Hive supports 100+ LLM providers through LiteLLM integration, including OpenAI (GPT-4, GPT-4o), Anthropic (Claude models), Google Gemini, DeepSeek, Mistral, Groq, and many more. Simply set the appropriate API key environment variable and specify the model name. We recommend using Claude, GLM and Gemini as they have the best performance."
      }
    },
    {
      "@type": "Question",
      "name": "Can I use Hive with local AI models like Ollama?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes! Hive supports local models through LiteLLM. Simply use the model name format ollama/model-name (e.g., ollama/llama3, ollama/mistral) and ensure Ollama is running locally."
      }
    },
    {
      "@type": "Question",
      "name": "What makes Hive different from other agent frameworks?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Hive generates your entire agent system from natural language goals using a coding agent—you don't hardcode workflows or manually define graphs. When agents fail, the framework automatically captures failure data, evolves the agent graph, and redeploys. This self-improving loop is unique to Aden."
      }
    },
    {
      "@type": "Question",
      "name": "Is Hive open-source?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, Hive is fully open-source under the Apache License 2.0. We actively encourage community contributions and collaboration."
      }
    },
    {
      "@type": "Question",
      "name": "Does Hive support human-in-the-loop workflows?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, Hive fully supports human-in-the-loop workflows through intervention nodes that pause execution for human input. These include configurable timeouts and escalation policies, allowing seamless collaboration between human experts and AI agents."
      }
    },
    {
      "@type": "Question",
      "name": "What programming languages does Hive support?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The Hive framework is built in Python. A JavaScript/TypeScript SDK is on the roadmap."
      }
    },
    {
      "@type": "Question",
      "name": "Can Hive agents interact with external tools and APIs?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. Aden's SDK-wrapped nodes provide built-in tool access, and the framework supports flexible tool ecosystems. Agents can integrate with external APIs, databases, and services through the node architecture."
      }
    },
    {
      "@type": "Question",
      "name": "How does cost control work in Hive?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Hive provides granular budget controls including spending limits, throttles, and automatic model degradation policies. You can set budgets at the team, agent, or workflow level, with real-time cost tracking and alerts."
      }
    },
    {
      "@type": "Question",
      "name": "Where can I find examples and documentation?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Visit docs.adenhq.com for complete guides, API reference, and getting started tutorials. The repository also includes documentation in the docs/ folder and a comprehensive developer guide."
      }
    },
    {
      "@type": "Question",
      "name": "How can I contribute to Aden?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Contributions are welcome! Fork the repository, create your feature branch, implement your changes, and submit a pull request. See CONTRIBUTING.md for detailed guidelines."
      }
    }
  ]
}
</script>

# Frequently Asked Questions (FAQ)

**Q: What LLM providers does Hive support?**

Hive supports 100+ LLM providers through LiteLLM integration, including OpenAI (GPT-4, GPT-4o), Anthropic (Claude models), Google Gemini, DeepSeek, Mistral, Groq, and many more. Simply set the appropriate API key environment variable and specify the model name. We recommend using Claude, GLM and Gemini as they have the best performance.

**Q: Can I use Hive with local AI models like Ollama?**

Yes! Hive supports local models through LiteLLM. Simply use the model name format `ollama/model-name` (e.g., `ollama/llama3`, `ollama/mistral`) and ensure Ollama is running locally.

**Q: What makes Hive different from other agent frameworks?**

Hive generates your entire agent system from natural language goals using a coding agent—you don't hardcode workflows or manually define graphs. When agents fail, the framework automatically captures failure data, [evolves the agent graph](key_concepts/evolution.md), and redeploys. This self-improving loop is unique to Aden.

**Q: Is Hive open-source?**

Yes, Hive is fully open-source under the Apache License 2.0. We actively encourage community contributions and collaboration.

**Q: Does Hive support human-in-the-loop workflows?**

Yes, Hive fully supports [human-in-the-loop](key_concepts/graph.md#human-in-the-loop) workflows through intervention nodes that pause execution for human input. These include configurable timeouts and escalation policies, allowing seamless collaboration between human experts and AI agents.

**Q: What programming languages does Hive support?**

The Hive framework is built in Python. A JavaScript/TypeScript SDK is on the roadmap.

**Q: Can Hive agents interact with external tools and APIs?**

Yes. Aden's SDK-wrapped nodes provide built-in tool access, and the framework supports flexible tool ecosystems. Agents can integrate with external APIs, databases, and services through the node architecture.

**Q: How does cost control work in Hive?**

Hive provides granular budget controls including spending limits, throttles, and automatic model degradation policies. You can set budgets at the team, agent, or workflow level, with real-time cost tracking and alerts.

**Q: Where can I find examples and documentation?**

Visit [docs.adenhq.com](https://docs.adenhq.com/) for complete guides, API reference, and getting started tutorials. The repository also includes documentation in the `docs/` folder and a comprehensive [developer guide](developer-guide.md).

**Q: How can I contribute to Aden?**

Contributions are welcome! Fork the repository, create your feature branch, implement your changes, and submit a pull request. See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.
