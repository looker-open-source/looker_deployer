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

import re


def sanitize_command(command):
    if isinstance(command, list):
        command = " ".join(command)
    if not isinstance(command, str):
        return str(command)
    # Scrub sensitive flags (--client-secret, --token, --client-id) followed by space or equals
    return re.sub(r"((?:--client-secret|--token|--client-id)(?:\s+|=))[^\s]+", r"\1******", command)


class LookerCLIError(Exception):
    """Exception raised when a looker-cli command execution fails."""
    def __init__(self, command, exit_code, stdout, stderr):
        self.command = sanitize_command(command)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        message = f"Command '{self.command}' failed with exit code {exit_code}.\nStdout: {stdout}\nStderr: {stderr}"
        super().__init__(message)
