# app.py
# Purpose: Expose analyzer endpoints for HA; support `?init=...` to upsert sane defaults without camera/Bedrock calls,
# ensuring entities exist after restarts. Adds LPG auto-switcher detector + hardened Bedrock JSON-only prompting.

import base64
import json
import logging
import os
import time
from typing import Dict, Any, Tuple

import boto3
import requests
from flask import Flask, jsonify, request

# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Environment Variables
# ---------------------------------------------------------
HA_BASE_URL = os.environ.get("HA_BASE_URL", "").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN")

CLOTHES_RACK_CAMERA_ENTITY_ID = os.environ.get("CLOTHES_RACK_CAMERA_ENTITY_ID")
CLOTHES_RACK_TARGET_ENTITY_ID = os.environ.get("CLOTHES_RACK_TARGET_ENTITY_ID")

GAS_HEATER_CAMERA_ENTITY_ID = os.environ.get("GAS_HEATER_CAMERA_ENTITY_ID")
GAS_HEATER_TARGET_ENTITY_ID = os.environ.get("GAS_HEATER_TARGET_ENTITY_ID")

STUDY_ROOM_CAMERA_ENTITY_ID = os.environ.get("STUDY_ROOM_CAMERA_ENTITY_ID")
STUDY_ROOM_CAMERA_TARGET_ENTITY_ID = os.environ.get("STUDY_ROOM_CAMERA_TARGET_ENTITY_ID")

ENTRANCE_DOORBELL_CAMERA_ENTITY_ID = os.environ.get("ENTRANCE_DOORBELL_CAMERA_ENTITY_ID")
ENTRANCE_DOORBELL_CAMERA_TARGET_ENTITY_ID = os.environ.get("ENTRANCE_DOORBELL_CAMERA_TARGET_ENTITY_ID")

LPG_AUTO_SWITCHER_CAMERA_ENTITY_ID = os.environ.get("LPG_AUTO_SWITCHER_CAMERA_ENTITY_ID")
LPG_AUTO_SWITCHER_TARGET_ENTITY_ID = os.environ.get("LPG_AUTO_SWITCHER_TARGET_ENTITY_ID")

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

# Optional default overrides via env (so you can tweak boot defaults without code changes)
DEFAULTS_CLOTHES_RACK_DETECTED = os.environ.get("DEFAULTS_CLOTHES_RACK_DETECTED", "off")
DEFAULTS_CLOTHES_RACK_CONFIDENCE = float(os.environ.get("DEFAULTS_CLOTHES_RACK_CONFIDENCE", "0.0"))

DEFAULTS_GAS_HEATER_TEMPERATURE = float(os.environ.get("DEFAULTS_GAS_HEATER_TEMPERATURE", "0.0"))
DEFAULTS_GAS_HEATER_ACTIVE = os.environ.get("DEFAULTS_GAS_HEATER_ACTIVE", "off")
DEFAULTS_GAS_HEATER_HEATING = os.environ.get("DEFAULTS_GAS_HEATER_HEATING", "off")
DEFAULTS_GAS_HEATER_CONFIDENCE = float(os.environ.get("DEFAULTS_GAS_HEATER_CONFIDENCE", "0.0"))

DEFAULTS_STUDY_ROOM_STATE = os.environ.get("DEFAULTS_STUDY_ROOM_STATE", "off")
DEFAULTS_STUDY_ROOM_CONFIDENCE = float(os.environ.get("DEFAULTS_STUDY_ROOM_CONFIDENCE", "0.0"))

DEFAULTS_DOORBELL_STATE = os.environ.get("DEFAULTS_DOORBELL_STATE", "unknown")
DEFAULTS_DOORBELL_CONFIDENCE = float(os.environ.get("DEFAULTS_DOORBELL_CONFIDENCE", "0.0"))

# NEW: LPG defaults
DEFAULTS_LPG_AUTO_SWITCHER_STATE = os.environ.get("DEFAULTS_LPG_AUTO_SWITCHER_STATE", "off")  # 'on' when red
DEFAULTS_LPG_AUTO_SWITCHER_CONFIDENCE = float(os.environ.get("DEFAULTS_LPG_AUTO_SWITCHER_CONFIDENCE", "0.0"))

