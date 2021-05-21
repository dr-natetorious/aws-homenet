from infra.interfaces import ILandingZone
from aws_cdk import (
  core,
  aws_codeartifact as art,
  aws_route53 as r53,
)

class ArtifactsConstruct(core.Construct):
  """
  Represents a code artifact repository.
  """
  def __init__(self, scope: core.Construct, id: str, landing_zone:ILandingZone, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)    
    core.Tags.of(self).add('Construct',ArtifactsConstruct.__name__)

    self.domain = art.CfnDomain(self,'Domain',
      domain_name=landing_zone.zone_name)

    self.repo = art.CfnRepository(self,'Repository',
      repository_name=landing_zone.zone_name,
      domain_name= self.domain.attr_name,
      description='Artifacts for '+landing_zone.zone_name,
      upstreams=['pypi-store'])

  def configure_dns(self,zone:r53.IHostedZone):
    r53.CnameRecord(self,'DnsRecord',
      zone=zone,
      record_name='artifacts.{}'.format(zone.zone_name),
      domain_name=self.domain.domain_name)
