#!/bin/bash

export SERVER_URI=admin:EYE_SEE_YOU@192.168.0.70
export BUCKET=infra.bucket.bucket_name
export FRAME_ANALYZED_TOPIC=HomeNet-Hybrid-Rtsp-FrameAnalysis
export REK_COLLECT_ID=homenet-hybrid-collection
export REGION=us-east-1
export IMAGE_URI=581361757134.dkr.ecr.us-east-1.amazonaws.com/aws-cdk/assets:92a60e529caad622409066629001e0b6cd59fa771dc87c141e4666d39b589547

# Setup access
`aws ecr get-login --no-include-email --region us-east-1`
mkdir -p /root/.aws

docker run -d --env-file debug.env -v ~/.aws:/root/.aws $IMAGE_URI