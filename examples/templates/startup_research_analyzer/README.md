# Startup Research Analyzer

A template agent designed to perform comprehensive research on startups and businesses.
It extracts what the company does, funding stage, competitors, risks, market size, tech stack,
and provides a short investor-style summary.

## Usage

Run the agent using the following command:

### Linux / Mac
```bash
PYTHONPATH=core:examples/templates python -m startup_research_analyzer run --mock --topic "Stripe"
```

### Windows
```powershell
$env:PYTHONPATH="core;examples\templates"
python -m startup_research_analyzer run --mock --topic "Stripe"
```

## Options

- `-t, --topic`: The startup name or website URL to analyze (required).
- `--mock`: Run without calling real LLM APIs (simulated execution).
- `--help`: Show all available options.
