#!/usr/bin/env python3
import json
import os
import sys
import time
from google.adk.agents import LlmAgent
import requests
from vertexai.agent_engines import AdkApp

# Public and private endpoints to verify through the Agent Gateway on startup and via tools
PUBLIC_ENDPOINTS = [
    "https://httpbin.org/get",
    "https://api.frankfurter.app/latest",
]
PRIVATE_ENDPOINTS = [
    "https://aiplatform.us.rep.googleapis.com/$discovery/rest?version=v1",
    "https://us-east4-aiplatform.googleapis.com/$discovery/rest?version=v1",
    "https://internal.cloud.dinesh.com",
]


def write_cloud_log(
    message: str,
    severity: str = "INFO",
    **extra_fields,
) -> None:
    """Emits a structured JSON log entry automatically ingested by Cloud Logging."""
    entry = {
        "severity": severity,
        "message": message,
        "event": "AGENT_GATEWAY_CONNECTIVITY_CHECK",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "https_proxy": os.environ.get(
            "HTTPS_PROXY", os.environ.get("https_proxy", "unset")
        ),
        **extra_fields,
    }
    # Vertex AI Reasoning Engine automatically parses single-line JSON on stdout into Cloud Logging jsonPayload
    print(json.dumps(entry), file=sys.stdout, flush=True)


def probe_endpoint(url: str, endpoint_type: str = "PUBLIC") -> dict:
    """Probes an endpoint through the Agent Gateway and logs the result to Cloud Logging."""
    start = time.time()
    try:
        resp = requests.get(url, timeout=10)
        latency_ms = round((time.time() - start) * 1000, 2)
        succeeded = 200 <= resp.status_code < 400
        status_str = "SUCCEEDED" if succeeded else "FAILED"
        severity = "INFO" if succeeded else "WARNING"
        result = {
            "endpoint": url,
            "endpoint_type": endpoint_type,
            "connectivity_status": status_str,
            "http_status_code": resp.status_code,
            "latency_ms": latency_ms,
            "response_preview": resp.text[:200],
        }
        write_cloud_log(
            f"[Agent Gateway Connectivity {status_str}] {endpoint_type} endpoint {url} returned HTTP {resp.status_code} ({latency_ms} ms)",
            severity=severity,
            **result,
        )
        return result
    except Exception as exc:
        latency_ms = round((time.time() - start) * 1000, 2)
        result = {
            "endpoint": url,
            "endpoint_type": endpoint_type,
            "connectivity_status": "FAILED",
            "error": str(exc),
            "latency_ms": latency_ms,
        }
        write_cloud_log(
            f"[Agent Gateway Connectivity FAILED] {endpoint_type} endpoint {url} error: {exc}",
            severity="ERROR",
            **result,
        )
        return result


def verify_all_gateway_endpoints() -> dict:
    """Tests all configured public and private endpoints through the Agent Gateway and logs results to Cloud Logging."""
    write_cloud_log(
        "Starting Agent Gateway egress connectivity verification for PUBLIC and PRIVATE endpoints..."
    )
    results = {"public": [], "private": []}
    for url in PUBLIC_ENDPOINTS:
        results["public"].append(probe_endpoint(url, endpoint_type="PUBLIC"))
    for url in PRIVATE_ENDPOINTS:
        results["private"].append(probe_endpoint(url, endpoint_type="PRIVATE"))

    write_cloud_log(
        "Completed Agent Gateway egress connectivity verification.",
        summary=results,
    )
    return results


def check_endpoint(url: str = "https://httpbin.org/get") -> dict:
    """Tests connectivity to a specific URL through the Agent Gateway and logs to Cloud Logging."""
    endpoint_type = (
        "PRIVATE"
        if any(
            domain in url
            for domain in (
                "dinesh.com",
                ".internal",
                "aiplatform.us.rep.googleapis.com",
                "us-east4-aiplatform.googleapis.com",
            )
        )
        else "PUBLIC"
    )
    return probe_endpoint(url, endpoint_type=endpoint_type)


# Run connectivity verification automatically when the Agent Runtime container boots during deployment
try:
    verify_all_gateway_endpoints()
except Exception as boot_exc:
    write_cloud_log(
        f"Startup connectivity check encountered an error: {boot_exc}",
        severity="ERROR",
    )

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="agw_egress_test_agent",
    instruction=(
        "You are an agent deployed on Vertex AI Agent Runtime with outbound traffic "
        "routed through an Agent Gateway. Use verify_all_gateway_endpoints or "
        "check_endpoint to verify connectivity to public and private endpoints and "
        "log the results to Cloud Logging."
    ),
    tools=[verify_all_gateway_endpoints, check_endpoint],
)

agent = AdkApp(agent=root_agent)
