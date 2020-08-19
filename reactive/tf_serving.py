from charmhelpers.core import hookenv
from charms import layer
from charms.reactive import hook, set_flag, clear_flag, when, when_any, when_not


@hook("upgrade-charm")
def upgrade_charm():
    clear_flag("charm.started")


@when("charm.started")
def charm_ready():
    layer.status.active("")


@when_any("layer.docker-resource.oci-image.changed", "config.changed")
def update_image():
    clear_flag("charm.started")


@when("layer.docker-resource.oci-image.available")
@when_not("charm.started")
def start_charm():
    layer.status.maintenance("configuring container")

    image_info = layer.docker_resource.get_info("oci-image")

    config = dict(hookenv.config())

    model_conf = config["model-conf"]
    grpc_port = config["grpc-port"]
    rest_port = config["rest-port"]

    if config.get('model-conf'):
        hookenv.log(f"Serving models from {model_conf}")
        command_args = [f"--model_config_file=/models/{model_conf}"]
    elif config.get('model-base-path') and config.get('model-name'):
        hookenv.log(f"Serving single model `{config['model-name']}`")
        command_args = [
            f"--model_name={config['model-name']}",
            f"--model_base_path={config['model-base-path']}",
        ]
    else:
        layer.status.blocked('One of model-conf or model-base-path must be specified.')
        return False

    layer.caas_base.pod_spec_set(
        {
            "version": 2,
            "containers": [
                {
                    "name": "tf-serving",
                    "imageDetails": {
                        "imagePath": image_info.registry_path,
                        "username": image_info.username,
                        "password": image_info.password,
                    },
                    "command": [
                        "/usr/bin/tensorflow_model_server",
                        f"--port={grpc_port}",
                        f"--rest_api_port={rest_port}",
                    ]
                    + command_args,
                    'config': {
                        'AWS_ACCESS_KEY_ID': config['aws-access-key-id'],
                        'AWS_REGION': config['aws-region'],
                        'AWS_SECRET_ACCESS_KEY': config['aws-secret-access-key'],
                        'MODEL_BASE_PATH': config['model-base-path'],
                        'MODEL_NAME': config['model-name'],
                        'S3_ENDPOINT': config['s3-endpoint'],
                        'S3_USE_HTTPS': config['s3-use-https'],
                        'S3_VERIFY_SSL': config['s3-verify-ssl'],
                        'TF_CPP_MIN_LOG_LEVEL': config['tf-logging-level'],
                    },
                    "ports": [
                        {"name": "tf-serving-grpc", "containerPort": grpc_port},
                        {"name": "tf-serving-rest", "containerPort": rest_port},
                    ],
                }
            ],
        }
    )

    layer.status.maintenance("creating container")
    set_flag("charm.started")
