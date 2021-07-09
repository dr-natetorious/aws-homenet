import builtins
from infra.services.fsi.secrets_mgmt import FsiSecretManagement
from infra.services.fsi.earnings_api import FsiEarningsGateway
from infra.interfaces import IVpcLandingZone
from infra.services.fsi.collector import FsiCollectorConstruct
from infra.services.fsi.account_linking import FsiAmeritradeAuthGateway
from infra.services.fsi.resources import FsiSharedResources
from aws_cdk import (
  core,
)

class FsiRootConstruct(core.Construct):
  def __init__(self, scope: core.Construct, id: builtins.str, landing_zone:IVpcLandingZone) -> None:
    super().__init__(scope, id)
    core.Tags.of(self).add('Service', FsiRootConstruct.__name__)

    self.resources = FsiSharedResources(self,'Resources', landing_zone=landing_zone)
    FsiAmeritradeAuthGateway(self,'AmeritradeAuth', resources=self.resources)
    FsiCollectorConstruct(self,'Collector', resources=self.resources)
    FsiEarningsGateway(self,'EarningsGateway',resources=self.resources)
    FsiSecretManagement(self,'SecretsMgmt',resources=self.resources)
