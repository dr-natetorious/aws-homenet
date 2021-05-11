#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk import core
from infra.interfaces  import ILandingZone
from infra.basenet import Chatham, CoreServices, Hybrid, VpcPeeringConnection
src_root_dir = os.path.join(os.path.dirname(__file__))

us_east_1 = core.Environment(region="us-east-1", account='581361757134')
us_east_2 = core.Environment(region="us-east-2", account='581361757134')

class NetworkingApp(core.App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    # Deploy core services
    self.core_svc = CoreServices(self,'HomeNet-CoreSvc', env=us_east_2)

    # Main setup
    self.hybrid = Hybrid(self,'HomeNet-Hybrid', env=us_east_1)
    self.chatham = Chatham(self,'HomeNet-Chatham', vpc=self.hybrid.vpc, env=us_east_1)

    # Link the Vpcs...
    self.vpc_peering = VpcPeeringConnection(self,'HomeNet-PeerCoreHybrid',
      vpc_id='vpc-0e10050cc2d4bd007', #self.core_svc.vpc,
      peer_vpc_id= 'vpc-0b0841e660b52b9b9', #self.hybrid.vpc.vpc_id,
      peer_region=us_east_1.region,
      env=us_east_1)


  @property
  def zones(self)->List[ILandingZone]:
    return [ self.virginia, self.chatham ]

app = NetworkingApp()
app.synth()
