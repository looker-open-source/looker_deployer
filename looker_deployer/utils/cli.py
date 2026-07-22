# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import os
import re
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.exceptions import LookerCLIError, sanitize_command
import urllib.parse

logger = deploy_logging.get_logger(__name__)


def inject_auth_flags(cmd, creds):
    """
    Parses creds dict and injects them as global flags into the looker-cli command.
    """
    if not isinstance(cmd, list):
        return cmd

    if not isinstance(creds, dict):
        return cmd

    cmd = list(cmd)
    auth_flags = []

    base_url = creds.get("base_url")
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    verify_ssl = creds.get("verify_ssl")
    host = creds.get("host")
    port = creds.get("port")

    if base_url:
        # Handle cases where base_url has no scheme prefix
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            parsed = urllib.parse.urlparse("https://" + base_url)
        else:
            parsed = urllib.parse.urlparse(base_url)

        host = parsed.hostname
        port = parsed.port

        if parsed.scheme == "http":
            auth_flags.append("--ssl=false")

    if host:
        auth_flags.extend(["--host", host])
    if port:
        auth_flags.extend(["--port", str(port)])

    token = creds.get("token")
    if token:
        auth_flags.extend(["--token", token])
    else:
        if client_id:
            auth_flags.extend(["--client-id", client_id])
        if client_secret:
            auth_flags.extend(["--client-secret", client_secret])

    if verify_ssl:
        val = str(verify_ssl).lower()
        if val == "false":
            auth_flags.append("--verify-ssl=false")

    if auth_flags:
        cli_idx = -1
        for i, arg in enumerate(cmd):
            # Strip trailing .exe, .bat, or .cmd extensions case-insensitively
            normalized_arg = re.sub(r"\.(exe|bat|cmd)$", "", arg, flags=re.IGNORECASE)
            if normalized_arg == "looker-cli" or normalized_arg.endswith("/looker-cli") or normalized_arg.endswith("\\looker-cli"):
                cli_idx = i
                break
        if cli_idx != -1:
            cmd = cmd[:cli_idx + 1] + auth_flags + cmd[cli_idx + 1:]

    return cmd


def is_windows():
    return os.name == "nt"


def run_cli_command(cmd, creds=None, **kwargs):
    """
    Wrapper for subprocess.run that executes looker-cli commands.
    Automatically handles Windows execution wrapping and raises descriptive
    exceptions if looker-cli is not found.
    Automatically injects authentication flags from creds dict.
    Enforces a default timeout of 60 seconds if not specified.
    Raises LookerCLIError if the command fails.
    """
    if isinstance(cmd, list):
        if creds:
            cmd = inject_auth_flags(cmd, creds)

        if is_windows():
            if not (len(cmd) >= 2 and cmd[0] == "cmd.exe" and cmd[1] == "/c"):
                cmd = ["cmd.exe", "/c"] + cmd

    # Pop 'check' because we handle error checking manually to raise LookerCLIError
    # Default to True to enforce error checking
    check = kwargs.pop("check", True)

    # Ensure we capture output by default if not specified, so we can populate exceptions
    if "capture_output" not in kwargs and "stdout" not in kwargs and "stderr" not in kwargs:
        kwargs["capture_output"] = True

    # Enforce default timeout of 60 seconds if not specified
    kwargs.setdefault("timeout", 60)

    try:
        result = subprocess.run(cmd, **kwargs)
    except FileNotFoundError as e:
        msg = f"looker-cli command not found (No such file or directory): {sanitize_command(cmd)}. Please ensure looker-cli is installed and in your PATH."
        logger.error(msg)
        raise FileNotFoundError(msg) from e
    except subprocess.TimeoutExpired as e:
        msg = f"looker-cli command timed out after {e.timeout} seconds: {sanitize_command(cmd)}."
        logger.error(msg)
        raise subprocess.TimeoutExpired(e.cmd, e.timeout, output=e.output, stderr=e.stderr) from e

    if check and result.returncode != 0:
        stdout_val = result.stdout
        stderr_val = result.stderr
        if isinstance(stdout_val, bytes):
            stdout_val = stdout_val.decode("utf-8", errors="replace")
        if isinstance(stderr_val, bytes):
            stderr_val = stderr_val.decode("utf-8", errors="replace")

        raise LookerCLIError(
            command=" ".join(cmd) if isinstance(cmd, list) else cmd,
            exit_code=result.returncode,
            stdout=stdout_val,
            stderr=stderr_val
        )

    return result
