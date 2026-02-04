# Greenhouse Tool

Greenhouse Harvest API integration for recruiting automation. Enables agents to manage job postings, candidates, and applications directly through the Greenhouse ATS (Applicant Tracking System).

## Use Cases

- **Job Management**: List and view job postings with filters (status, department, office)
- **Candidate Pipeline**: Browse candidates, view details, and add new candidates to jobs
- **Application Tracking**: Monitor applications for specific jobs with status filtering
- **Recruiting Automation**: Build workflows that automate candidate sourcing and tracking

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GREENHOUSE_API_KEY` | Yes | Greenhouse Harvest API Key |

### Obtaining an API Key

1. Log in to your Greenhouse account at https://app.greenhouse.io
2. Navigate to **Configure > Dev Center > API Credential Management**
3. Click **Create New API Key**
4. Select **Harvest API** as the API type
5. Give the key a descriptive name (e.g., 'Aden Integration')
6. Select the appropriate permissions:
   - Jobs: Read access (for listing/viewing jobs)
   - Candidates: Read/Write access (for listing/adding candidates)
   - Applications: Read access (for listing applications)
7. Click **Create** and copy the generated API key
8. Set the environment variable:
   ```bash
   export GREENHOUSE_API_KEY=your_key
   ```

## Tools

### `greenhouse_list_jobs`

List job postings with optional filters.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `limit` | int | 50 | Maximum number of jobs to return |
| `status` | str | "open" | Filter by status: `open`, `closed`, `draft` |
| `department_id` | int | None | Filter by department ID |
| `office_id` | int | None | Filter by office/location ID |

**Example:**
```python
# List all open jobs
greenhouse_list_jobs()

# List closed jobs in a specific department
greenhouse_list_jobs(status="closed", department_id=12345)
```

---

### `greenhouse_get_job`

Get detailed information about a specific job.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `job_id` | int | Yes | The ID of the job to retrieve |

**Example:**
```python
greenhouse_get_job(job_id=12345)
```

---

### `greenhouse_list_candidates`

List candidates with optional filters.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `limit` | int | 50 | Maximum number of candidates to return |
| `job_id` | int | None | Filter by job application |
| `stage` | str | None | Filter by current stage name (e.g., 'Initial Screen') |
| `created_after` | str | None | ISO 8601 date string (e.g., '2023-01-01T00:00:00Z') |
| `updated_after` | str | None | ISO 8601 date string |

**Example:**
```python
# List candidates for a specific job
greenhouse_list_candidates(job_id=12345)

# List recently created candidates
greenhouse_list_candidates(created_after="2024-01-01T00:00:00Z", limit=100)
```

---

### `greenhouse_get_candidate`

Get full candidate details including applications and activity.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `candidate_id` | int | Yes | The ID of the candidate |

**Example:**
```python
greenhouse_get_candidate(candidate_id=67890)
```

---

### `greenhouse_add_candidate`

Submit a new candidate to the pipeline for a specific job.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `first_name` | str | Yes | Candidate's first name |
| `last_name` | str | Yes | Candidate's last name |
| `email` | str | Yes | Candidate's primary email |
| `job_id` | int | Yes | ID of the job to apply to |
| `phone` | str | No | Optional phone number |
| `source` | str | No | Source of the candidate (e.g., 'LinkedIn', 'Referral') |
| `resume_url` | str | No | URL to resume file (PDF/Doc) |
| `notes` | str | No | Initial notes to add to candidate profile |

**Example:**
```python
greenhouse_add_candidate(
    first_name="Jane",
    last_name="Doe",
    email="jane.doe@example.com",
    job_id=12345,
    phone="+1-555-0100",
    source="LinkedIn",
    notes="Strong Python background"
)
```

---

### `greenhouse_list_applications`

List applications for a specific job.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `job_id` | int | Required | The job to list applications for |
| `limit` | int | 50 | Maximum applications to return |
| `status` | str | None | Filter by status: `active`, `rejected`, `hired` |

**Example:**
```python
# List all applications for a job
greenhouse_list_applications(job_id=12345)

# List only hired candidates
greenhouse_list_applications(job_id=12345, status="hired")
```

## Error Handling

All tools return error dictionaries instead of raising exceptions, following the BUILDING_TOOLS.md pattern:

```python
# Success response
{"id": 123, "title": "Software Engineer", ...}

# Error responses
{"error": "Authentication failed: Invalid Greenhouse API key"}
{"error": "Access denied: Check API permissions or use HTTPS"}
{"error": "Resource not found", "status": 404}
{"error": "Rate limit exceeded", "status": 429}
{"error": "Request timed out"}
{"error": "Network error: <details>"}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Authentication failed | Invalid or expired API key | Regenerate API key in Greenhouse |
| Access denied | Insufficient permissions | Check API key permissions in Dev Center |
| Resource not found | Invalid ID provided | Verify the job/candidate ID exists |
| Rate limit exceeded | Too many requests | Implement backoff, reduce request frequency |

## API Reference

- [Greenhouse Harvest API Documentation](https://developers.greenhouse.io/harvest.html)
- [Authentication Guide](https://developers.greenhouse.io/harvest.html#authentication)
- [Rate Limits](https://developers.greenhouse.io/harvest.html#throttling)
