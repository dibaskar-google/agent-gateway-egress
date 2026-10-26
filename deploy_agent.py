#!/usr/bin/env python3
"""Deploys a Vertex AI Agent Runtime (Reasoning Engine) attached to the cff-egress-agw Agent Gateway."""

import base64
import io
import json
import os
import sys
import tarfile
import time
import google.auth
import google.auth.transport.requests
import requests

# ---------------------------------------------------------------------------
# Configuration (matches provisioned Agent Gateway in theta-ocean-464621-p0)
# ---------------------------------------------------------------------------
PROJECT_ID = os.environ.get("PROJECT_ID", "theta-ocean-464621-p0")
REGION = os.environ.get("REGION", "us-east4")
GATEWAY_NAME = os.environ.get("GATEWAY_NAME", "cff-egress-agw")
AGENT_DISPLAY_NAME = os.environ.get("AGENT_DISPLAY_NAME", "cff-agent-runtime")
PYTHON_VERSION = os.environ.get("PYTHON_VERSION", "3.13")

AGENT_GATEWAY_ID = (
    f"projects/{PROJECT_ID}/locations/{REGION}/agentGateways/{GATEWAY_NAME}"
)
SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_src")


def build_source_archive_b64(src_dir: str) -> str:
    """Packages agent.py and requirements.txt from src_dir into a base64 tar.gz string."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for fname in ("agent.py", "requirements.txt"):
            fpath = os.path.join(src_dir, fname)
            if not os.path.exists(fpath):
                raise FileNotFoundError(f"Missing required source file: {fpath}")
            tar.add(fpath, arcname=fname)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def get_headers(creds, auth_req) -> dict:
    if not creds.valid:
        creds.refresh(auth_req)
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def main():
    print(f"Packaging agent source from: {SOURCE_DIR}")
    source_archive_b64 = build_source_archive_b64(SOURCE_DIR)

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    api_base = f"https://{REGION}-aiplatform.googleapis.com/v1beta1"
    create_url = f"{api_base}/projects/{PROJECT_ID}/locations/{REGION}/reasoningEngines"

    payload = {
        "displayName": AGENT_DISPLAY_NAME,
        "description": f"Agent Runtime with egress via {GATEWAY_NAME}",
        "spec": {
            "agentFramework": "google-adk",
            "identityType": "AGENT_IDENTITY",
            "deploymentSpec": {
                "agentGatewayConfig": {
                    "agentToAnywhereConfig": {
                        "agentGateway": AGENT_GATEWAY_ID,
                    }
                }
            },
            "sourceCodeSpec": {
                "inlineSource": {
                    "sourceArchive": source_archive_b64,
                },
                "pythonSpec": {
                    "version": PYTHON_VERSION,
                    "entrypointModule": "agent",
                    "entrypointObject": "agent",
                    "requirementsFile": "requirements.txt",
                },
            },
        },
    }

    print(f"Deploying Agent Runtime '{AGENT_DISPLAY_NAME}' in {PROJECT_ID}/{REGION}...")
    print(f"Attached Egress Agent Gateway: {AGENT_GATEWAY_ID}")

    resp = requests.post(
        create_url, headers=get_headers(creds, auth_req), json=payload, timeout=60
    )
    if resp.status_code != 200:
        print(f"Error ({resp.status_code}):\n{resp.text}", file=sys.stderr)
        sys.exit(1)

    op = resp.json()
    op_name = op["name"]
    op_url = f"{api_base}/{op_name}"
    print(f"Started operation: {op_name}")

    while True:
        time.sleep(10)
        poll = requests.get(op_url, headers=get_headers(creds, auth_req), timeout=30)
        poll.raise_for_status()
        op_data = poll.json()
        if op_data.get("done"):
            if "error" in op_data:
                print(
                    f"\nDeployment failed:\n{json.dumps(op_data['error'], indent=2)}",
                    file=sys.stderr,
                )
                sys.exit(1)
            result = op_data.get("response", {})
            break
        print("Still deploying Agent Runtime... (waiting 10s)", flush=True)

    engine_name = result.get("name", "")
    engine_id = engine_name.split("/")[-1] if engine_name else ""
    effective_identity = result.get("spec", {}).get("effectiveIdentity", "")
    principal_uri = (
        f"principal://{effective_identity}"
        if effective_identity and not effective_identity.startswith("principal://")
        else effective_identity
    )

    print("\n============================================================")
    print("Agent Runtime Deployed Successfully!")
    print(f"Resource Name     : {engine_name}")
    print(f"ReasoningEngine ID: {engine_id}")
    print(f"Egress Gateway    : {AGENT_GATEWAY_ID}")
    if principal_uri:
        print(f"Agent Principal   : {principal_uri}")
        print(
            "\nYou can use this Agent Principal in data/endpoints/*.yaml under 'principals:'"
        )
    print("\nCloud Logging Filter to view Agent Gateway connectivity results:")
    print(
        f'  resource.type="aiplatform.googleapis.com/ReasoningEngine"\n'
        f'  resource.labels.reasoning_engine_id="{engine_id}"\n'
        f'  jsonPayload.event="AGENT_GATEWAY_CONNECTIVITY_CHECK"'
    )
    print("============================================================")


if __name__ == "__main__":
    main()
