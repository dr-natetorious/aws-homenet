from infra.interfaces import IVpcLandingZone
from infra.subnets.videos.base_resources import Infra
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_apigateway as a,
  aws_lambda as lambda_,
  aws_ecr_assets as assets,
  aws_route53 as r53,
)

class FrameInspectorConstruct(core.Construct):
  """
  Configure and deploy the account linking service
  """
  def __init__(self, scope: core.Construct, id: str, landing_zone:IVpcLandingZone, infra:Infra, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add(key='Source', value= FrameInspectorConstruct.__name__)
      
    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='src/frame-inspector',
      file='Dockerfile',
      repository_name='homenet-video-frame-inspector')

    code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1])

    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='Role for RTSP Frame Inspector',
      role_name='video-frame-inspector@homenet-{}'.format(core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole'
      )])
    infra.bucket.grant_read(role)

    self.function = lambda_.DockerImageFunction(self,'Function',
      code = code,
      role= role,
      function_name='HomeNet-Video-FrameInspector',
      description='Python container lambda function for Rtsp Frame Inspection',
      timeout= core.Duration.seconds(30),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= landing_zone.vpc,
      memory_size=128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      security_groups=[landing_zone.security_group]
    )

    self.frontend_proxy =  a.LambdaRestApi(self,id,
      options=a.RestApiProps(),
      handler=self.function,
      proxy=True,
      description='Frontend proxy for '+self.function.function_name)

  def configure_dns(self,zone:r53.IHostedZone)->None:
    r53.CnameRecord(self,'ProxyCname',
      zone=zone,
      domain_name= self.frontend_proxy.url.split('/')[2],
      record_name='frame-inspector.{}'.format(zone.zone_name),
      comment='Frame Inspector ApiGateway')
