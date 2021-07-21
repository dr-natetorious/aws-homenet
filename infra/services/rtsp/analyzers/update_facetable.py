from typing import Mapping
from infra.services.rtsp.analyzers.analysis_function import RtspAnalysisFunction
from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
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

class RtspUpdateFaceTableFunction(RtspAnalysisFunction):

  @property
  def source_directory(self) -> str:
    return 'src/rtsp/update-facetable'

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

    infra.face_table.grant_write_data(self.function.role)
    self.function.add_environment(
      key='TABLE_NAME',
      value=infra.face_table.table_name)
