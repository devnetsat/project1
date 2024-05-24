import os
import sys
import yaml
import pandas as pd
import importlib

def read_yaml(file_path):
    with open(file_path, 'r') as file):
        return yaml.safe_load(file)

def read_exclusions(exclusions_file):
    df = pd.read_excel(exclusions_file)
    exclusions = {}
    for _, row in df.iterrows():
        device_key = (row['ip'], row['device'], row['group'])
        exclusions[device_key] = set(map(int, row['exclude_tests'].split(',')))
    return exclusions

def get_test_case_runner(device_info, username, password, expected_output, testname):
    test_case_mapping = {
        "show_version": "ShowVersionRunner",
        "show_running_config": "ShowRunningConfigRunner",
        "system_status": "SystemStatusRunner"
    }

    if testname not in test_case_mapping:
        raise ValueError(f"Test case '{testname}' is not defined in the test case mapping.")
    
    classname = test_case_mapping[testname]
    module_name = f"testcase_runners.{classname.lower()}"
    module = importlib.import_module(module_name)
    runner_class = getattr(module, classname)
    return runner_class(device_info, username, password, expected_output, testname)

def main(testbed_file, testcase_file, exclusions_file, cluster_name, testcase_names=None):
    username = os.getenv('DEVICE_USERNAME')
    password = os.getenv('DEVICE_PASSWORD')

    if not username or not password:
        print("Error: DEVICE_USERNAME and DEVICE_PASSWORD environment variables must be set.")
        return

    testbed = read_yaml(testbed_file)
    testcases = read_yaml(testcase_file)
    exclusions = read_exclusions(exclusions_file)

    if not testcase_names or testcase_names.lower() == "all":
        testcase_names = [tc['testname'] for tc in testcases['testcases']]
    else:
        testcase_names = testcase_names.split(',')

    invalid_testcases = [name for name in testcase_names if name not in [tc['testname'] for tc in testcases['testcases']]]
    if invalid_testcases:
        print(f"Test cases not found: {', '.join(invalid_testcases)}")
        return

    if cluster_name not in testbed['clusters']:
        print(f"Cluster '{cluster_name}' not found in the testbed.")
        return

    cluster = testbed['clusters'][cluster_name]

    for device_name, device_info in cluster['devices'].items():
        device_key = (device_info['ip'], device_name, cluster_name)
        excluded_tests = exclusions.get(device_key, set())

        for testcase_name in testcase_names:
            testcase_info = next(tc for tc in testcases['testcases'] if tc['testname'] == testcase_name)
            test_id = testcase_info['testid']

            if test_id in excluded_tests:
                print(f"Skipping test {testcase_name} (ID: {test_id}) for device {device_name} ({device_info['ip']}) in group {cluster_name}")
                continue

            expected_output = testcase_info['expected_output']
            runner = get_test_case_runner(device_info, username, password, expected_output, testcase_name)
            results = runner.run_test_case()
            
            if results:
                print(f"Results for {device_name} ({testcase_info['testname']}):")
                for command, output in results.items():
                    print(f"Command/API Call: {command}")
                    print(f"Output: {output['stdout']}")
                    print(f"Test {'Passed' if output['success'] else 'Failed'}")
                    if not output['success']:
                        if isinstance(expected_output, dict):
                            print(f"Failed Key: {output['failed_key']}")
                        print(f"Expected: {expected_output}")
                        print(f"Actual: {output['stdout']}")

if __name__ == "__main__":
    if len(sys.argv) not in [5, 6]:
        print("Usage: python main.py <testbed_file> <testcase_file> <exclusions_file> <cluster_name> [<testcase_names>]")
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) == 6 else None)
