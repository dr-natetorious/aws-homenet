from typing import Mapping
from infra.services.rtsp.analyzers.analysis_function import RtspAnalysisFunction
from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from aws_cdk import (
  core,
  aws_sns as sns,
  aws_iam as iam,
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
