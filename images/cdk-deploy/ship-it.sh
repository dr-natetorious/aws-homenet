#!/bin/bash

cdk diff -a /files/app.py --require-approval never HomeNet-CoreSvc
cdk deploy -a /files/app.py --require-approval never HomeNet-CoreSvc

cdk diff -a /files/app.py --require-approval never HomeNet-Hybrid
cdk deploy -a /files/app.py --require-approval never HomeNet-Hybrid

cdk diff -a /files/app.py --require-approval never HomeNet-Chatham
cdk deploy -a /files/app.py --require-approval never HomeNet-Chatham

cdk diff -a /files/app.py --require-approval never HomeNet-Peering
cdk deploy -a /files/app.py --require-approval never HomeNet-Peering

cdk diff -a /files/app.py --require-approval never HomeNet-HybridReceiver
cdk deploy -a /files/app.py --require-approval never HomeNet-HybridReceiver