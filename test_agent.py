#!/usr/bin/env python3
"""Queries the deployed Agent Runtime to trigger live Agent Gateway connectivity checks."""

import json
import os
import sys
import google.auth
import google.auth.transport.requests
import requests

PROJECT_ID = os.environ.get("PROJECT_ID", "theta-ocean-464621-p0")
REGION = os.environ.get("REGION", "us-east4")


def get_headers(creds, auth_req) -> dict:
    if not creds.valid:
        creds.refresh(auth_req)
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def main():
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    api_base = f"https://{REGION}-aiplatform.googleapis.com/v1beta1"

    if len(sys.argv) > 1:
        engine_id = sys.argv[1].split("/")[-1]
    else:
        # Auto-discover the latest cff-agent-runtime Reasoning Engine in the project/region
        list_url = f"{api_base}/projects/{PROJECT_ID}/locations/{REGION}/reasoningEngines"
        resp = requests.get(
            list_url, headers=get_headers(creds, auth_req), timeout=30
        )
        resp.raise_for_status()
        engines = resp.json().get("reasoningEngines", [])
        if not engines:
            print(
                f"No Reasoning Engines found in {PROJECT_ID}/{REGION}. Run deploy_agent.py first.",
                file=sys.stderr,
            )
            sys.exit(1)
        engine_id = engines[0]["name"].split("/")[-1]

    stream_url = f"{api_base}/projects/{PROJECT_ID}/locations/{REGION}/reasoningEngines/{engine_id}:streamQuery"
    prompt = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "Run verify_all_gateway_endpoints to test connectivity to all public and private endpoints."
    )

    print(f"Querying Reasoning Engine {engine_id} in {PROJECT_ID}/{REGION}...")
    print(f"Prompt: {prompt}\n")

    payload = {
        "classMethod": "stream_query",
        "input": {
            "user_id": "test-user",
            "message": prompt,
        },
    }

    resp = requests.post(
        stream_url,
        headers=get_headers(creds, auth_req),
        json=payload,
        stream=True,
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"Error ({resp.status_code}):\n{resp.text}", file=sys.stderr)
        sys.exit(1)

    for line in resp.iter_lines(decode_unicode=True):
        if line:
            print(line)

    print("\n------------------------------------------------------------")
    print("View Cloud Logging connectivity results with:")
    print(
        f"gcloud logging read 'resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" "
        f"AND resource.labels.reasoning_engine_id=\"{engine_id}\" "
        f"AND jsonPayload.event=\"AGENT_GATEWAY_CONNECTIVITY_CHECK\"' "
        f"--project={PROJECT_ID} --limit=10 --format='yaml(timestamp,jsonPayload)'"
    )


if __name__ == "__main__":
    main()

