import builtins
from typing import Mapping
from aws_cdk import (
  core,
  aws_kms as kms,
  aws_iam as iam,
  aws_finspace as space,
)

class FsiSharedResources(core.Construct):
  def __init__(self, scope: core.Construct, id: builtins.str) -> None:
    super().__init__(scope, id)

    # Create a key and delegate access to IAM...
    self.key = kms.Key(self,'Key',
      alias='homenet/fsi',
      enable_key_rotation=True,
      policy=iam.PolicyDocument(
        statements=[
          iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            principals=[iam.AccountPrincipal(
              core.Stack.of(self).account)
            ],
            actions=['kms:*'],
            resources=['*']
          )
        ]
      ))

    self.fspace = space.CfnEnvironment(self,'Environment',
      name='HomeNet-Fsi',
      description="HomeNets Financial Servicing")
