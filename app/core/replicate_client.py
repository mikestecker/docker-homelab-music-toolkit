"""Replicate API client for AI cover-art generation.

Uses Replicate's "official model" predictions endpoint
(POST /v1/models/{owner}/{name}/predictions), which always runs that model's
latest version - no version hash to pin or keep updated. This is the
convention Replicate's own code samples use for official models like
google/imagen-4 and the black-forest-labs/flux-*-pro family; REPLICATE_MODEL
is an "owner/name" id, not a version hash.

REST + poll, stdlib urllib only - same pattern as audiomuse_client.py.
"""
import json
import time
import urllib.error
import urllib.request

from app.core.config import REPLICATE_API_TOKEN, REPLICATE_MODEL

API_BASE = "https://api.replicate.com/v1"
POLL_INTERVAL = 1.5
POLL_TIMEOUT = 180


class ReplicateError(RuntimeError):
    pass


def _request(method, path, payload=None, timeout=30):
    if not REPLICATE_API_TOKEN:
        raise ReplicateError("REPLICATE_API_TOKEN isn't set.")
    req = urllib.request.Request(
        f"{API_BASE}{path}", method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Token {REPLICATE_API_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise ReplicateError(f"Replicate returned {e.code} for {path}: {detail[:300]}")
    except (urllib.error.URLError, OSError) as e:
        raise ReplicateError(f"Replicate is unreachable: {e}")


def generate_image(prompt, aspect_ratio="1:1", extra_input=None):
    """Submit a prediction against REPLICATE_MODEL, poll to completion,
    return the raw image bytes. extra_input lets callers pass model-specific
    fields (e.g. safety_filter_level) without this client needing to know
    every model's schema."""
    if not REPLICATE_MODEL:
        raise ReplicateError('REPLICATE_MODEL isn\'t set (e.g. "google/imagen-4").')
    input_payload = {"prompt": prompt, "aspect_ratio": aspect_ratio}
    if extra_input:
        input_payload.update(extra_input)
    created = _request("POST", f"/models/{REPLICATE_MODEL}/predictions", {"input": input_payload})
    prediction_id = created.get("id")
    if not prediction_id:
        raise ReplicateError(f"Replicate didn't return a prediction id: {created}")

    deadline = time.time() + POLL_TIMEOUT
    status = created.get("status")
    result = created
    while status in ("starting", "processing"):
        if time.time() > deadline:
            raise ReplicateError(f"Prediction {prediction_id} timed out after {POLL_TIMEOUT}s.")
        time.sleep(POLL_INTERVAL)
        result = _request("GET", f"/predictions/{prediction_id}")
        status = result.get("status")

    if status != "succeeded":
        raise ReplicateError(f"Prediction {prediction_id} {status}: {result.get('error')}")

    output = result.get("output")
    image_url = output[0] if isinstance(output, list) else output
    if not image_url:
        raise ReplicateError(f"Prediction {prediction_id} succeeded with no output.")
    try:
        with urllib.request.urlopen(image_url, timeout=60) as r:
            return r.read()
    except (urllib.error.URLError, OSError) as e:
        raise ReplicateError(f"Couldn't download the generated image: {e}")
