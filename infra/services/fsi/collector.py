import builtins
from infra.services.fsi.resources import FsiSharedResources
from typing import Mapping
from aws_cdk import (
  core,
  aws_kms as kms,
  aws_iam as iam,
  aws_secretsmanager as sm,
  aws_finspace as space,
)

class FsiCollectorConstruct(core.Construct):
  def __init__(self, scope: core.Construct, id: builtins.str, resources:FsiSharedResources) -> None:
    super().__init__(scope, id)

    self.tda_secret = sm.Secret(self,'AmeritradeSecrets',
      removal_policy=core.RemovalPolicy.DESTROY,
      secret_name='HomeNet-{}-Ameritrade-Secrets'.format(resources.landing_zone.zone_name))