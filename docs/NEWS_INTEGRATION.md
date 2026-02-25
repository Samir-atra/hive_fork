# News API Integration ([Issue #3060](https://github.com/Samir-atra/hive_fork/issues/3060))

The News API integration enables Hive agents to monitor real-time news, track company mentions, and perform sentiment analysis on market trends. It leverages **NewsData.io** as the primary provider and **Finlight.me** for optional sentiment analysis and fallback.

## 🔑 Authentication

Add the following credentials to your `.env` file:

```bash
# Primary news provider (https://newsdata.io/)
NEWSDATA_API_KEY=your_newsdata_api_key

# Optional: Sentiment analysis (https://finlight.me/)
FINLIGHT_API_KEY=your_finlight_api_key
```

## 🛠 Tools Reference

### 1. `news_search`
General purpose news search with advanced filtering.
- **Parameters**: `query`, `from_date`, `to_date`, `language`, `limit`, `sources`, `category`, `country`.
- **Note**: Automatically falls back to Finlight if NewsData fails and `FINLIGHT_API_KEY` is present.

### 2. `news_headlines`
Retrieve the latest top headlines by category or region.
- **Parameters**: `category` (business, tech, finance, etc.), `country`, `limit`.

### 3. `news_by_company`
Quick utility to find mentions of a specific company.
- **Parameters**: `company_name`, `days_back` (default: 7), `limit`, `language`.

### 4. `news_sentiment`
Get news articles paired with sentiment scores (Positive/Negative/Neutral).
- **Required**: `FINLIGHT_API_KEY`.
- **Parameters**: `query`, `from_date`, `to_date`.

## 🤖 Usage Examples

### Meeting Preparation Agent
An agent can gather recent news about a prospect before a meeting:
```python
# Agent logic (pseudo)
news = news_by_company(company_name="Acme Corp", days_back=3)
brief = summarize(news)
print(f"Pre-meeting brief for Acme Corp: {brief}")
```

### Market Intelligence Agent
Track trigger events like funding or expansions:
```python
# Agent logic (pseudo)
funding_news = news_search(query="Series B funding AND fintech", limit=5)
# ... process and notify
```

## 🧪 Error Handling
- **401 (Unauthorized)**: Check if your API key is valid.
- **429 (Rate Limit)**: NewsData Free Tier allows 30 requests per 15 minutes.
- **422 (Validation Error)**: Ensure dates are in `YYYY-MM-DD` format and country codes are ISO alpha-2.

## ⚙️ Provider Comparison

| Feature | NewsData.io (Primary) | Finlight.me (Sentiment) |
| :--- | :--- | :--- |
| **Free Tier** | 200 credits/day | 5K-10K req/mo |
| **Delay** | 12-hour delay (Free) | Near real-time |
| **Sentiment** | No | Yes |
| **Category Filter**| Excellent | Basic |
