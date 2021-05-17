from infra.subnets.identity import CertificateAuthority
from infra.subnets.videos.photos_api import PhotosApiConstruct
from infra.subnets.videos.base_resources import Infra
from infra.subnets.videos.producer_service import VideoProducerService
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_route53 as r53,
)

cameras=['live'+str(x) for x in range(0,3)]
class VideoSubnet(core.Construct):
  def __init__(self, scope: core.Construct, id: str, landing_zone:IVpcLandingZone, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add('Component','VideoSubnet')

    self.infra = Infra(self,'Infra',
      landing_zone= landing_zone,
      subnet_group_name=subnet_group_name)

    #self.compute = VideoProducerFunctions(self,'Functions',infra=self.infra)
    self.moon_base = VideoProducerService(
      self,'MoonBase',
      infra=self.infra,
      camera_name='moon-base')

    self.photos_api = PhotosApiConstruct(self,'PhotosApi',
      landing_zone = landing_zone,
      subnet_group_name= subnet_group_name,
      infra= self.infra)

  def configure_dns(self,zone:r53.IHostedZone, ca:CertificateAuthority)->None:
    self.photos_api.configure_dns(zone, ca)
