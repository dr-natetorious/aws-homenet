#!/usr/bin/env python3
from infra.services.fsi.resources import FsiSharedResources
from aws_cdk.aws_certificatemanager import Certificate
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

class FsiAccountLinkingGateway(core.Construct):
  """
  Configure and deploy the account linking service
  """
  def __init__(self, scope: core.Construct, id: str, resources:FsiSharedResources, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    
    # Configure the container resources...
    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='src/fsi/account-linking',
      file='Dockerfile')

    code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1])

    # Configure security policies...
    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='HomeNet-{}-Fsi-AccountLinking'.format(resources.landing_zone.zone_name),
      role_name='fsi-accountlinking@homenet.{}.{}'.format(
        resources.landing_zone.zone_name,
        core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole'),        
      ])

    # Grant any permissions...
    resources.tda_secret.grant_write(role)

    # Define any variables for the function
    self.function_env = {
      'REGION': core.Stack.of(self).region,
      'TDA_SECRET_ID': resources.tda_secret.secret_arn,
      'TDA_REDIRECT_URI':  ssm.StringParameter.from_string_parameter_name(self,'TDA_REDIRECT_URI',
        string_parameter_name='/HomeNet/Amertitrade/redirect_uri').string_value,
      'TDA_CLIENT_ID': ssm.StringParameter.from_string_parameter_name(self, 'TDA_CLIENT_ID',
        string_parameter_name='/HomeNet/Ameritrade/client_id').string_value
    }

    # Create the backing webapi compute ...
    self.function = lambda_.DockerImageFunction(self,'Function',
      code = code,
      role= role,
      function_name='HomeNet-{}-Fsi-{}'.format(
        resources.landing_zone.zone_name,
        FsiAccountLinkingGateway.__name__),
      description='Python Lambda function for '+FsiAccountLinkingGateway.__name__,
      timeout= core.Duration.seconds(30),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= resources.landing_zone.vpc,
      log_retention= logs.RetentionDays.FIVE_DAYS,
      memory_size=128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      security_groups=[resources.landing_zone.security_group],
      environment=self.function_env,
    )

    # Bind APIG to Lambda compute...
    self.frontend_proxy =  a.LambdaRestApi(self,'ApiGateway',
      proxy=True,
      handler=self.function,
      options=a.RestApiProps(
        description='Hosts the Ameritrade Auth Callback  via '+self.function.function_name,
        domain_name= a.DomainNameOptions(
          domain_name='account-linking.fsi.virtual.world',
          certificate=Certificate.from_certificate_arn(self,'Certificate',
           certificate_arn= 'arn:aws:acm:us-east-2:581361757134:certificate/203d0a7d-9ace-41a8-8667-f2f450fa2211'),
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
          types = [ a.EndpointType.REGIONAL],
        )
      ))
