#!/usr/bin/env python3
import os.path
from aws_cdk.core import App, Stack, Environment, Construct, NestedStack
from infra.exports import create_layers, landing_zone
from infra.networking import VpcPeeringConnection, HomeNetVpn
src_root_dir = os.path.join(os.path.dirname(__file__))

us_east_1 = Environment(region="us-east-1", account='581361757134')
eu_west_1 = Environment(region="eu-west-1", account='581361757134')
ap_ne_1 = Environment(region='ap-northeast-1', account='581361757134')

vpc_ids = {
  'ireland':'vpc-0e953932de63095c4',
  'tokyo':'vpc-0280a30d9b234a71e'
}

app = App()

def create_virginia():
  virginia = Stack(app,'HomeNet', env=us_east_1)
  networking = landing_zone(virginia,'DataLake',cidr='10.0.0.0/16')
  create_layers(virginia,networking)
  return networking

def create_ireland():
  ireland = Stack(app,'EuroNet', env=eu_west_1)
  networking = landing_zone(ireland,'Ireland',cidr='10.10.0.0/16')
  return networking

def create_tokyo():
  tokyo = Stack(app,'Tokyo', env=ap_ne_1)
  networking = landing_zone(tokyo,'Tokyo',cidr='10.20.0.0/16')
  return networking

virginia = create_virginia()
ireland = create_ireland()
tokyo = create_tokyo()

def create_peering():
  VpcPeeringConnection(virginia, 'USE1-to-EUW1',
    vpc=virginia.vpc,
    peer_vpc_id=vpc_ids['ireland'],#ireland.vpc.vpc_id,
    peer_region=eu_west_1.region)

  VpcPeeringConnection(virginia, 'USE1-to-AP1',
    vpc=virginia.vpc,
    peer_vpc_id=vpc_ids['tokyo'],#ireland.vpc.vpc_id,
    peer_region=ap_ne_1.region)

  VpcPeeringConnection(ireland, 'USE1-to-AP1',
    vpc=ireland.vpc,
    peer_vpc_id=vpc_ids['tokyo'],#ireland.vpc.vpc_id,
    peer_region=ap_ne_1.region)

#create_peering()

#vpn = HomeNetVpn(virginia, 'Vpn',virginia.vpc)

app.synth()
