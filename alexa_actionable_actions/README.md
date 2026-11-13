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

The secret starts with the placeholder `REPLACE_WITH_NEW_HOME_ASSISTANT_TOKEN`. In Secrets Manager, replace its value with a newly generated Home Assistant long-lived access token as plain text. Do not put the token in this repository, a command line, or the CloudFormation template. The function reads the secret for each Alexa request, so updates apply on the next request. Keep the current Alexa endpoint until the new function can reach Home Assistant; then copy the stack's `LambdaFunctionArn` output into Alexa Developer Console > Build > Endpoint.

`ENABLE_COMMANDS` remains false. The Lambda role has no Home Assistant or other AWS data access. The Alexa invoke permission allows only the configured skill ID.

To change the skill ID or Home Assistant URL, set `ALEXA_SKILL_ID` or `HOME_ASSISTANT_URL` before running the deployment script. The script refuses to deploy outside the personal AWS account above.

## Source and license

The vendored source is from [keatontaylor/alexa-actions](https://github.com/keatontaylor/alexa-actions), pinned to the revision above. See [LICENSE](LICENSE). Do not remove its license or attribution notices.
