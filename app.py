#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk import core
from infra.tgw import RegionalGatewayLayer
from infra.basenet import Virginia,Ireland,Tokyo,Canada,Oregon, LandingZone, Chatham
src_root_dir = os.path.join(os.path.dirname(__file__))

us_east_1 = core.Environment(region="us-east-1", account='581361757134')
eu_west_1 = core.Environment(region="eu-west-1", account='581361757134')
ap_ne_1 = core.Environment(region='ap-northeast-1', account='581361757134')
us_west_2 = core.Environment(region='us-west-2', account='581361757134')
ca_central_1 =core.Environment(region='ca-central-1', account='581361757134')

class NetworkingApp(core.App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    self.virginia = Virginia(self,'HomeNet', env=us_east_1)
    self.ireland = Ireland(self,'EuroNet', env=eu_west_1)
    self.tokyo = Tokyo(self,'Tokyo', env=ap_ne_1)
    self.canada = Canada(self,'Canada', env=ca_central_1)
    self.oregon = Oregon(self,'Oregon', env=us_west_2)
    self.chatham = Chatham(self,'Chatham', vpc=None, env=us_east_1)

    amazon_asn=64512
    for landing_zone in self.zones:
      amazon_asn+=1
      RegionalGatewayLayer(landing_zone,'RegionalGateway',
        landing_zone=landing_zone,
        amazon_asn=amazon_asn)

  @property
  def zones(self)->List[LandingZone]:
    return [ self.virginia, self.ireland, self.tokyo, self.oregon, self.canada]

  def tag_everything(self)->None:
    for zone in self.zones:
      tags = core.Tags.of(zone)
      tags.add('purpose','homeNet')
      tags.add('maintainer','nateb')
      tags.add('backup','true')

app = NetworkingApp()
app.synth()