# Basic validation (keep existing behavior)
required_vars = [
    HA_BASE_URL,
    HA_TOKEN,
    CLOTHES_RACK_CAMERA_ENTITY_ID,
    CLOTHES_RACK_TARGET_ENTITY_ID,
    GAS_HEATER_CAMERA_ENTITY_ID,
    GAS_HEATER_TARGET_ENTITY_ID,
    BEDROCK_MODEL_ID,
]
if any(not var for var in required_vars):
    logger.warning(
        "Some required environment variables are missing. "
        "Ensure HA_BASE_URL, HA_TOKEN, CAMERA_ENTITY_ID, TARGET_ENTITY_ID, "
        "and BEDROCK_MODEL_ID are set."
    )

# ---------------------------------------------------------
# Flask Application
# ---------------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------------
# Small helpers
# ---------------------------------------------------------
def _is_truthy(val: str | None) -> bool:
    """Return True for common truthy strings/numbers."""
    if val is None:
        return False
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _make_fake_bedrock_result(text_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a fake Bedrock-like response so we can reuse the existing update_* functions
    without touching their signatures or downstream logic.
    """
    return {
        "output": {"message": {"content": [{"text": json.dumps(text_obj)}]}},
        "usage": {"inputTokens": 0, "outputTokens": 0},
        "stopReason": "init",
    }


def _parse_bedrock_content_json(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Bedrock result content into JSON robustly.

    Purpose:
      - Prefer "prompt correctness" (strict JSON-only prompts) so this never triggers.
      - Still handle occasional formatting drift (e.g., markdown fences) so the app doesn't 500.

    Returns:
      Dict parsed JSON object.
    """
    raw = result["output"]["message"]["content"][0]["text"]
    s = str(raw).strip()

    # If the model still wraps JSON in markdown fences, strip them safely.
    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1 :].strip()
        if s.endswith("```"):
            s = s[:-3].strip()

    # Extract the first JSON object, if extra text exists.
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first : last + 1].strip()

    try:
        return json.loads(s)
    except json.JSONDecodeError as ex:
        raise ValueError(f"Bedrock response not valid JSON. Raw begins with: {raw[:120]!r}") from ex


