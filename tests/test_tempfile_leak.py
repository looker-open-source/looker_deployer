import pytest
import os
import tempfile
from looker_deployer.commands import deploy_connections


def test_write_connections_leak_on_json_dump_error():
    # We pass a set in connections, which is not JSON serializable.
    # This should cause json.dump to raise TypeError.
    connections = [{"name": "Taco", "value": {1, 2, 3}}]

    # Let's count files in temp directory before the call
    temp_dir = tempfile.gettempdir()
    files_before = set(os.listdir(temp_dir))

    with pytest.raises(TypeError):
        deploy_connections.write_connections(connections, {"ENV": "2"})

    files_after = set(os.listdir(temp_dir))
    new_files = files_after - files_before

    # Check if any new temp files starting with 'tmp' (default prefix for NamedTemporaryFile) were leaked
    leaked_files = [f for f in new_files if f.startswith("tmp")]

    # Clean up any leaked files so we don't pollute the test environment
    for f in leaked_files:
        try:
            os.remove(os.path.join(temp_dir, f))
        except OSError:
            pass

    assert not leaked_files, f"Leaked temporary files: {leaked_files}"
