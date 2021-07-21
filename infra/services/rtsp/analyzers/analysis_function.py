from infra.services.rtsp.resources.function import RtspFunction
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

class RtspAnalysisFunction(RtspFunction):
  
  @property
  def topic(self)->sns.ITopic:
    return self.infra.frameAnalyzed

  @property
  def filter_policy(self)->Mapping[str,SubscriptionFilter]:
    return {}
  
  def __init__(self, scope: core.Construct, id: str, 
    infra:RtspBaseResourcesConstruct,
    **kwargs) -> None:
    super().__init__(scope, id, infra=infra, **kwargs)

    self.function.add_event_source(events.SnsEventSource(
      topic= self.topic,
      dead_letter_queue= self.dlq,
      filter_policy=self.filter_policy))
    
