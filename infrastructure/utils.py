import os
from typing import Text, Dict

import monocdk as core
from monocdk import aws_lambda


def build_path_to_lambdas(path):
    return os.path.join("lambdas", path)


def build_path_to_layer(path):
    return os.path.join("layers", path)


python_38_function_bundling_options = core.BundlingOptions(
    image=aws_lambda.Runtime.PYTHON_3_8.bundling_docker_image,
    command=[
        "bash",
        "-c",
        "\n        pip install -r requirements.txt -t /asset-output &&\n        cp -au . /asset-output\n        ",
    ],
)

python_38_layer_bundling_options = core.BundlingOptions(
    image=aws_lambda.Runtime.PYTHON_3_8.bundling_docker_image,
    command=[
        "bash",
        "-c",
        "\n        pip install -r requirements.txt -t /asset-output/python &&\n        cp -au . /asset-output/python\n        ",
    ],
)


class Stack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

    def add_parameters(self):
        pass

    def add_outputs(self):
        pass
