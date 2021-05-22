from infra.subnets.jumpbox import JumpBoxConstruct
from infra.subnets.videos.base_resources import RtspBaseResourcesConstruct
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_ssm as ssm,
  aws_route53 as r53,
  aws_s3_deployment as s3d,
  aws_ecr as ecr,
  aws_ecr_assets as assets,
)

install_script="""
#!/bin/bash
yum -y update
yum -y install docker jq
service docker start
chkconfig docker on

mkdir -p /app
cd /app

aws s3 cp --recursive s3://homenet-hybrid.us-east-1.virtual.world/app/rtsp-connector/ .
chmod +x ./run-connector.sh
./run-connector.sh
""".strip()


class RtspConnectorConstruct(JumpBoxConstruct):
  """
  Represents an ECS service for collecting RTSP frames.
  """
  def __init__(self, scope: core.Construct, id: str,infra:RtspBaseResourcesConstruct, home_base:str, **kwargs) -> None:
    super().__init__(scope, id, landing_zone=infra.landing_zone, **kwargs)
    core.Tags.of(self).add('home_base',home_base)

    # Create repository
    self.container_image = assets.DockerImageAsset(self,'Container',
      directory='src/rtsp-connector')
  
    tag_param = ssm.StringParameter(self,'ImageTagParam',
      parameter_name='/homenet/{}/ecr/rtsp-connector/latest'.format(infra.landing_zone.zone_name),
      string_value=self.container_image.image_uri)

    # Grant permissions...
    infra.bucket.grant_read_write(self.instance.role)
    infra.frameAnalyzed.grant_publish(self.instance.role)
    tag_param.grant_read(self.instance.role)

    for name in [
      'AWSCodeArtifactReadOnlyAccess',
      'AmazonEC2ContainerRegistryReadOnly',
      'AmazonRekognitionFullAccess']:
      self.instance.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(name))

    # Upload the application
    deployment = s3d.BucketDeployment(self,'AppDeployment',
      destination_bucket=infra.bucket,
      destination_key_prefix='app/rtsp-connector',
      sources=[s3d.Source.asset(
        path='src/rtsp-connector')])

    self.instance.node.add_dependency(deployment)

  @property
  def machine_image(self) -> ec2.IMachineImage:
    """
    Returns the latest supported AL2 x64 image.
    """
    param = ssm.StringParameter.from_string_parameter_name(self,'Parameter',
      string_parameter_name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-ebs')
    
    return ec2.MachineImage.generic_linux(
      user_data= ec2.UserData.for_linux(
        shebang=install_script),
      ami_map={
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