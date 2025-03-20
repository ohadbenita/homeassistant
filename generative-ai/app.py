import base64
import json
import logging
import os
import time
from typing import Dict, Any, Tuple

import boto3
import requests
from flask import Flask, jsonify

# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Environment Variables
# ---------------------------------------------------------
HA_BASE_URL = os.environ.get("HA_BASE_URL").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN")
CLOTHES_RACK_CAMERA_ENTITY_ID = os.environ.get("CLOTHES_RACK_CAMERA_ENTITY_ID")
CLOTHES_RACK_TARGET_ENTITY_ID = os.environ.get("CLOTHES_RACK_TARGET_ENTITY_ID")
GAS_HEATER_CAMERA_ENTITY_ID = os.environ.get("GAS_HEATER_CAMERA_ENTITY_ID")
GAS_HEATER_TARGET_ENTITY_ID = os.environ.get("GAS_HEATER_TARGET_ENTITY_ID")

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

# Basic validation
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


def get_short_lived_token(camera_entity_id: str) -> str:
    """
    Retrieve the short-lived token stored in a sensor entity.
    For a camera entity like 'camera.front_porch_and_parking_clear',
    we assume there's a sensor entity named 'sensor.front_porch_and_parking_clear_token'.
    """
    # e.g., camera.front_porch_and_parking_clear -> sensor.front_porch_and_parking_clear_token
    if "." not in camera_entity_id:
        raise ValueError(
            f"Camera entity '{camera_entity_id}' is invalid. "
            "Must have a domain prefix (e.g., 'camera.')."
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
    to fetch the snapshot image for the given camera entity.
    Returns the raw image bytes if successful.
    """
    short_lived_token = get_short_lived_token(camera_entity_id)

    # e.g. http://<HA>:8123/api/camera_proxy/camera.front_porch_and_parking_clear?token=<short_lived_token>
    snapshot_url = (
        f"{HA_BASE_URL}/api/camera_proxy/{camera_entity_id}?token={short_lived_token}"
    )
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}

    logger.info(f"Requesting camera snapshot from {snapshot_url}")
    resp = requests.get(snapshot_url, headers=headers, timeout=10)
    if resp.status_code == 200:
        logger.info("Snapshot fetched successfully from Home Assistant.")
        return resp.content
    else:
        raise ConnectionError(
            f"Failed to retrieve snapshot. Status: {resp.status_code}, Response: {resp.text}"
        )


def analyze_image_with_bedrock(
    image_bytes: bytes, system_prompt: str, user_prompt: str
) -> Dict[str, Any]:
    """
    Send the base64-encoded image to AWS Bedrock for analysis.
    Assumes the model returns JSON with 'detected' (bool) and 'confidence' (float).
    Returns tuple: (detected, confidence).
    """
    if not BEDROCK_MODEL_ID:
        raise EnvironmentError("AWS Bedrock Model ID is not configured.")

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    system_prompt = [{"text": system_prompt}]

    user_message = [
        {
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": "jpg",  # image format, e.g. jpg or png
                        "source": {"bytes": base64_image},
                    }
                },
                {"text": user_prompt},
            ],
        }
    ]

    payload = {
        "schemaVersion": "messages-v1",
        "messages": user_message,
        "system": system_prompt,
    }

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

    # The response body is a streaming object; read and decode it
    response_body = response.get("body")
    if not response_body:
        raise ValueError("No body in Bedrock response.")

    response_data = response_body.read().decode("utf-8")
    try:
        result = json.loads(response_data)
    except json.JSONDecodeError:
        logger.error(f"Bedrock response invalid JSON: {response_data}")
        raise ValueError("Bedrock response not valid JSON.")

    logger.info(f"Bedrock analysis result -> {result}")
    return result


def update_clothes_rack_ha_entity(result: Dict[str, Any]) -> Tuple[bool, float]:
    """
    Update a Home Assistant entity with the detection results.
    """
    if not (HA_BASE_URL and HA_TOKEN and CLOTHES_RACK_TARGET_ENTITY_ID):
        logger.warning("Cannot update entity. Missing HA config or target entity.")
        raise ValueError("Cannot update entity. Missing HA config or target entity.")

    # For a binary sensor style: 'on' if True, 'off' if False
    detection_result = json.loads(result["output"]["message"]["content"][0]["text"])
    is_detected = detection_result["detected"]
    confidence = detection_result["confidence"]
    state_value = "on" if is_detected else "off"
    attributes = {
        "device_class": "occupancy",
        "detected": is_detected,
        "confidence": round(confidence, 3),
        "updated_at": int(time.time()),
        "input_tokens": result["usage"]["inputTokens"],
        "output_tokens": result["usage"]["outputTokens"],
        "stop_reason": result["stopReason"],
    }

    url = f"{HA_BASE_URL}/api/states/{CLOTHES_RACK_TARGET_ENTITY_ID}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"state": state_value, "attributes": attributes}

    resp = requests.post(url, headers=headers, json=data, timeout=5)
    if resp.status_code in (200, 201):
        logger.info(
            f"Successfully updated '{CLOTHES_RACK_TARGET_ENTITY_ID}' with detected={is_detected}, "
            f"confidence={confidence:.3f}."
        )
    else:
        logger.error(
            f"Failed to update entity '{CLOTHES_RACK_TARGET_ENTITY_ID}'. Status: {resp.status_code}, Error: {resp.text}"
        )

    return is_detected, confidence


def update_gas_heater_display_ha_entity(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a Home Assistant entity with the detection results.
    """
    if not (HA_BASE_URL and HA_TOKEN and GAS_HEATER_TARGET_ENTITY_ID):
        logger.warning("Cannot update entity. Missing HA config or target entity.")
        raise ValueError("Cannot update entity. Missing HA config or target entity.")

    # For a binary sensor style: 'on' if True, 'off' if False
    detection_result = json.loads(result["output"]["message"]["content"][0]["text"])
    confidence = detection_result["confidence"]
    attributes = {
        "device_class": "temperature",
        "is_active": detection_result["is_active"],
        "temperature": detection_result["temperature"],
        "confidence": round(confidence, 3),
        "updated_at": int(time.time()),
        "input_tokens": result["usage"]["inputTokens"],
        "output_tokens": result["usage"]["outputTokens"],
        "stop_reason": result["stopReason"],
    }

    url = f"{HA_BASE_URL}/api/states/{GAS_HEATER_TARGET_ENTITY_ID}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"state": detection_result["state"], "attributes": attributes}

    resp = requests.post(url, headers=headers, json=data, timeout=5)
    if resp.status_code in (200, 201):
        logger.info(
            f"Successfully updated '{GAS_HEATER_TARGET_ENTITY_ID}' with data={data}, "
            f"confidence={confidence:.3f}."
        )
    else:
        logger.error(
            f"Failed to update entity '{CLOTHES_RACK_TARGET_ENTITY_ID}'. Status: {resp.status_code}, Error: {resp.text}"
        )

    return data


@app.route("/analyze/clothes-rack", methods=["GET"])
def analyze_clothes_rack():
    """
    Flask endpoint to capture, analyze, and update the detection results in Home Assistant.
    """
    try:
        image_bytes = capture_image_from_ha(CLOTHES_RACK_CAMERA_ENTITY_ID)
        detection_result = analyze_image_with_bedrock(
            image_bytes=image_bytes,
            system_prompt=(
                "You are an image analysis expert. "
                "Identify if an image contains a clothes drying rack with clothes on it. "
                "Respond **only** in JSON with keys 'detected' (boolean) and 'confidence' (0 to 1)."
                "Don't include any other markdown or text in your response such as ```json"
            ),
            user_prompt=(
                "Does this image contain a clothes drying rack with clothes on it? "
                "Answer with a JSON object containing 'detected' and 'confidence' and "
                "nothing else but these fields."
            ),
        )
        is_detected, confidence = update_clothes_rack_ha_entity(detection_result)

        return jsonify({"detected": is_detected, "confidence": confidence}), 200

    except Exception as ex:
        logger.error(f"Analysis workflow failed: {ex}")
        return jsonify({"error": str(ex)}), 500


@app.route("/analyze/gas-heater-display", methods=["GET"])
def analyze_gas_heater_display():
    """
    Flask endpoint to capture, analyze, and update the detection results in Home Assistant.
    """
    try:
        image_bytes = capture_image_from_ha(GAS_HEATER_CAMERA_ENTITY_ID)
        detection_result = analyze_image_with_bedrock(
            image_bytes=image_bytes,
            system_prompt=(
                "You are an image analysis expert. "
                "Identify if the image contains a number, a red dot and a green dot. "
                "Respond **only** in JSON with keys 'temperature' (integer) 'is_active' for the green "
                "dot ('on' if there is a green dot, 'off' if there isn't) and 'state' for the red "
                "dot ('on' if there is a green dot, 'off' if there isn't) and 'confidence' (0 to 1)"
                "Don't include any other markdown or text in your response such as ```json"
            ),
            user_prompt=(
                "Parse the image provided and check for a number, red dot and green dot."
                "Answer with a JSON object containing 'temperature', 'is_active', 'state' and 'confidence' "
                "and nothing else but these fields."
            ),
        )
        data_sent = update_gas_heater_display_ha_entity(detection_result)

        return jsonify(data_sent, 200)

    except Exception as ex:
        logger.error(f"Analysis workflow failed: {ex}")
        return jsonify({"error": str(ex)}), 500


if __name__ == "__main__":
    # Run the Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
