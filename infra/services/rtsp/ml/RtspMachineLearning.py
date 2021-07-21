from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from infra.services.rtsp.ml.RtspDataPreparation import RtspDataPreparation
from aws_cdk import (
  core,
)

class RtspMachineLearning(core.Construct):
  """
  Represents the Rtsp Data Preparation Layer
  """
  def __init__(self, scope: core.Construct, id: str,infra:RtspBaseResourcesConstruct, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    RtspDataPreparation(self,'Preparation', infra=infra)
