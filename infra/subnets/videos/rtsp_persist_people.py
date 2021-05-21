from infra.subnets.videos.base_resources import RtspBaseResourcesConstruct
from infra.interfaces import IVpcLandingZone
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

class RtspPersistPeopleFunction(core.Construct):
  def __init__(self, scope: core.Construct, id: str, 
    infra:RtspBaseResourcesConstruct,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='src/rtsp-persist-people',
      file='Dockerfile',
      repository_name='homenet-rtsp-persist-people')

    code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1])

    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='Listen to FrameAnalyzed events and persist people',
      role_name='rtsp-process-locations@homenet-{}'.format(core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole'
      )])

    self.function = lambda_.DockerImageFunction(self,'Function',
      code = code,
      role= role,
      function_name='HomeNet-Rtsp-Persist-People',
      description='Python container lambda function for '+RtspPersistPeopleFunction.__name__,
      timeout= core.Duration.minutes(1),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= infra.landing_zone.vpc,
      memory_size=128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=infra.subnet_group_name),
      security_groups=[infra.security_group]
    )

    self.dlq = sqs.Queue(self,'DeadLetterQueue',
      queue_name=self.function.function_name+"_dlq")

    self.function.add_event_source(events.SnsEventSource(
      topic= infra.frameAnalyzed,
      dead_letter_queue= self.dlq,
      filter_policy={
        'HasPerson': sns.SubscriptionFilter.string_filter(
          allowlist=['true','True','TRUE'])
      }))

    # sns.Subscription(self,'Subscription',
    #   topic=infra.frameAnalyzed,
    #   endpoint= self.function.function_arn,
    #   protocol= sns.SubscriptionProtocol.LAMBDA,
    #   dead_letter_queue= self.dlq)

    
