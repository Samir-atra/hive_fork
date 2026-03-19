# Analytics Agent

A goal-driven conversational analytics agent that processes uploaded data (CSV/structured) or queries datasets via natural language. It performs automated EDA, statistical summaries, basic visualizations, and extracts insights.

## Capabilities

- **Automated EDA**: Reads a CSV file and generates a statistical summary including descriptive statistics, missing values count, and structural info using pandas.
- **Visualizations**: Generates and saves plots (bar, scatter, hist) using seaborn and matplotlib.
- **Conversational Insights**: Can be queried via natural language to extract deeper insights.

## Setup

Ensure dependencies are installed:
```bash
pip install pandas matplotlib seaborn
```

Run the agent via the Hive framework:
```bash
hive run analytics_agent
```
