import requests
import time
import pytest
import subprocess

SERVICE_IP = subprocess.check_output(
    [
        'microk8s',
        'kubectl',
        'get',
        '-n',
        'ci-test',
        'service/tf-serving',
        '-o=jsonpath={.spec.clusterIP}',
    ]
).decode('utf-8')


def setup_module(module):
    url = 'http://%s:9001/v1/models/saved_model_half_plus_two_cpu' % SERVICE_IP

    for _ in range(30):
        try:
            response = requests.get(url)
            response.raise_for_status()
            break
        except Exception as err:
            print(err)
            time.sleep(5)
    else:
        pytest.fail("Waited too long for model to get served.")


def test_status():
    url = 'http://%s:9001/v1/models/saved_model_half_plus_two_cpu' % SERVICE_IP

    response = requests.get(url)
    response.raise_for_status()

    assert response.json() == {
        "model_version_status": [
            {
                "version": "123",
                "state": "AVAILABLE",
                "status": {"error_code": "OK", "error_message": ""},
            }
        ]
    }


def test_prediction():
    url = 'http://%s:9001/v1/models/saved_model_half_plus_two_cpu:predict' % SERVICE_IP

    response = requests.post(url, json={"instances": [1, 2, 3]})
    response.raise_for_status()

    assert response.json() == {"predictions": [2.5, 3.0, 3.5]}
