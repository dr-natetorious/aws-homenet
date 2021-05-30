import builtins
from infra.interfaces import IVpcLandingZone
from infra.services.fsi.collector import FsiCollectorConstruct
from typing import Mapping
from infra.services.fsi.resources import FsiSharedResources
from aws_cdk import (
  core,
  aws_sns as sns,
  aws_iam as iam,
)

class FsiRootConstruct(core.Construct):
  def __init__(self, scope: core.Construct, id: builtins.str, landing_zone:IVpcLandingZone) -> None:
    super().__init__(scope, id)
    core.Tags.of(self).add('Service', FsiRootConstruct.__name__)

    self.resources = FsiSharedResources(self,'Resources', landing_zone=landing_zone)
    FsiCollectorConstruct(self,'Collector', resources=self.resources)
