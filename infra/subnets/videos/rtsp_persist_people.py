from typing import Mapping
from infra.subnets.videos.rtsp_analysis_function import RtspAnalysisFunction
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

class RtspPersistPeopleFunction(RtspAnalysisFunction):

  @property
  def source_directory(self) -> str:
    return 'src/rtsp-persist-people'

  @property
  def filter_policy(self)->Mapping[str,sns.SubscriptionFilter]:
    return {
      'HasPerson': sns.SubscriptionFilter.string_filter(
        allowlist=['true','True','TRUE'])
    }

  def __init__(self, scope: core.Construct, id: str, 
    infra:RtspBaseResourcesConstruct,
    **kwargs) -> None:
    super().__init__(scope, id, infra=infra, **kwargs)

    self.function.role.add_managed_policy(
      iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='AmazonTimestreamFullAccess'))

    self.function.add_environment(
      key='DATABASE_NAME',
      value=infra.time_stream.people_table.database_name)
    self.function.add_environment(
      key='TABLE_NAME',
      value=infra.time_stream.people_table.table_name)
