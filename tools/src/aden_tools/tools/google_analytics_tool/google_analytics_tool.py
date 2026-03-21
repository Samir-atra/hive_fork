"""
Google Analytics Tool - Query GA4 website traffic and marketing performance data.

Provides read-only access to Google Analytics 4 via the Data API v1.

Supports:
- Service account authentication (GOOGLE_APPLICATION_CREDENTIALS)
- Credential store via CredentialStoreAdapter

API Reference: https://developers.google.com/analytics/devguides/reporting/data/v1
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    FilterExpressionList,
    Metric,
    MinuteRange,
    OrderBy,
    RunRealtimeReportRequest,
    RunReportRequest,
)
from google.oauth2.service_account import Credentials

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

logger = logging.getLogger(__name__)


class _GAClient:
    """Internal client wrapping Google Analytics 4 Data API v1beta calls."""

    def __init__(self, credentials_path: str):
        self._credentials_path = credentials_path
        creds = Credentials.from_service_account_file(credentials_path)
        self._client = BetaAnalyticsDataClient(credentials=creds)
        self._admin_client = AnalyticsAdminServiceClient(credentials=creds)

    def _parse_filter_expression(self, filter_dict: dict) -> FilterExpression | None:
        """Convert a plain dict into a GA4 FilterExpression."""
        if not filter_dict:
            return None

        if "andGroup" in filter_dict:
            return FilterExpression(
                and_group=FilterExpressionList(
                    expressions=[
                        self._parse_filter_expression(e) for e in filter_dict["andGroup"] if e
                    ]
                )
            )
        if "orGroup" in filter_dict:
            return FilterExpression(
                or_group=FilterExpressionList(
                    expressions=[
                        self._parse_filter_expression(e) for e in filter_dict["orGroup"] if e
                    ]
                )
            )
        if "notExpression" in filter_dict:
            expr = self._parse_filter_expression(filter_dict["notExpression"])
            if expr:
                return FilterExpression(not_expression=expr)
            return None

        # Build individual filter
        f = Filter(field_name=filter_dict.get("field", ""))

        if "inList" in filter_dict:
            f.in_list_filter = Filter.InListFilter(values=[str(v) for v in filter_dict["inList"]])
        elif "op" in filter_dict:
            # Numeric filter
            from google.analytics.data_v1beta.types import NumericValue

            op_str = str(filter_dict["op"]).upper()

            # Use getattr with a fallback to OPERATION_UNSPECIFIED
            try:
                operation = getattr(Filter.NumericFilter.Operation, op_str)
            except AttributeError:
                # If invalid operation string is passed, try mapping common names like 'gt'
                op_map = {
                    "EQUAL": Filter.NumericFilter.Operation.EQUAL,
                    "LESS_THAN": Filter.NumericFilter.Operation.LESS_THAN,
                    "LESS_THAN_OR_EQUAL": Filter.NumericFilter.Operation.LESS_THAN_OR_EQUAL,
                    "GREATER_THAN": Filter.NumericFilter.Operation.GREATER_THAN,
                    "GREATER_THAN_OR_EQUAL": Filter.NumericFilter.Operation.GREATER_THAN_OR_EQUAL,
                    "GT": Filter.NumericFilter.Operation.GREATER_THAN,
                    "LT": Filter.NumericFilter.Operation.LESS_THAN,
                    "GTE": Filter.NumericFilter.Operation.GREATER_THAN_OR_EQUAL,
                    "LTE": Filter.NumericFilter.Operation.LESS_THAN_OR_EQUAL,
                    "EQ": Filter.NumericFilter.Operation.EQUAL,
                }
                operation = op_map.get(op_str, Filter.NumericFilter.Operation.OPERATION_UNSPECIFIED)

            val = filter_dict.get("value", 0)
            if isinstance(val, int):
                num_val = NumericValue(int64_value=val)
            else:
                num_val = NumericValue(double_value=float(val))

            f.numeric_filter = Filter.NumericFilter(operation=operation, value=num_val)
        else:
            # String filter
            match_type_str = filter_dict.get("matchType", "EXACT").upper()
            try:
                match_type = getattr(Filter.StringFilter.MatchType, match_type_str)
            except AttributeError:
                match_type = Filter.StringFilter.MatchType.EXACT

            f.string_filter = Filter.StringFilter(
                match_type=match_type,
                value=str(filter_dict.get("value", "")),
                case_sensitive=filter_dict.get("caseSensitive", False),
            )

        return FilterExpression(filter=f)

    def _parse_order_by(self, order_dict: dict) -> OrderBy:
        """Convert a plain dict into a GA4 OrderBy."""
        order_by = OrderBy(desc=order_dict.get("desc", False))

        field = order_dict.get("field", "")
        # By default assume the field refers to a metric unless specified
        # in the input dict like {"dimension": "pagePath"} or {"metric": "sessions"}
        if "dimension" in order_dict:
            order_by.dimension = OrderBy.DimensionOrderBy(dimension_name=order_dict["dimension"])
        elif "metric" in order_dict:
            order_by.metric = OrderBy.MetricOrderBy(metric_name=order_dict["metric"])
        else:
            # Default to metric order if 'field' is provided and assume it's a metric
            # or fallback to using the provided string as a metric name
            order_by.metric = OrderBy.MetricOrderBy(metric_name=field)

        return order_by

    def run_report(
        self,
        property_id: str,
        metrics: list[str],
        dimensions: list[str] | None = None,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 100,
        dimension_filter: dict | None = None,
        metric_filter: dict | None = None,
        order_bys: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Run a GA4 report and return structured results."""
        request = RunReportRequest(
            property=property_id,
            metrics=[Metric(name=m) for m in metrics],
            dimensions=[Dimension(name=d) for d in (dimensions or [])],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
        )

        if dimension_filter:
            expr = self._parse_filter_expression(dimension_filter)
            if expr:
                request.dimension_filter = expr

        if metric_filter:
            expr = self._parse_filter_expression(metric_filter)
            if expr:
                request.metric_filter = expr

        if order_bys:
            request.order_bys = [self._parse_order_by(o) for o in order_bys]

        response = self._client.run_report(request)
        return self._format_report_response(response)

    def run_realtime_report(
        self,
        property_id: str,
        metrics: list[str],
    ) -> dict[str, Any]:
        """Run a GA4 realtime report."""
        request = RunRealtimeReportRequest(
            property=property_id,
            metrics=[Metric(name=m) for m in metrics],
            minute_ranges=[MinuteRange(start_minutes_ago=29, end_minutes_ago=0)],
        )

        response = self._client.run_realtime_report(request)
        return self._format_realtime_response(response)

    def compare_date_ranges(
        self,
        property_id: str,
        metrics: list[str],
        dimensions: list[str] | None = None,
        current_start: str = "7daysAgo",
        current_end: str = "today",
        previous_start: str = "14daysAgo",
        previous_end: str = "8daysAgo",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Compare two date ranges in a single report."""
        request = RunReportRequest(
            property=property_id,
            metrics=[Metric(name=m) for m in metrics],
            dimensions=[Dimension(name=d) for d in (dimensions or [])],
            date_ranges=[
                DateRange(start_date=current_start, end_date=current_end, name="current"),
                DateRange(start_date=previous_start, end_date=previous_end, name="previous"),
            ],
            limit=limit,
        )

        response = self._client.run_report(request)
        return self._format_report_response(response)

    def list_properties(self) -> dict[str, Any]:
        """List GA4 properties accessible by the configured service account."""

        properties = []
        # Find all account summaries to discover what we have access to
        account_summaries = self._admin_client.list_account_summaries()

        for account_summary in account_summaries:
            for property_summary in account_summary.property_summaries:
                properties.append(
                    {
                        "account": account_summary.account,
                        "account_name": account_summary.display_name,
                        "property_id": property_summary.property,
                        "property_name": property_summary.display_name,
                        "property_type": property_summary.property_type.name
                        if hasattr(property_summary.property_type, "name")
                        else str(property_summary.property_type),
                    }
                )

        return {
            "property_count": len(properties),
            "properties": properties,
        }

    def _format_report_response(
        self,
        response: Any,
    ) -> dict[str, Any]:
        """Format a RunReportResponse into a plain dict."""
        rows = []
        dim_headers = [h.name for h in response.dimension_headers]
        metric_headers = [h.name for h in response.metric_headers]

        for row in response.rows:
            row_data: dict[str, str] = {}
            for i, dim_value in enumerate(row.dimension_values):
                row_data[dim_headers[i]] = dim_value.value
            for i, metric_value in enumerate(row.metric_values):
                row_data[metric_headers[i]] = metric_value.value
            rows.append(row_data)

        return {
            "row_count": response.row_count,
            "rows": rows,
            "dimension_headers": dim_headers,
            "metric_headers": metric_headers,
        }

    def _format_realtime_response(
        self,
        response: Any,
    ) -> dict[str, Any]:
        """Format a RunRealtimeReportResponse into a plain dict."""
        rows = []
        metric_headers = [h.name for h in response.metric_headers]

        for row in response.rows:
            row_data: dict[str, str] = {}
            for i, metric_value in enumerate(row.metric_values):
                row_data[metric_headers[i]] = metric_value.value
            rows.append(row_data)

        return {
            "row_count": response.row_count,
            "rows": rows,
            "metric_headers": metric_headers,
        }


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Google Analytics tools with the MCP server."""

    def _get_credentials_path() -> str | None:
        """Get GA credentials path from credential store or environment."""
        if credentials is not None:
            path = credentials.get("google_analytics")
            if path is not None and not isinstance(path, str):
                raise TypeError(
                    f"Expected string from credentials.get('google_analytics'), "
                    f"got {type(path).__name__}"
                )
            return path
        return os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    def _get_client() -> _GAClient | dict[str, str]:
        """Get a GA client, or return an error dict if no credentials."""
        creds_path = _get_credentials_path()
        if not creds_path:
            return {
                "error": "Google Analytics credentials not configured",
                "help": (
                    "Set GOOGLE_APPLICATION_CREDENTIALS environment variable "
                    "to the path of your service account JSON key file, "
                    "or configure via credential store"
                ),
            }
        try:
            return _GAClient(creds_path)
        except Exception as e:
            return {"error": f"Failed to initialize Google Analytics client: {e}"}

    def _validate_inputs(property_id: str, *, limit: int | None = None) -> dict[str, str] | None:
        """Validate common inputs. Returns an error dict or None."""
        if not property_id or not property_id.startswith("properties/"):
            return {
                "error": "property_id must start with 'properties/' (e.g., 'properties/123456')"
            }
        if limit is not None and (limit < 1 or limit > 10000):
            return {"error": "limit must be between 1 and 10000"}
        return None

    @mcp.tool()
    def ga_run_report(
        property_id: str,
        metrics: list[str],
        dimensions: list[str] | None = None,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 100,
        dimension_filter: dict | None = None,
        metric_filter: dict | None = None,
        order_bys: list[dict] | None = None,
    ) -> dict:
        """
        Run a custom Google Analytics 4 report.

        Use this tool to query website traffic data with custom dimensions,
        metrics, and date ranges.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            metrics: Metrics to retrieve
                (e.g., ["sessions", "totalUsers", "conversions"])
            dimensions: Dimensions to group by
                (e.g., ["pagePath", "sessionSource"])
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo")
            end_date: End date (e.g., "today")
            limit: Max rows to return (1-10000)

        Returns:
            Dict with report rows or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id, limit=limit):
            return err
        if not metrics:
            return {"error": "metrics list must not be empty"}

        try:
            return client.run_report(
                property_id=property_id,
                metrics=metrics,
                dimensions=dimensions,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                dimension_filter=dimension_filter,
                metric_filter=metric_filter,
                order_bys=order_bys,
            )
        except Exception as e:
            logger.warning("ga_run_report failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_get_realtime(
        property_id: str,
        metrics: list[str] | None = None,
    ) -> dict:
        """
        Get real-time Google Analytics data (active users, current pages).

        Use this tool to check current website activity and detect traffic anomalies.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            metrics: Metrics to retrieve (default: ["activeUsers"])

        Returns:
            Dict with real-time data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id):
            return err

        effective_metrics = metrics or ["activeUsers"]

        try:
            return client.run_realtime_report(
                property_id=property_id,
                metrics=effective_metrics,
            )
        except Exception as e:
            logger.warning("ga_get_realtime failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_get_top_pages(
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 10,
    ) -> dict:
        """
        Get top pages by views and engagement.

        Convenience wrapper that returns the most-visited pages with
        key engagement metrics.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo")
            end_date: End date (e.g., "today")
            limit: Max pages to return (1-10000, default 10)

        Returns:
            Dict with top pages, their views, avg engagement time, and bounce rate
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id, limit=limit):
            return err

        try:
            return client.run_report(
                property_id=property_id,
                metrics=["screenPageViews", "averageSessionDuration", "bounceRate"],
                dimensions=["pagePath", "pageTitle"],
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        except Exception as e:
            logger.warning("ga_get_top_pages failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_get_traffic_sources(
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 10,
    ) -> dict:
        """
        Get traffic breakdown by source/medium.

        Convenience wrapper that shows which channels drive visitors to the site.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo")
            end_date: End date (e.g., "today")
            limit: Max sources to return (1-10000, default 10)

        Returns:
            Dict with traffic sources, sessions, users, and conversions per source
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id, limit=limit):
            return err

        try:
            return client.run_report(
                property_id=property_id,
                metrics=["sessions", "totalUsers", "conversions"],
                dimensions=["sessionSource", "sessionMedium"],
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        except Exception as e:
            logger.warning("ga_get_traffic_sources failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_get_user_demographics(
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 20,
    ) -> dict:
        """
        Get user demographics breakdown (country, language, device).

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo")
            end_date: End date (e.g., "today")
            limit: Max rows to return (1-10000, default 20)

        Returns:
            Dict with user counts by country, language, and device category
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id, limit=limit):
            return err

        try:
            return client.run_report(
                property_id=property_id,
                metrics=["totalUsers", "sessions", "engagedSessions"],
                dimensions=["country", "language", "deviceCategory"],
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        except Exception as e:
            logger.warning("ga_get_user_demographics failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_get_conversion_events(
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 20,
    ) -> dict:
        """
        Get conversion event counts and values.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo")
            end_date: End date (e.g., "today")
            limit: Max rows to return (1-10000, default 20)

        Returns:
            Dict with event names, counts, conversion counts, and total revenue
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id, limit=limit):
            return err

        try:
            return client.run_report(
                property_id=property_id,
                metrics=["eventCount", "conversions", "totalRevenue"],
                dimensions=["eventName"],
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        except Exception as e:
            logger.warning("ga_get_conversion_events failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_get_landing_pages(
        property_id: str,
        start_date: str = "28daysAgo",
        end_date: str = "today",
        limit: int = 10,
    ) -> dict:
        """
        Get top landing pages with entrance metrics.

        Shows which pages users arrive on first and their engagement.

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            start_date: Start date (e.g., "2024-01-01" or "28daysAgo")
            end_date: End date (e.g., "today")
            limit: Max pages to return (1-10000, default 10)

        Returns:
            Dict with landing pages, sessions, bounce rate, and conversions
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id, limit=limit):
            return err

        try:
            return client.run_report(
                property_id=property_id,
                metrics=["sessions", "bounceRate", "conversions", "averageSessionDuration"],
                dimensions=["landingPagePlusQueryString"],
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        except Exception as e:
            logger.warning("ga_get_landing_pages failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_compare_date_ranges(
        property_id: str,
        metrics: list[str],
        dimensions: list[str] | None = None,
        current_start: str = "7daysAgo",
        current_end: str = "today",
        previous_start: str = "14daysAgo",
        previous_end: str = "8daysAgo",
        limit: int = 100,
    ) -> dict:
        """
        Compare two date ranges in a single report (e.g., this week vs last week).

        Args:
            property_id: GA4 property ID (e.g., "properties/123456")
            metrics: Metrics to retrieve
                (e.g., ["sessions", "conversions"])
            dimensions: Dimensions to group by
                (e.g., ["sessionSource"])
            current_start: Current period start date
            current_end: Current period end date
            previous_start: Previous period start date
            previous_end: Previous period end date
            limit: Max rows to return (1-10000)

        Returns:
            Dict with report rows containing data for both date ranges or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if err := _validate_inputs(property_id, limit=limit):
            return err
        if not metrics:
            return {"error": "metrics list must not be empty"}

        try:
            return client.compare_date_ranges(
                property_id=property_id,
                metrics=metrics,
                dimensions=dimensions,
                current_start=current_start,
                current_end=current_end,
                previous_start=previous_start,
                previous_end=previous_end,
                limit=limit,
            )
        except Exception as e:
            logger.warning("ga_compare_date_ranges failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}

    @mcp.tool()
    def ga_list_properties() -> dict:
        """
        List GA4 properties accessible by the configured service account.

        Returns:
            Dict containing available accounts and their properties or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        try:
            return client.list_properties()
        except Exception as e:
            logger.warning("ga_list_properties failed: %s", e)
            return {"error": f"Google Analytics API error: {e}"}
