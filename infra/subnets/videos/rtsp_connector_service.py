from infra.subnets.videos.base_resources import Infra
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_ecs as ecs,
)

desired_count = 1
cameras=['live'+str(x) for x in range(0,3)]

install_ssm_script="""
#!/bin/bash
yum -y update && yum -y https://s3.us-east-1.amazonaws.com/amazon-ssm-us-east-1/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl status amazon-ssm-agent
"""

class RtspConnectorService(core.Construct):
  """
  Represents an ECS service for collecting RTSP frames.
  """
  def __init__(self, scope: core.Construct, id: str, 
    infra:Infra,
    home_base:str,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)    
    core.Tags.of(self).add('home_base',home_base)

    definition = ecs.TaskDefinition(self,'DefaultTask',
      compatibility= ecs.Compatibility.EC2,
      cpu='128', memory_mib='128',
      task_role= infra.task_role,
      execution_role= infra.execution_role,
      network_mode= ecs.NetworkMode.AWS_VPC)

    definition.add_container('DefaultContainer',
      memory_reservation_mib=128,
      image = infra.container,
      logging= ecs.AwsLogDriver(
        stream_prefix='rtsp-connector/{}'.format(home_base),
        log_group=infra.log_group),
      environment={
        'SERVER_URI':'admin:EYE_SEE_YOU@192.168.0.70',
        'BUCKET':infra.bucket.bucket_name,
        'FRAME_ANALYZED_TOPIC': infra.frameAnalyzed.topic_arn,
        'REK_COLLECT_ID': 'homenet-hybrid-collection',
        'REGION':core.Stack.of(self).region,
      })

    ecs.Ec2Service(self,'RtspConnectorService',
      service_name='{}-rtsp-connector-{}'.format(infra.landing_zone.zone_name, home_base),
      task_definition= definition,
      assign_public_ip=False,
      cluster= infra.cluster,      
      deployment_controller=ecs.DeploymentController(type=ecs.DeploymentControllerType.ECS),
      security_group= infra.security_group,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name=infra.subnet_group_name),
      desired_count=desired_count)
