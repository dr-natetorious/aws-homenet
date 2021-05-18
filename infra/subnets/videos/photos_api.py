from infra.subnets.identity import CertificateAuthority
from aws_cdk.aws_certificatemanager import Certificate
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
  aws_route53_targets as dns_targets,
)

class PhotosApiConstruct(core.Construct):
  """
  Configure and deploy the account linking service
  """
  def __init__(self, scope: core.Construct, id: str, landing_zone:IVpcLandingZone, infra:Infra,subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add(key='Source', value= PhotosApiConstruct.__name__)
      
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

    self.function_env = {
      'BUCKET_NAME': infra.bucket.bucket_name
    }
    self.function = lambda_.DockerImageFunction(self,'Function',
      code = code,
      role= role,
      function_name='HomeNet-PhotoApi',
      description='Python Lambda function for '+PhotosApiConstruct.__name__,
      timeout= core.Duration.seconds(30),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= landing_zone.vpc,
      memory_size=128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      security_groups=[landing_zone.security_group],
      environment=self.function_env,
    )

    self.frontend_proxy =  a.LambdaRestApi(self,'ApiGateway',
      proxy=True,
      handler=self.function,
      options=a.RestApiProps(
        description='Photo-Api proxy for '+self.function.function_name,
        domain_name= a.DomainNameOptions(
          domain_name='photos-api.virtual.world',
          certificate=Certificate.from_certificate_arn(self,'Certificate',
            certificate_arn= 'arn:aws:acm:us-east-1:581361757134:certificate/c91263e7-882e-441d-aa2f-717074aed6d0'),
          #endpoint_type= a.EndpointType.PRIVATE,
          security_policy= a.SecurityPolicy.TLS_1_0),
        policy= iam.PolicyDocument(
          statements=[
            iam.PolicyStatement(
              effect= iam.Effect.ALLOW,
              actions=['execute-api:Invoke'],
              principals=[iam.AnyPrincipal()],
              resources=['*'],
              conditions={
                'IpAddress':{
                  'aws:SourceIp': ['10.0.0.0/8','192.168.0.0/16','72.88.152.62/32']
                }
              }
            )
          ]
        ),
        endpoint_configuration= a.EndpointConfiguration(
          types = [ a.EndpointType.PRIVATE],
          vpc_endpoints=[
            landing_zone.vpc_endpoints.interfaces['execute-api']
          ]
        )
      ))

  def configure_dns(self,zone:r53.IHostedZone, ca:CertificateAuthority)->None:
    # Define the Certificate
    friendly_name = 'photos-api.{}'.format(zone.zone_name)
    r53.ARecord(self,'PhotosApi',
      zone=zone,
      record_name=friendly_name,
      target= r53.RecordTarget.from_alias(dns_targets.ApiGateway(self.frontend_proxy)))
   