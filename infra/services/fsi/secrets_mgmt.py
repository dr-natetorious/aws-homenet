#!/usr/bin/env python3
from aws_cdk.aws_secretsmanager import HostedRotation
from infra.services.fsi.resources import FsiSharedResources
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_apigateway as a,
  aws_lambda as lambda_,
  aws_ecr_assets as assets,
  aws_route53 as r53,
  aws_route53_targets as dns_targets,
  aws_logs as logs,
  aws_ssm as ssm,
)

class FsiSecretManagement(core.Construct):
  
  @property
  def component_name(self)->str:
    return FsiSecretManagement.__name__
  
  def __init__(self, scope: core.Construct, id: str, resources:FsiSharedResources, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    # Configure role...
    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='Ameritrade Secrets Rotation Lambda via '+self.component_name,
      role_name='{}@homenet-{}.{}'.format(
        self.component_name,
        resources.landing_zone.zone_name,
        core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole')        
      ])

    resources.tda_secret.grant_write(role)

    # Configure the lambda...
    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='src/fsi/secret-rotation')

    code = lambda_.DockerImageCode.from_ecr(
      repository=self.repo.repository,
      tag=self.repo.image_uri.split(':')[-1])    

    self.function = lambda_.DockerImageFunction(self,'Function',
      code = code,
      role= role,
      function_name='HomeNet-Fsi{}-{}'.format(
        resources.landing_zone.zone_name,
        self.component_name),
      description='Python container function for '+self.component_name,
      timeout= core.Duration.minutes(15),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= resources.landing_zone.vpc,
      log_retention= logs.RetentionDays.TWO_WEEKS,
      memory_size= 3 * 128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      security_groups=[resources.landing_zone.security_group],
      environment={
      }
    )

    resources.tda_secret.grant_write(self.function.role)
    resources.tda_secret.grant_read(self.function.role)

    # Automatically rotate credentials every 30 days...
    # resources.tda_secret.add_rotation_schedule('Rotation',
    #   automatically_after=core.Duration.days(30),
    #   rotation_lambda=self.function)

