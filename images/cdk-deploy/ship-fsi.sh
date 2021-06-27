#!/bin/bash

cdk diff -a /files/app.py --require-approval never HomeNet-CoreSvc
cdk deploy -a /files/app.py --require-approval never HomeNet-CoreSvc
