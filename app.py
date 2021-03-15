#!/usr/bin/env python3
import os.path
from aws_cdk.core import App, Stack, Environment
from infra.exports import create_layers
src_root_dir = os.path.join(os.path.dirname(__file__))

default_env= Environment(region="us-east-1")

app = App()
infra_stack = Stack(app,'HomeNet', env=default_env)
create_layers(infra_stack)
app.synth()
