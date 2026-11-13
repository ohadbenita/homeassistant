#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-AlexaActionableActionsPython313}"
ARTIFACT_STACK_NAME="${ARTIFACT_STACK_NAME:-AlexaActionableActionsArtifacts}"
SKILL_ID="${ALEXA_SKILL_ID:-amzn1.ask.skill.d3fbfb9e-b9aa-454c-8f34-0da94050c526}"
HA_URL="${HOME_ASSISTANT_URL:-https://hass.benita.click}"
MONITOR_ALARM_THRESHOLD="${MONITOR_ALARM_THRESHOLD:-1}"
EXPECTED_ACCOUNT="701255146615"

if [[ "${1:-}" != "--confirm-security-changes" ]]; then
  echo "Refusing to deploy without --confirm-security-changes."
  echo "This creates a Lambda role with log-write and one-secret read access, and lets only skill ${SKILL_ID} invoke the function."
  exit 2
fi

cd "$ROOT"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
if [[ "$ACCOUNT_ID" != "$EXPECTED_ACCOUNT" ]]; then
  echo "Wrong AWS account: expected ${EXPECTED_ACCOUNT}, got ${ACCOUNT_ID}." >&2
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  python3.13 -m venv "$ROOT/.venv"
fi
UPTIMEROBOT_RANGES="$("$ROOT/.venv/bin/python" - <<'PY'
import ipaddress
import hashlib
import json
from urllib.request import urlopen

with urlopen("https://api.uptimerobot.com/meta/ips", timeout=20) as response:
    prefixes = json.load(response)["prefixes"]

ipv4 = sorted({item["ip_prefix"] for item in prefixes if item.get("service") == "checker" and "ip_prefix" in item})
ipv6 = sorted({item["ipv6_prefix"] for item in prefixes if item.get("service") == "checker" and "ipv6_prefix" in item})
if not ipv4 or not ipv6:
    raise SystemExit("UptimeRobot returned an empty checker IP list.")
for prefix in ipv4 + ipv6:
    ipaddress.ip_network(prefix, strict=True)

policy = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Principal": "*", "Action": "execute-api:Invoke", "Resource": "execute-api:/*",
         "Condition": {"IpAddress": {"aws:SourceIp": ipv4}}},
        {"Effect": "Allow", "Principal": "*", "Action": "execute-api:Invoke", "Resource": "execute-api:/*",
         "Condition": {"IpAddress": {"aws:SourceIp": ipv6}}},
    ],
}
if len(json.dumps(policy, separators=(",", ":")).encode()) > 8192:
    raise SystemExit("UptimeRobot checker IP policy exceeds API Gateway's 8 KB limit.")
version = hashlib.sha256((",".join(ipv4 + ipv6)).encode()).hexdigest()
print("\t".join((",".join(ipv4), ",".join(ipv6), version)))
PY
)"
IFS=$'\t' read -r UPTIMEROBOT_IPV4_RANGES UPTIMEROBOT_IPV6_RANGES UPTIMEROBOT_IP_LIST_VERSION <<< "$UPTIMEROBOT_RANGES"
CURRENT_UPTIMEROBOT_IP_LIST_VERSION="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
  --query "Stacks[0].Parameters[?ParameterKey=='UptimeRobotIpListVersion'].ParameterValue | [0]" --output text 2>/dev/null || true)"
if [[ "$CURRENT_UPTIMEROBOT_IP_LIST_VERSION" == "$UPTIMEROBOT_IP_LIST_VERSION" ]]; then
  echo "UptimeRobot checker IP list unchanged (${UPTIMEROBOT_IP_LIST_VERSION})."
else
  echo "UptimeRobot checker IP list changed; updating CloudFormation policy."
fi
"$ROOT/.venv/bin/python" scripts/build_package.py --kind pure --output dist
PACKAGE_KEY="lambda/AlexaActionsNoBinaryLinux.zip"

aws cloudformation deploy \
  --template-file artifacts-template.yaml \
  --stack-name "$ARTIFACT_STACK_NAME" \
  --region "$REGION"

BUCKET="$(aws cloudformation describe-stacks --stack-name "$ARTIFACT_STACK_NAME" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ArtifactBucketName'].OutputValue | [0]" --output text)"
aws s3api put-object --bucket "$BUCKET" --key "$PACKAGE_KEY" \
  --body dist/AlexaActionsNoBinaryLinux.zip --server-side-encryption AES256

aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides PackageBucket="$BUCKET" PackageKey="$PACKAGE_KEY" SkillId="$SKILL_ID" HomeAssistantUrl="$HA_URL" MonitorAlarmThreshold="$MONITOR_ALARM_THRESHOLD" UptimeRobotIPv4Ranges="$UPTIMEROBOT_IPV4_RANGES" UptimeRobotIPv6Ranges="$UPTIMEROBOT_IPV6_RANGES" UptimeRobotIpListVersion="$UPTIMEROBOT_IP_LIST_VERSION"

echo "CloudFormation-managed package bucket: ${BUCKET} (versioning retains previous ZIPs)."
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
  --query 'Stacks[0].Outputs' --output table
