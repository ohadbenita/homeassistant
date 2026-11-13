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
  --parameter-overrides PackageBucket="$BUCKET" PackageKey="$PACKAGE_KEY" SkillId="$SKILL_ID" HomeAssistantUrl="$HA_URL" MonitorAlarmThreshold="$MONITOR_ALARM_THRESHOLD"

echo "CloudFormation-managed package bucket: ${BUCKET} (versioning retains previous ZIPs)."
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
  --query 'Stacks[0].Outputs' --output table
