import builtins
from infra.services.fsi.resources import FsiSharedResources
from typing import Mapping
from aws_cdk import (
  core,
  aws_secretsmanager as sm,
  aws_ec2 as ec2,
  aws_ecr_assets as assets,  
)

class FsiCollectorConstruct(core.Construct):
  def __init__(self, scope: core.Construct, id: builtins.str, resources:FsiSharedResources) -> None:
    super().__init__(scope, id)    

    # Configure the container resources...
    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='src/fsi/collectors',
      file='Dockerfile')

    # kplus.Deployment(self,'Collector',
    #   replicas=1,
    #   containers=[kplus.Container(
    #     image= self.repo.image_uri,        
    #   )])