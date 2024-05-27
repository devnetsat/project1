import csv
import pytest
from utils.ssh_client import SSHClient

def read_test_config(file_path):
    test_config = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            test_config.append(row)
    return test_config

def read_expected_outputs(file_path):
    expected_outputs = {}
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            test_case = row['Test Case Name']
            expected_output = row['Expected Output']
            expected_outputs[test_case] = expected_output
    return expected_outputs

@pytest.fixture(scope='session')
def test_config():
    return read_test_config('data/test_config.csv')

@pytest.fixture(scope='session')
def expected_outputs():
    return read_expected_outputs('data/expected_outputs.csv')

@pytest.mark.parametrize("command", [
    "show version",
    "show running-config",
    "show vlan",
    "show ip route"
])
def test_device_commands(test_config, expected_outputs, command):
    for device in test_config:
        hostname = device['Device Hostname']
        device_ip = device['Device IP']
        group = device['Group']
        excluded_tests = device.get('Excluded Tests', '').split(',') if device.get('Excluded Tests') else []

        # If the command is in the excluded tests list, skip the test
        if command in excluded_tests:
            continue

        # Perform actions to get output
        ssh_client = SSHClient(hostname, username, password)
        output = ssh_client.run_command(command)

        # Validate output based on expected output
        test_case_name = f"test_{command.replace(' ', '_')}"
        expected_output = expected_outputs.get(test_case_name)
        assert output == expected_output, f"Expected output mismatch for {test_case_name} on {hostname}"
