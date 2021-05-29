"""
This deploys the /src/rtsp-connector into ECS service.

For some reason EC2 instances in ASG cannot talk across the site-to-site vpn.

The rtsp_connector.py is interm replacement solution.
"""
from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_ecs as ecs,
)

desired_count = 0

class RtspConnectorService(core.Construct):
  """
  Represents an ECS service for collecting RTSP frames.
  """
  def __init__(self, scope: core.Construct, id: str, 
    infra:RtspBaseResourcesConstruct,
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
