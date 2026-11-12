#!/usr/bin/env python3
"""Open a Compose PR, then deploy its merged image tag through Synology Docker."""

import base64
import fcntl
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path("/config")
STATUS = CONFIG / "www/home_assistant_upgrade/status.json"
LOCK = CONFIG / ".home_assistant_upgrade.lock"
COMPOSE_PATH = "hass/docker-compose.yaml"
REPO = "ohadbenita/docker-config"
HOST_COMPOSE_DIR = "/volume1/Media/SmartHome/Backup/docker-compose"
HOST_CONFIG_DIR = "/volume1/Media/SmartHome/Config/HASS"
COMPOSE_HELPER_IMAGE = "docker:cli"
IMAGE_PATTERN = re.compile(
    r"(?m)^(\s*image:\s*homeassistant/home-assistant:)([^\s#]+)"
)
VERSION_PATTERN = re.compile(r"^\d{4}\.\d{1,2}\.\d+$")


def write_status(
    status, message, version=None, pull_request=None, pull_request_number=None
):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    data = {"status": status, "message": message}
    if version:
        data["version"] = version
    if pull_request:
        data["pull_request"] = pull_request
    if pull_request_number:
        data["pull_request_number"] = pull_request_number
    temporary = STATUS.with_suffix(".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    temporary.replace(STATUS)


def github_request(path, method="GET", payload=None, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Home-Assistant-upgrade-button",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    request = urllib.request.Request(
        f"https://api.github.com{path}", data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except ValueError:
            pass
        raise RuntimeError(f"GitHub API returned {error.code}: {detail}") from None


def read_secret(name):
    # Home Assistant already stores GitHub credentials in this protected file.
    import yaml

    with (CONFIG / "secrets.yaml").open(encoding="utf-8") as source:
        value = yaml.safe_load(source).get(name)
    if not value:
        raise RuntimeError(f"Missing Home Assistant secret: {name}")
    return value


def latest_version(token):
    _, release = github_request("/repos/home-assistant/core/releases/latest", token=token)
    version = release.get("tag_name", "").removeprefix("v")
    if not VERSION_PATTERN.fullmatch(version):
        raise RuntimeError("GitHub returned an invalid Home Assistant release tag.")
    return version


def get_compose(ref, token):
    quoted_path = urllib.parse.quote(COMPOSE_PATH, safe="/")
    query = urllib.parse.urlencode({"ref": ref})
    _, file_info = github_request(
        f"/repos/{REPO}/contents/{quoted_path}?{query}", token=token
    )
    content = base64.b64decode(file_info["content"]).decode("utf-8")
    return content, file_info["sha"]


def compose_version(content):
    matches = list(IMAGE_PATTERN.finditer(content))
    if len(matches) != 1:
        raise RuntimeError("Compose file must contain exactly one Home Assistant image.")
    return matches[0].group(2)


def open_or_create_pr(latest, token):
    branch = f"codex/home-assistant-{latest}"
    query = urllib.parse.urlencode({
        "state": "open",
        "head": f"ohadbenita:{branch}",
        "base": "master",
    })
    _, prs = github_request(f"/repos/{REPO}/pulls?{query}", token=token)
    if prs:
        return prs[0]

    _, master = github_request(f"/repos/{REPO}/git/ref/heads/master", token=token)
    try:
        github_request(
            f"/repos/{REPO}/git/ref/heads/{urllib.parse.quote(branch, safe='/')}",
            token=token,
        )
    except RuntimeError as error:
        if "404" not in str(error):
            raise
        github_request(
            f"/repos/{REPO}/git/refs",
            method="POST",
            token=token,
            payload={"ref": f"refs/heads/{branch}", "sha": master["object"]["sha"]},
        )

    content, file_sha = get_compose(branch, token)
    updated = IMAGE_PATTERN.sub(rf"\g<1>{latest}", content)
    if updated != content:
        github_request(
            f"/repos/{REPO}/contents/{COMPOSE_PATH}",
            method="PUT",
            token=token,
            payload={
                "message": f"Update Home Assistant to {latest}",
                "content": base64.b64encode(updated.encode()).decode(),
                "sha": file_sha,
                "branch": branch,
            },
        )
    _, pr = github_request(
        f"/repos/{REPO}/pulls",
        method="POST",
        token=token,
        payload={
            "title": f"Update Home Assistant to {latest}",
            "head": branch,
            "base": "master",
            "body": (
                f"Update the Synology Home Assistant image to {latest}. "
                "After merging, press **Upgrade Home Assistant** again in the "
                "Monitoring dashboard to apply this Compose version on Synology."
            ),
        },
    )
    return pr


def wait_for_merge(pull_request, version, token):
    number = pull_request["number"]
    url = pull_request["html_url"]
    write_status(
        "waiting_for_merge",
        f"Compose PR #{number} is ready. Merge it to continue the upgrade.",
        version,
        url,
        number,
    )
    while True:
        _, current_pr = github_request(
            f"/repos/{REPO}/pulls/{number}", token=token
        )
        if current_pr.get("merged_at"):
            break
        if current_pr.get("state") == "closed":
            write_status(
                "failed",
                f"Compose PR #{number} closed without a merge. Tap to start again.",
                version,
                url,
                number,
            )
            return None
        time.sleep(60)

    merged_compose, _ = get_compose("master", token)
    merged_version = compose_version(merged_compose)
    if merged_version != version:
        write_status(
            "failed",
            f"Compose PR #{number} merged, but master now targets {merged_version}. Tap to check again.",
            version,
            url,
            number,
        )
        return None
    return merged_compose


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=30):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def docker_request(method, path, body=None, timeout=30):
    connection = UnixHTTPConnection("/var/run/docker.sock", timeout=timeout)
    headers = {}
    encoded = None
    if body is not None:
        encoded = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    connection.request(method, path, body=encoded, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    if response.status < 200 or response.status >= 300:
        detail = payload.decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Synology Docker API returned {response.status}: {detail}")
    return response.status, payload


def deploy(version, compose_content):
    helper_dir = CONFIG / "www/home_assistant_upgrade"
    helper_dir.mkdir(parents=True, exist_ok=True)
    (helper_dir / "docker-compose.yaml").write_text(compose_content, encoding="utf-8")
    write_status(
        "applying",
        f"Preparing the Synology deployment for Home Assistant {version}.",
        version,
    )

    image_query = urllib.parse.urlencode({"fromImage": "docker", "tag": "cli"})
    docker_request("POST", f"/images/create?{image_query}", timeout=900)
    write_status(
        "applying",
        f"Docker helper is ready. Updating Home Assistant {version} on Synology.",
        version,
    )
    compose_command = (
        "docker compose --project-name hass --project-directory /repo/hass "
        "-f /upgrade/docker-compose.yaml up -d --pull always --no-deps homeassistant"
    )
    success = json.dumps({
        "status": "success",
        "message": f"Home Assistant {version} is running on Synology.",
        "version": version,
    })
    failure = json.dumps({
        "status": "failed",
        "message": f"Synology could not apply Home Assistant {version}; see deploy.log in the upgrade folder.",
        "version": version,
    })
    command = (
        f"{compose_command} > /upgrade/deploy.log 2>&1; result=$?; "
        f"if [ \"$result\" -eq 0 ]; then printf '%s\\n' '{success}' > /upgrade/status.json; "
        f"else printf '%s\\n' '{failure}' > /upgrade/status.json; fi; exit \"$result\""
    )
    _, created = docker_request(
        "POST",
        "/containers/create",
        body={
            "Image": COMPOSE_HELPER_IMAGE,
            "Entrypoint": ["sh"],
            "Cmd": ["-c", command],
            "HostConfig": {
                "Binds": [
                    "/var/run/docker.sock:/var/run/docker.sock",
                    f"{HOST_COMPOSE_DIR}:/repo:ro",
                    f"{HOST_CONFIG_DIR}/www/home_assistant_upgrade:/upgrade:rw",
                ],
                "AutoRemove": True,
            },
        },
    )
    container_id = json.loads(created)["Id"]
    docker_request("POST", f"/containers/{container_id}/start")


def run_upgrade():
    token = read_secret("github_access_token")
    latest = latest_version(token)
    master_compose, _ = get_compose("master", token)
    current = compose_version(master_compose)
    if current != latest:
        if tuple(map(int, current.split("."))) > tuple(map(int, latest.split("."))):
            write_status("current", f"Compose already targets {current}.", current)
            return
        pull_request = open_or_create_pr(latest, token)
        master_compose = wait_for_merge(pull_request, latest, token)
        if master_compose is None:
            return

    deploy(latest, master_compose)


def start():
    with LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        write_status("running", "Checking the latest Home Assistant release and Compose PR.")
        child = subprocess.Popen(
            [sys.executable, __file__, "run"],
            stdin=subprocess.DEVNULL,
            stdout=open(CONFIG / "home_assistant_upgrade.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
        del child


def run():
    try:
        with LOCK.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            run_upgrade()
    except Exception as error:
        write_status("failed", f"Upgrade request failed: {error}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"start", "run"}:
        raise SystemExit("Use: home_assistant_upgrade.py start|run")
    start() if sys.argv[1] == "start" else run()
