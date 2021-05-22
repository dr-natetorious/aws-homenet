#!/bin/bash

export REGION=us-east-1
function get_value(){
  aws ssm get-parameter --region $REGION --name /homenet/Hybrid/rtsp/rtsp-connector/$1 --region us-east-1 | jq .Parameter.Value | tr -d '"'
}

export SERVER_URI=`get_value SERVER_URI`
export BUCKET=`get_value BUCKET`
export FRAME_ANALYZED_TOPIC=`get_value FRAME_ANALYZED_TOPIC`
export REK_COLLECT_ID=`get_value REK_COLLECT_ID`
export IMAGE_URI=`get_value IMAGE_URI`
export LOG_GROUP=`get_value LOG_GROUP`

echo SERVER_URI=$SERVER_URI > prod.env
echo BUCKET=$BUCKET >> prod.env
echo FRAME_ANALYZED_TOPIC=$FRAME_ANALYZED_TOPIC >> prod.env
echo REK_COLLECT_ID=$REK_COLLECT_ID >> prod.env
echo IMAGE_URI=$IMAGE_URI >> prod.env
echo LOG_GROUP=$LOG_GROUP >> prod.env
echo REGION=$REGION >> prod.env


# Setup access
`aws ecr get-login --no-include-email --region us-east-1`
mkdir -p /root/.aws

docker run -d --restart always --env-file prod.env -v ~/.aws:/root/.aws --log-driver=awslogs --log-opt awslogs-group=$LOG_GROUP $IMAGE_URI