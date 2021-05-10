#!/bin/bash

cdk deploy -a /files/app.py --require-approval never HomeNet-Hybrid
cdk deploy -a /files/app.py --require-approval never HomeNet-Chatham
