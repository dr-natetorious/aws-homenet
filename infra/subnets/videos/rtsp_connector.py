from infra.subnets.jumpbox import JumpBoxConstruct
from infra.subnets.videos.base_resources import RtspBaseResourcesConstruct
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_ssm as ssm,
  aws_route53 as r53,
)

class RtspConnectorConstruct(JumpBoxConstruct):
  """
  Represents an ECS service for collecting RTSP frames.
  """
  def __init__(self, scope: core.Construct, id: str,infra:RtspBaseResourcesConstruct, home_base:str, **kwargs) -> None:
    super().__init__(scope, id, landing_zone=infra.landing_zone, **kwargs)
    core.Tags.of(self).add('home_base',home_base)

    self.instance.role.add_managed_policy(
      iam.ManagedPolicy.from_aws_managed_policy_name('AWSCodeArtifactReadOnlyAccess'))

  @property
  def machine_image(self) -> ec2.IMachineImage:
    """
    Returns the latest supported AL2 x64 image.
    """
    param = ssm.StringParameter.from_string_parameter_name(self,'Parameter',
      string_parameter_name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-ebs')
    
    return ec2.MachineImage.generic_linux(ami_map={
      core.Stack.of(self).region: param.string_value
    })

  def configure_dns(self,zone:r53.IHostedZone):
    r53.ARecord(self,'HostRecord',
      zone=zone,
      record_name='rtsp-connector.{}'.format(zone.zone_name),
      ttl = core.Duration.minutes(1),
      target= r53.RecordTarget(
        values=[self.instance.instance_private_ip]
      ))