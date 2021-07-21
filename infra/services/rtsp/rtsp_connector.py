from infra.services.jumpbox import JumpBoxConstruct
from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_ssm as ssm,
  aws_route53 as r53,
  aws_s3_deployment as s3d,
  aws_logs as logs,
  aws_ecr_assets as assets,
)

class RtspConnectorConstruct(JumpBoxConstruct):
  """
  Represents an ECS service for collecting RTSP frames.
  """

  @property
  def infra(self)->RtspBaseResourcesConstruct:
    return self.__infra

  def __init__(self, scope: core.Construct, id: str,infra:RtspBaseResourcesConstruct, **kwargs) -> None:
    super().__init__(scope, id, landing_zone=infra.landing_zone, **kwargs)
    self.__infra = infra

    # Create repository
    self.container_image = assets.DockerImageAsset(self,'Container',
      directory='src/rtsp/connector')

    self.log_group = logs.LogGroup(self,'LogGroup',
      log_group_name='/homenet/rtsp/connector',
      retention=logs.RetentionDays.ONE_DAY,
      removal_policy= core.RemovalPolicy.DESTROY)
  
    # Pass the environment variables via SSM
    environment={
        'BUCKET':self.infra.bucket.bucket_name,
        'FRAME_ANALYZED_TOPIC': self.infra.frameAnalyzed.topic_arn,
        'REK_COLLECT_ID': 'homenet-hybrid-collection',
        'REGION':core.Stack.of(self).region,
        'IMAGE_URI': self.container_image.image_uri,
        'LOG_GROUP': self.log_group.log_group_name,
      }

    # Add the userdata
    self.instance.add_user_data(self.__create_user_data())

    for env_name in environment.keys():
      param = ssm.StringParameter(self,env_name+'Param',
        parameter_name='/homenet/{}/rtsp/rtsp-connector/{}'.format(
          self.infra.landing_zone.zone_name,
          env_name),
        string_value=environment[env_name])
      param.grant_read(self.instance.role)
      
    # Grant permissions...
    self.instance.role
    self.infra.bucket.grant_read_write(self.instance.role)
    self.infra.frameAnalyzed.grant_publish(self.instance.role)
    self.infra.log_group.grant_write(self.instance.role)
    self.infra.secrets.grant_read(self.instance.role)
    self.instance.role.add_to_policy(iam.PolicyStatement(
      effect= iam.Effect.ALLOW,
      actions=['cloudwatch:PutMetricData'],
      resources=['*']
    ))

    for name in [
      'AWSCodeArtifactReadOnlyAccess',
      'AmazonEC2ContainerRegistryReadOnly',
      'AmazonRekognitionFullAccess',
      'CloudWatchLogsFullAccess']:
      self.instance.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(name))

    # Upload the application
    deployment = s3d.BucketDeployment(self,'AppDeployment',
      destination_bucket=self.infra.bucket,
      destination_key_prefix='app/rtsp-connector',
      sources=[s3d.Source.asset(
        path='src/rtsp/connector')])
    self.instance.node.add_dependency(deployment)

    # Configure the startup script
    self.instance.add_user_data()

  @property
  def machine_image(self) -> ec2.IMachineImage:
    """
    Returns the latest supported AL2 x64 image.
    """
    param = ssm.StringParameter.from_string_parameter_name(self,'Parameter',
      string_parameter_name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-ebs')      

    return ec2.MachineImage.generic_linux(
      user_data=ec2.UserData.for_linux(),
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

  def __create_user_data(self)->str:
    install_script="""
#!/bin/bash
yum -y update
yum -y install docker jq
service docker start
chkconfig docker on

IMAGE_URI={image_uri}
mkdir -p /app
cd /app

aws s3 cp --recursive s3://homenet-hybrid.us-east-1.virtual.world/app/rtsp-connector/systemd/ . > install.log 2>&1
chmod +x /app/run-connector.sh >> install.log 2>&1
mv /app/connector.service /usr/lib/systemd/system/connector.service >> install.log 2>&1
systemctl daemon-reload >> install.log 2>&1
systemctl enable connector.service >> install.log 2>&1
systemctl status connector.service >> install.log 2>&1
systemctl start connector.service >> install.log 2>&1
""".format(
  image_uri=self.container_image.image_uri).strip()

    return install_script