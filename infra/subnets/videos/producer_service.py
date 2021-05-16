from infra.subnets.videos.base_resources import Infra
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_ecs as ecs,
)

cameras=['live'+str(x) for x in range(0,3)]

install_ssm_script="""
#!/bin/bash
yum -y update && yum -y https://s3.us-east-1.amazonaws.com/amazon-ssm-us-east-1/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl status amazon-ssm-agent
"""

class VideoProducerService(core.Construct):
  """
  Represents an ECS service for collecting RTSP frames.
  """
  def __init__(self, scope: core.Construct, id: str, 
    infra:Infra,
    camera_name:str,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)    
    core.Tags.of(self).add('Camera',camera_name)

    definition = ecs.TaskDefinition(self,'ProducerTask',
      compatibility= ecs.Compatibility.EC2,
      cpu='128', memory_mib='128',
      task_role= infra.task_role,
      execution_role= infra.execution_role,
      network_mode= ecs.NetworkMode.AWS_VPC)

    definition.add_container('DefaultContainer',
      memory_reservation_mib=128,
      image = infra.container,
      logging= ecs.AwsLogDriver(
        stream_prefix='video-producer/{}'.format(camera_name),
        log_group=infra.log_group),
      # secrets= {
      #   'BASE_URI': ecs.Secret.from_ssm_parameter(
      #       ssm.StringParameter.from_string_parameter_name(
      #         self,'BaseUriParam',
      #         string_parameter_name='/homenet/{}/videosubnet/camera-base-uri'.format(
      #           core.Stack.of(self).region)))
      # },
      environment={
        'SERVER_URI':'admin:EYE_SEE_YOU@192.168.0.70',
        'BUCKET':infra.bucket.bucket_name,
      })

    ecs.Ec2Service(self,'ProducerService',
      service_name='homenet-producer-'+camera_name,
      task_definition= definition,
      assign_public_ip=False,
      cluster= infra.cluster,      
      deployment_controller=ecs.DeploymentController(type=ecs.DeploymentControllerType.ECS),
      security_group= infra.security_group,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name=infra.subnet_group_name),
      desired_count=1)
