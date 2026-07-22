import pytest
import os
import tempfile
import subprocess
from unittest.mock import patch
from looker_deployer.commands import deploy_connections


@pytest.fixture
def temp_dir_check():
    temp_dir = tempfile.gettempdir()
    files_before = set(os.listdir(temp_dir))
    yield
    files_after = set(os.listdir(temp_dir))
    new_files = files_after - files_before
    # Filter files that look like temporary files
    leaked_files = [f for f in new_files if f.startswith("tmp")]

    # Cleanup any leaked files
    for f in leaked_files:
        try:
            os.remove(os.path.join(temp_dir, f))
        except OSError:
            pass

    assert not leaked_files, f"Leaked temporary files: {leaked_files}"


def test_stress_serialization_error(temp_dir_check):
    # Pass a non-serializable object (a set) to force TypeError in json.dump
    connections = [{"name": "Taco", "value": {1, 2, 3}}]
    with pytest.raises(TypeError):
        deploy_connections.write_connections(connections, {"ENV": "2"})


def test_stress_io_error_during_write(temp_dir_check):
    connections = [{"name": "Taco"}]
    # Patch json.dumps to raise an IOError to simulate serializing/write failure
    with patch("looker_deployer.commands.deploy_connections.json.dumps", side_effect=IOError("Mock Disk Full")):
        with pytest.raises(IOError, match="Mock Disk Full"):
            deploy_connections.write_connections(connections, {"ENV": "2"})


def test_stress_subprocess_not_found(temp_dir_check):
    connections = [{"name": "Taco"}]
    # We patch subprocess.run to raise FileNotFoundError (simulating command not found)
    with patch("looker_deployer.commands.deploy_connections.subprocess.run", side_effect=FileNotFoundError(2, "No such file or directory")):
        with pytest.raises(FileNotFoundError):
            deploy_connections.write_connections(connections, {"ENV": "2"})


def test_stress_subprocess_called_process_error(temp_dir_check):
    connections = [{"name": "Taco"}]
    # We patch subprocess.run to raise CalledProcessError (simulating command returning non-zero exit status)
    with patch("looker_deployer.commands.deploy_connections.subprocess.run", side_effect=subprocess.CalledProcessError(1, "looker-cli")):
        with pytest.raises(subprocess.CalledProcessError):
            deploy_connections.write_connections(connections, {"ENV": "2"})


def test_stress_subprocess_generic_exception(temp_dir_check):
    connections = [{"name": "Taco"}]
    # General unexpected exception during execution
    with patch("looker_deployer.commands.deploy_connections.subprocess.run", side_effect=RuntimeError("Subprocess crashed")):
        with pytest.raises(RuntimeError, match="Subprocess crashed"):
            deploy_connections.write_connections(connections, {"ENV": "2"})
