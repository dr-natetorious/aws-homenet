#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk import core
from infra.interfaces  import ILandingZone
from infra.basenet import Chatham, CoreFinancialServices, Hybrid, VpcPeeringOwner, VpcPeeringReceiver, Artifactory
src_root_dir = os.path.join(os.path.dirname(__file__))

us_east_1 = core.Environment(region="us-east-1", account='581361757134')
us_east_2 = core.Environment(region="us-east-2", account='581361757134')

class NetworkingApp(core.App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    # Deploy code artifacts and cicd...
    self.artifacts = Artifactory(self,'HomeNet-Artifacts', env=us_east_1)

    # Deploy core services
    # Don't touch this identifier. It autogen 'vpc-id' is currently sacred :'(
    self.core_svc = CoreFinancialServices(self,'HomeNet-CoreSvc', env=us_east_2)

    # Main setup
    self.hybrid = Hybrid(self,'HomeNet-Hybrid', env=us_east_1)
    self.chatham = Chatham(self,'HomeNet-Chatham', vpc=self.hybrid.vpc, env=us_east_1)

    # Link the Vpcs...
    VpcPeeringOwner(self,'HomeNet-Peering',
      vpc_id='vpc-0cd3a7c3f73ecae29', #self.core_svc.vpc,
      peer_vpc_id= 'vpc-0b0841e660b52b9b9', #self.hybrid.vpc.vpc_id,
      peer_cidr= '10.10.0.0/16', #self.hybrid.vpc.vpc_cidr_block
      peer_region=us_east_1.region,
      env=us_east_2)

    VpcPeeringReceiver(self,'HomeNet-HybridReceiver',
      vpc_id='vpc-0cd3a7c3f73ecae29', #self.core_svc.vpc,
      peer_vpc_id= 'vpc-0b0841e660b52b9b9', #self.hybrid.vpc.vpc_id,
      owner_cidr='10.20.0.0/16',
      vpc_peering_connection_id= 'pcx-06e27708a9c1d190b',   #self.vpc_peering.peering.ref,
      env=us_east_1)

    # Deploy Identity Policy

  @property
  def zones(self)->List[ILandingZone]:
    return [ self.virginia, self.chatham ]

app = NetworkingApp()
app.synth()
