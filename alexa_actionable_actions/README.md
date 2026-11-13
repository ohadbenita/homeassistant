# Alexa Actionable Actions: Python 3.13 deployment

This folder contains the self-managed AWS Lambda deployment for the existing Alexa skill. It uses the upstream Alexa Actions backend at commit `af4963710dcf5ebbd8191483519aab9379473edb` and its supplied license.

## Build

Build the complete dependency ZIP with Python 3.13:

```sh
python3.13 scripts/build_package.py --kind pure --output dist
```

The resulting ZIP includes the skill handler and pinned runtime dependencies. It has no Home Assistant token.

## Deploy

Use AWS credentials for account `701255146615` in `us-east-1`, then run:

```sh
./deploy.sh --confirm-security-changes
```

The deployment creates a CloudFormation-managed private, encrypted, versioned S3 package bucket in its own bootstrap stack, then creates a Python 3.13 Lambda function, a 14-day CloudWatch log group, one Secrets Manager secret, a Lambda role limited to writing that function's logs and reading only that secret, and an invoke permission restricted to the Alexa skill ID in the main stack. Keep the artifact stack: it stores deployment ZIPs and older versions for rollback. Empty its bucket before deleting the stack. The secret is retained if the main stack is deleted, so remove it separately if you later retire this deployment. Secrets Manager has a monthly charge.

The main stack also creates a CloudWatch alarm on the Alexa Lambda's `Errors` metric (one-minute period, one error by default). A small API Gateway endpoint reads that alarm's current state and returns HTTP 503 while it is active and HTTP 200 after it recovers. Configure an HTTP monitor in UptimeRobot using the `UptimeRobotMonitorUrl` stack output. UptimeRobot's check interval and retry policy determine how quickly it reports and clears an incident. A monitor alert is resolved when a successful HTTP check confirms the endpoint is healthy; the monitor itself remains enabled.

The API Gateway resource policy allows only UptimeRobot's published checker IPs. `deploy.sh` fetches the official IP list each time it runs, validates it, reports whether its SHA-256 version changed, and applies the ranges through CloudFormation. CloudFormation outputs the deployed version as `UptimeRobotIpListVersion`. The list is refreshed on deployment; there is no scheduled checker or automatic notification between deployments. The deployment function only runs when CloudFormation creates or updates the API stage.

Set `MONITOR_ALARM_THRESHOLD` if you want a different error count threshold before deploying. The endpoint returns only the alarm state and accepts requests from the UptimeRobot checker IPs in the API resource policy.

The monitor uses the custom URL `https://status.benita.click/alexa/status`. The API Gateway custom domain and `alexa` base path mapping are managed by the main CloudFormation stack. `benita.click` uses Cloudflare DNS, so request an ACM certificate in `us-east-1` for `status.benita.click`, add its validation CNAME in Cloudflare as DNS only, and wait for ACM to issue it. Then deploy with `API_CUSTOM_DOMAIN_CERTIFICATE_ARN` set to that certificate ARN. After deployment, add a DNS-only CNAME for `status` in Cloudflare pointing to the `ApiCustomDomainRegionalDomainName` stack output. Keep it DNS only so API Gateway sees UptimeRobot's checker IP instead of Cloudflare proxy addresses.

The secret starts with the placeholder `REPLACE_WITH_NEW_HOME_ASSISTANT_TOKEN`. In Secrets Manager, replace its value with a newly generated Home Assistant long-lived access token as plain text. Do not put the token in this repository, a command line, or the CloudFormation template. The function reads the secret for each Alexa request, so updates apply on the next request. Keep the current Alexa endpoint until the new function can reach Home Assistant; then copy the stack's `LambdaFunctionArn` output into Alexa Developer Console > Build > Endpoint.

`ENABLE_COMMANDS` remains false. The Lambda role has no Home Assistant or other AWS data access. The Alexa invoke permission allows only the configured skill ID.

To change the skill ID or Home Assistant URL, set `ALEXA_SKILL_ID` or `HOME_ASSISTANT_URL` before running the deployment script. The script refuses to deploy outside the personal AWS account above.

## Source and license

The vendored source is from [keatontaylor/alexa-actions](https://github.com/keatontaylor/alexa-actions), pinned to the revision above. See [LICENSE](LICENSE). Do not remove its license or attribution notices.
