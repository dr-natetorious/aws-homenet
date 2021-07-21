from typing import Mapping

from aws_cdk.aws_logs import RetentionDays, SubscriptionFilter
from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_sns as sns,
  aws_sqs as sqs,
  aws_iam as iam,
  aws_lambda as lambda_,
  aws_lambda_event_sources as events,
  aws_ecr_assets as assets,
)

class RtspAnalysisFunction(core.Construct):
  
  @property
  def source_directory(self)->str:
    raise NotImplemented()

  @property
  def component_name(self)->str:
    return self.__class__.__name__

  @property
  def topic(self)->sns.ITopic:
    return self.infra.frameAnalyzed

  @property
  def function_timeout(self)->core.Duration:
    return core.Duration.minutes(1)

  @property
  def filter_policy(self)->Mapping[str,SubscriptionFilter]:
    return {}
  
  def __init__(self, scope: core.Construct, id: str, 
    infra:RtspBaseResourcesConstruct,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.infra = infra

    self.repo = assets.DockerImageAsset(self,'Repo',
      directory=self.source_directory,
      file='Dockerfile')

    code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1])

    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='Listen to FrameAnalyzed events for '+self.component_name,
      role_name='{}@homenet-{}.{}'.format(
        self.component_name,
        infra.landing_zone.zone_name,
        core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole')        
      ])

    self.function = lambda_.DockerImageFunction(self,'Function',
      code = code,
      role= role,
      function_name='HomeNet-{}-{}'.format(
        infra.landing_zone.zone_name,
        self.component_name),
      description='Python container lambda function for '+self.component_name,
      timeout= self.function_timeout,
      tracing= lambda_.Tracing.ACTIVE,
      vpc= infra.landing_zone.vpc,
      log_retention= RetentionDays.FIVE_DAYS,
      memory_size=128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=infra.subnet_group_name),
      security_groups=[infra.security_group],
      environment={
        'REGION':core.Stack.of(self).region,
      }
    )

    self.dlq = sqs.Queue(self,'DeadLetterQueue',
      queue_name=self.function.function_name+"_dlq")

    self.function.add_event_source(events.SnsEventSource(
      topic= self.topic,
      dead_letter_queue= self.dlq,
      filter_policy=self.filter_policy))
    
