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
  def __init__(self, scope: core.Construct, id: str, landing_zone:ILandingZone,zone:r53.IHostedZone, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)    
    core.Tags.of(self).add('Construct',ArtifactsConstruct.__name__)

    self.domain = art.CfnDomain(self,'Domain',
      domain_name=landing_zone.zone_name)

    self.repo = art.CfnRepository(self,'PyPi',
      domain_name=self.domain.domain_name,
      repository_name='pypi-store',
      description='PyPI connector',
      external_connections=['public:pypi'])

    self.repo = art.CfnRepository(self,'DefaultRepo',
      repository_name=landing_zone.zone_name,
      domain_name= self.domain.domain_name,
      #upstreams=['pypi-store'],
      description='Artifacts for '+zone.zone_name)

    r53.CnameRecord(self,'DnsRecord',
      zone=zone,
      record_name='artifacts.{}'.format(zone.zone_name),
      domain_name=self.domain.domain_name)
