from infra.subnets.jumpbox import JumpBoxConstruct
from infra.subnets.videos.base_resources import RtspBaseResourcesConstruct
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_ssm as ssm,
)

class RtspConnectorConstruct(JumpBoxConstruct):
  """
  Represents an ECS service for collecting RTSP frames.
  """
  def __init__(self, scope: core.Construct, id: str,landing_zone:IVpcLandingZone, home_base:str, **kwargs) -> None:
    super().__init__(scope, id, landing_zone=landing_zone, **kwargs)
    core.Tags.of(self).add('home_base',home_base)

  @property
  def machine_image(self) -> ec2.IMachineImage:
    param = ssm.StringParameter.from_string_parameter_name(self,'Parameter',
      string_parameter_name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-ebs')
    return ec2.MachineImage.generic_linux(ami_map={
      core.Stack.of(self).region: param.string_value
    })