# ---------------------------------------------------------
# HA / Camera / Bedrock helpers
# ---------------------------------------------------------
def get_short_lived_token(camera_entity_id: str) -> str:
    """
    Retrieve the short-lived token stored on the camera entity attributes.
    """
    if "." not in camera_entity_id:
        raise ValueError(
            f"Camera entity '{camera_entity_id}' is invalid. Must have a domain prefix (e.g., 'camera.')."
        )

    states_url = f"{HA_BASE_URL}/api/states/{camera_entity_id}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}

    logger.info(f"Fetching short-lived token from {camera_entity_id}...")
    response = requests.get(states_url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()["attributes"]["access_token"]


def capture_image_from_ha(camera_entity_id: str) -> bytes:
    """
    Use the Home Assistant camera_proxy endpoint with the short-lived token
    to fetch the snapshot image bytes for the given camera entity.
    """
    short_lived_token = get_short_lived_token(camera_entity_id)
    snapshot_url = f"{HA_BASE_URL}/api/camera_proxy/{camera_entity_id}?token={short_lived_token}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}

    logger.info(f"Requesting camera snapshot from {snapshot_url}")
    resp = requests.get(snapshot_url, headers=headers, timeout=10)
    if resp.status_code == 200:
        logger.info("Snapshot fetched successfully from Home Assistant.")
        return resp.content

    raise ConnectionError(f"Failed to retrieve snapshot. Status: {resp.status_code}, Response: {resp.text}")


def analyze_image_with_bedrock(image_bytes: bytes, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    Send the base64-encoded image to AWS Bedrock for analysis.
    """
    if not BEDROCK_MODEL_ID:
        raise EnvironmentError("AWS Bedrock Model ID is not configured.")

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    system_prompt = [{"text": system_prompt}]

    user_message = [
        {
            "role": "user",
            "content": [
                {"image": {"format": "jpg", "source": {"bytes": base64_image}}},
                {"text": user_prompt},
            ],
        }
    ]

    payload = {"schemaVersion": "messages-v1", "messages": user_message, "system": system_prompt}

    bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    try:
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            body=json.dumps(payload),
        )
    except Exception as ex:
        logger.error(f"Error invoking AWS Bedrock model: {ex}")
        raise

    response_body = response.get("body")
    if not response_body:
        raise ValueError("No body in Bedrock response.")

    response_data = response_body.read().decode("utf-8")
    try:
        result = json.loads(response_data)
    except json.JSONDecodeError:
        logger.error(f"Bedrock response invalid JSON envelope: {response_data}")
        raise ValueError("Bedrock response not valid JSON envelope.")

    logger.info(f"Bedrock analysis result -> {result}")
    return result


# ---------------------------------------------------------
# HA state updaters (unchanged signatures; we'll reuse via fake results)
# ---------------------------------------------------------
def update_clothes_rack_ha_entity(result: Dict[str, Any]) -> Tuple[bool, float]:
    """Update a Home Assistant entity with the detection results."""
    if not (HA_BASE_URL and HA_TOKEN and CLOTHES_RACK_TARGET_ENTITY_ID):
        logger.warning("Cannot update entity. Missing HA config or target entity.")
        raise ValueError("Cannot update entity. Missing HA config or target entity.")

    detection_result = _parse_bedrock_content_json(result)
    is_detected = detection_result["detected"]
    confidence = detection_result["confidence"]

    state_value = "on" if is_detected else "off"
    attributes = {
        "device_class": "occupancy",
        "detected": is_detected,
        "confidence": round(float(confidence), 3),
        "updated_at": int(time.time()),
        "input_tokens": result.get("usage", {}).get("inputTokens", 0),
        "output_tokens": result.get("usage", {}).get("outputTokens", 0),
        "stop_reason": result.get("stopReason", ""),
    }

    url = f"{HA_BASE_URL}/api/states/{CLOTHES_RACK_TARGET_ENTITY_ID}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    data = {"state": state_value, "attributes": attributes}

    resp = requests.post(url, headers=headers, json=data, timeout=5)
    if resp.status_code in (200, 201):
        logger.info(
            f"Successfully updated '{CLOTHES_RACK_TARGET_ENTITY_ID}' with detected={is_detected}, "
            f"confidence={float(confidence):.3f}."
        )
    else:
        logger.error(
            f"Failed to update entity '{CLOTHES_RACK_TARGET_ENTITY_ID}'. Status: {resp.status_code}, Error: {resp.text}"
        )

    return bool(is_detected), float(confidence)


def update_gas_heater_display_ha_entity(result: Dict[str, Any]) -> Dict[str, Any]:
    """Update a Home Assistant entity with the detection results."""
    if not (HA_BASE_URL and HA_TOKEN and GAS_HEATER_TARGET_ENTITY_ID):
        logger.warning("Cannot update entity. Missing HA config or target entity.")
        raise ValueError("Cannot update entity. Missing HA config or target entity.")

    detection_result = _parse_bedrock_content_json(result)
    confidence = float(detection_result["confidence"])

    attributes = {
        "device_class": "temperature",
        # NOTE: Kept as-is from your original code.
        "is_out_of_order": "off" if detection_result["is_active"] == "on" else "off",
        "confidence": round(confidence, 3),
        "updated_at": int(time.time()),
        "input_tokens": result.get("usage", {}).get("inputTokens", 0),
        "output_tokens": result.get("usage", {}).get("outputTokens", 0),
        "stop_reason": result.get("stopReason", ""),
        "is_heating": detection_result["state"],
    }

    url = f"{HA_BASE_URL}/api/states/{GAS_HEATER_TARGET_ENTITY_ID}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    data = {"state": detection_result["temperature"], "attributes": attributes}

    resp = requests.post(url, headers=headers, json=data, timeout=5)
    if resp.status_code in (200, 201):
        logger.info(
            f"Successfully updated '{GAS_HEATER_TARGET_ENTITY_ID}' with data={data}, confidence={confidence:.3f}."
        )
    else:
        logger.error(
            f"Failed to update entity '{GAS_HEATER_TARGET_ENTITY_ID}'. Status: {resp.status_code}, Error: {resp.text}"
        )

    return data


def update_study_room_ha_entity(result: Dict[str, Any]) -> Dict[str, Any]:
    """Update a Home Assistant entity with the detection results."""
    if not (HA_BASE_URL and HA_TOKEN and STUDY_ROOM_CAMERA_TARGET_ENTITY_ID):
        logger.warning("Cannot update entity. Missing HA config or target entity.")
        raise ValueError("Cannot update entity. Missing HA config or target entity.")

    detection_result = _parse_bedrock_content_json(result)
    confidence = float(detection_result["confidence"])
    attributes = {
        "device_class": "presence",
        "confidence": round(confidence, 3),
        "updated_at": int(time.time()),
        "input_tokens": result.get("usage", {}).get("inputTokens", 0),
        "output_tokens": result.get("usage", {}).get("outputTokens", 0),
        "stop_reason": result.get("stopReason", ""),
    }

    url = f"{HA_BASE_URL}/api/states/{STUDY_ROOM_CAMERA_TARGET_ENTITY_ID}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    data = {"state": detection_result["state"], "attributes": attributes}

    resp = requests.post(url, headers=headers, json=data, timeout=5)
    if resp.status_code in (200, 201):
        logger.info(
            f"Successfully updated '{STUDY_ROOM_CAMERA_TARGET_ENTITY_ID}' with data={data}, confidence={confidence:.3f}."
        )
    else:
        logger.error(
            f"Failed to update entity '{STUDY_ROOM_CAMERA_TARGET_ENTITY_ID}'. Status: {resp.status_code}, Error: {resp.text}"
        )

    return data


def update_entrance_doorbell_ha_entity(result: Dict[str, Any]) -> Dict[str, Any]:
    """Update a Home Assistant entity with the detection results."""
    if not (HA_BASE_URL and HA_TOKEN and ENTRANCE_DOORBELL_CAMERA_TARGET_ENTITY_ID):
        logger.warning("Cannot update entity. Missing HA config or target entity.")
        raise ValueError("Cannot update entity. Missing HA config or target entity.")

    detection_result = _parse_bedrock_content_json(result)
    confidence = float(detection_result["confidence"])
    attributes = {
        "confidence": round(confidence, 3),
        "updated_at": int(time.time()),
        "input_tokens": result.get("usage", {}).get("inputTokens", 0),
        "output_tokens": result.get("usage", {}).get("outputTokens", 0),
        "stop_reason": result.get("stopReason", ""),
    }

    url = f"{HA_BASE_URL}/api/states/{ENTRANCE_DOORBELL_CAMERA_TARGET_ENTITY_ID}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    data = {"state": detection_result["state"], "attributes": attributes}

    resp = requests.post(url, headers=headers, json=data, timeout=5)
    if resp.status_code in (200, 201):
        logger.info(
            f"Successfully updated '{ENTRANCE_DOORBELL_CAMERA_TARGET_ENTITY_ID}' with data={data}, confidence={confidence:.3f}."
        )
    else:
        logger.error(
            f"Failed to update entity '{ENTRANCE_DOORBELL_CAMERA_TARGET_ENTITY_ID}'. Status: {resp.status_code}, Error: {resp.text}"
        )

    return data


def update_lpg_auto_switcher_ha_entity(result: Dict[str, Any]) -> Tuple[bool, float]:
    """
    Update HA entity reflecting whether LPG auto-switcher indicator window is red.

    HA state:
      - "on"  => indicator window is red
      - "off" => indicator window is not red
    """
    if not (HA_BASE_URL and HA_TOKEN and LPG_AUTO_SWITCHER_TARGET_ENTITY_ID):
        logger.warning("Cannot update entity. Missing HA config or target entity.")
        raise ValueError("Cannot update entity. Missing HA config or target entity.")

    detection_result = _parse_bedrock_content_json(result)
    is_red = bool(detection_result["is_red"])
    confidence = float(detection_result["confidence"])

    state_value = "on" if is_red else "off"
    attributes = {
        "device_class": "problem",
        "is_red": is_red,
        "confidence": round(confidence, 3),
        "updated_at": int(time.time()),
        "input_tokens": result.get("usage", {}).get("inputTokens", 0),
        "output_tokens": result.get("usage", {}).get("outputTokens", 0),
        "stop_reason": result.get("stopReason", ""),
    }

    url = f"{HA_BASE_URL}/api/states/{LPG_AUTO_SWITCHER_TARGET_ENTITY_ID}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    data = {"state": state_value, "attributes": attributes}

    resp = requests.post(url, headers=headers, json=data, timeout=5)
    if resp.status_code in (200, 201):
        logger.info(
            f"Successfully updated '{LPG_AUTO_SWITCHER_TARGET_ENTITY_ID}' with is_red={is_red}, confidence={confidence:.3f}."
        )
    else:
        logger.error(
            f"Failed to update entity '{LPG_AUTO_SWITCHER_TARGET_ENTITY_ID}'. Status: {resp.status_code}, Error: {resp.text}"
        )

    return is_red, confidence


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.route("/analyze/clothes-rack", methods=["GET"])
def analyze_clothes_rack():
    """Capture, analyze, and update detection results in Home Assistant. Supports `?init=1`."""
    try:
        if _is_truthy(request.args.get("init")):
            detected = DEFAULTS_CLOTHES_RACK_DETECTED.lower() == "on"
            fake = _make_fake_bedrock_result(
                {"detected": detected, "confidence": float(DEFAULTS_CLOTHES_RACK_CONFIDENCE)}
            )
            is_detected, confidence = update_clothes_rack_ha_entity(fake)
            return jsonify({"detected": is_detected, "confidence": confidence, "mode": "init"}), 200

        image_bytes = capture_image_from_ha(CLOTHES_RACK_CAMERA_ENTITY_ID)
        detection_result = analyze_image_with_bedrock(
            image_bytes=image_bytes,
            system_prompt=(
                "You are a vision classification system. "
                "Return STRICT JSON ONLY (no markdown, no triple backticks, no explanations). "
                "The response must start with '{' and end with '}'. "
                "Return exactly one JSON object with keys: "
                "'detected' (boolean) and 'confidence' (number 0..1)."
            ),
            user_prompt=(
                "Does this image contain a clothes drying rack with clothes on it? "
                "Return only: {\"detected\": <true/false>, \"confidence\": <0..1>}."
            ),
        )
        is_detected, confidence = update_clothes_rack_ha_entity(detection_result)
        return jsonify({"detected": is_detected, "confidence": confidence}), 200

    except Exception as ex:
        logger.exception(f"Analysis workflow failed: {ex}")
        return jsonify({"error": str(ex)}), 500


@app.route("/analyze/gas-heater-display", methods=["GET"])
def analyze_gas_heater_display():
    """Capture, analyze, and update the gas heater display results in Home Assistant. Supports `?init=1`."""
    try:
        if _is_truthy(request.args.get("init")):
            fake = _make_fake_bedrock_result(
                {
                    "temperature": float(DEFAULTS_GAS_HEATER_TEMPERATURE),
                    "is_active": DEFAULTS_GAS_HEATER_ACTIVE,
                    "state": DEFAULTS_GAS_HEATER_HEATING,
                    "confidence": float(DEFAULTS_GAS_HEATER_CONFIDENCE),
                }
            )
            data_sent = update_gas_heater_display_ha_entity(fake)
            return jsonify({**data_sent, "mode": "init"}), 200

        image_bytes = capture_image_from_ha(GAS_HEATER_CAMERA_ENTITY_ID)
        detection_result = analyze_image_with_bedrock(
            image_bytes=image_bytes,
            system_prompt=(
                "You are a vision parsing system. "
                "Return STRICT JSON ONLY (no markdown, no triple backticks, no explanations). "
                "The response must start with '{' and end with '}'. "
                "Return exactly one JSON object with keys: "
                "'temperature' (integer), "
                "'is_active' (string 'on'/'off' based on green dot), "
                "'state' (string 'on'/'off' based on red dot), "
                "'confidence' (number 0..1)."
            ),
            user_prompt=(
                "Parse the image and check for a number, a green dot, and a red dot. "
                "Return only: "
                "{\"temperature\": <int>, \"is_active\": \"on|off\", \"state\": \"on|off\", \"confidence\": <0..1>}."
            ),
        )
        data_sent = update_gas_heater_display_ha_entity(detection_result)
        return jsonify(data_sent), 200

    except Exception as ex:
        logger.exception(f"Analysis workflow failed: {ex}")
        return jsonify({"error": str(ex)}), 500


@app.route("/analyze/study-room-camera", methods=["GET"])
def analyze_study_room_camera():
    """Capture, analyze, and update study-room presence results in Home Assistant. Supports `?init=1`."""
    try:
        if _is_truthy(request.args.get("init")):
            fake = _make_fake_bedrock_result(
                {"state": DEFAULTS_STUDY_ROOM_STATE, "confidence": float(DEFAULTS_STUDY_ROOM_CONFIDENCE)}
            )
            data_sent = update_study_room_ha_entity(fake)
            return jsonify({**data_sent, "mode": "init"}), 200

        image_bytes = capture_image_from_ha(STUDY_ROOM_CAMERA_ENTITY_ID)
        detection_result = analyze_image_with_bedrock(
            image_bytes=image_bytes,
            system_prompt=(
                "You are a vision classification system. "
                "Return STRICT JSON ONLY (no markdown, no triple backticks, no explanations). "
                "The response must start with '{' and end with '}'. "
                "Return exactly one JSON object with keys: "
                "'state' (string 'on' when a person is present else 'off') and "
                "'confidence' (number 0..1)."
            ),
            user_prompt=(
                "Is there a person in the image? "
                "Return only: {\"state\": \"on|off\", \"confidence\": <0..1>}."
            ),
        )
        data_sent = update_study_room_ha_entity(detection_result)
        return jsonify(data_sent), 200

    except Exception as ex:
        logger.exception(f"Analysis workflow failed: {ex}")
        return jsonify({"error": str(ex)}), 500


@app.route("/analyze/entrance-doorbell-camera", methods=["GET"])
def analyze_entrance_doorbell_camera():
    """Capture, analyze, and update entrance-doorbell scene description in Home Assistant. Supports `?init=1`."""
    try:
        if _is_truthy(request.args.get("init")):
            fake = _make_fake_bedrock_result(
                {"state": DEFAULTS_DOORBELL_STATE, "confidence": float(DEFAULTS_DOORBELL_CONFIDENCE)}
            )
            data_sent = update_entrance_doorbell_ha_entity(fake)
            return jsonify({**data_sent, "mode": "init"}), 200

        image_bytes = capture_image_from_ha(ENTRANCE_DOORBELL_CAMERA_ENTITY_ID)
        detection_result = analyze_image_with_bedrock(
            image_bytes=image_bytes,
            system_prompt=(
                "You are a vision summarization system. "
                "Return STRICT JSON ONLY (no markdown, no triple backticks, no explanations). "
                "The response must start with '{' and end with '}'. "
                "Return exactly one JSON object with keys: "
                "'state' (string) and 'confidence' (number 0..1)."
            ),
            user_prompt=(
                "Describe what you see in a way that helps decide whether to open the door. "
                "Return only: {\"state\": \"...\", \"confidence\": <0..1>}."
            ),
        )
        data_sent = update_entrance_doorbell_ha_entity(detection_result)
        return jsonify(data_sent), 200

    except Exception as ex:
        logger.exception(f"Analysis workflow failed: {ex}")
        return jsonify({"error": str(ex)}), 500


@app.route("/analyze/lpg-auto-switcher", methods=["GET"])
def analyze_lpg_auto_switcher():
    """
    Capture, analyze, and update LPG auto-switcher indicator window status in Home Assistant.
    Detect if the small plastic window/indicator has turned red.

    Supports `?init=1` to upsert defaults without camera/Bedrock.
    """
    try:
        if _is_truthy(request.args.get("init")):
            fake = _make_fake_bedrock_result(
                {
                    "is_red": (DEFAULTS_LPG_AUTO_SWITCHER_STATE.lower() == "on"),
                    "confidence": float(DEFAULTS_LPG_AUTO_SWITCHER_CONFIDENCE),
                }
            )
            is_red, confidence = update_lpg_auto_switcher_ha_entity(fake)
            return jsonify({"is_red": is_red, "confidence": confidence, "mode": "init"}), 200

        if not LPG_AUTO_SWITCHER_CAMERA_ENTITY_ID:
            raise ValueError("LPG_AUTO_SWITCHER_CAMERA_ENTITY_ID is not set.")
        if not LPG_AUTO_SWITCHER_TARGET_ENTITY_ID:
            raise ValueError("LPG_AUTO_SWITCHER_TARGET_ENTITY_ID is not set.")

        image_bytes = capture_image_from_ha(LPG_AUTO_SWITCHER_CAMERA_ENTITY_ID)

        # Hardened prompts: strict JSON-only contract (no markdown / no fences).
        detection_result = analyze_image_with_bedrock(
            image_bytes=image_bytes,
            system_prompt=(
                "You are a vision classification system. "
                "You must return STRICT JSON ONLY. "
                "Do NOT use markdown. Do NOT use triple backticks. Do NOT add explanations. "
                "Do NOT add text before or after the JSON. "
                "The response must start with '{' and end with '}'. "
                "Return exactly one JSON object with keys: "
                "'is_red' (boolean) and 'confidence' (number between 0 and 1). "
                "Any response that is not valid JSON is a failure."
            ),
            user_prompt=(
                "Look at the LPG auto-switcher indicator window (small plastic window on the device). "
                "Is it red?\n"
                "Return ONLY this JSON shape:\n"
                "{\"is_red\": <true_or_false>, \"confidence\": <0_to_1>}\n"
                "No markdown. No triple backticks. No extra text."
            ),
        )

        is_red, confidence = update_lpg_auto_switcher_ha_entity(detection_result)
        return jsonify({"is_red": is_red, "confidence": confidence}), 200

    except Exception as ex:
        logger.exception(f"Analysis workflow failed: {ex}")
        return jsonify({"error": str(ex)}), 500


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    # (Note: code after app.run won't execute; kept for parity with original)
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        logger.info(f"{rule.endpoint:20s} {methods:10s} {rule}")
