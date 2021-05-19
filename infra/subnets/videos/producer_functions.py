from infra.subnets.videos.base_resources import Infra
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,  
  aws_lambda as lambda_,
  aws_ecr_assets as assets,
  aws_events as events,
  aws_events_targets as targets,  
)

cameras=['live'+str(x) for x in range(0,3)]

install_ssm_script="""
#!/bin/bash
yum -y update && yum -y https://s3.us-east-1.amazonaws.com/amazon-ssm-us-east-1/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl status amazon-ssm-agent
"""

class VideoProducerFunctions(core.Construct):
  def __init__(self, scope: core.Construct, id: str, 
    infra:Infra,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='src/rtsp-connector',
      file='Dockerfile.lambda',
      repository_name='homenet-rtsp-connector')

    code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1])

    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='Role for RTSP Video Producer',
      role_name='video-producer-function@homenet-{}'.format(core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole'
      )])

    self.function = lambda_.DockerImageFunction(self,'VideoProducer',
      code = code,
      role= role,
      function_name='HomeNet-RTSP-VideoProducer',
      description='Python container lambda function for VideoProducer',
      timeout= core.Duration.minutes(1),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= infra.landing_zone.vpc,
      memory_size=128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=infra.subnet_group_name),
      security_groups=[infra.security_group]
    )

    infra.bucket.grant_write(role)

    self.schedule = events.Schedule.rate(core.Duration.minutes(1))
    camera_targets = [
      targets.LambdaFunction(
        handler=self.function,
        event= events.RuleTargetInput.from_object({
          'SERVER_URI':'rtsp://admin:EYE_SEE_YOU@192.168.0.70/'+camera_name,
          'CAMERA':camera_name,
          'BUCKET':infra.bucket.bucket_name,
        })) for camera_name in cameras]

    self.rule = events.Rule(self,'RTSP-VideoProducer',
        description='Check for updates on HomeNet cameras: ',
        targets=camera_targets,
        enabled=False,
        schedule=self.schedule,
        rule_name='HomeNet-RTSP-VideoProducer')
