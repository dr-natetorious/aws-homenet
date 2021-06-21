from infra.services.rtsp.analyzers.update_facetable import RtspUpdateFaceTableFunction
from infra.services.rtsp.rtsp_connector import RtspConnectorConstruct
from infra.services.rtsp.analyzers.persist_people import RtspPersistPeopleFunction
from infra.services.core.identity import CertificateAuthority
from infra.services.rtsp.photos_api import PhotosApiConstruct
from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_route53 as r53,
)

class VideoSubnet(core.Construct):
  def __init__(self, scope: core.Construct, id: str, landing_zone:IVpcLandingZone, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add('Component','VideoSubnet')

    self.infra = RtspBaseResourcesConstruct(self,'Infra',
      landing_zone= landing_zone,
      subnet_group_name=subnet_group_name)

    self.rtsp_connector = RtspConnectorConstruct(self,'RtspConnector',
      infra=self.infra)

    self.photos_api = PhotosApiConstruct(self,'PhotosApi',
      subnet_group_name= subnet_group_name,
      infra= self.infra)

    # Add analytical functions...
    self.persist_people = RtspPersistPeopleFunction(self,'PersistPpl',
      infra= self.infra)

    self.persist_people = RtspUpdateFaceTableFunction(self,'UpdateFaceTable',
      infra= self.infra)

  def configure_dns(self,zone:r53.IHostedZone, ca:CertificateAuthority)->None:
    self.photos_api.configure_dns(zone, ca)
    self.rtsp_connector.configure_dns(zone=zone)
