#!/usr/bin/env python3
import os.path
from infra.basenet import NetworkingApp
src_root_dir = os.path.join(os.path.dirname(__file__))

app = NetworkingApp()

app.synth()
