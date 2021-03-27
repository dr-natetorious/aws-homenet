#!/usr/bin/env python3
import os.path
from aws_cdk.core import App, Stack, Environment, Construct, NestedStack
from infra.exports import create_layers, landing_zone
from infra.networking import VpcPeeringConnection, HomeNetVpn
from infra.basenet import NetworkingApp
src_root_dir = os.path.join(os.path.dirname(__file__))

us_east_1 = Environment(region="us-east-1", account='581361757134')
eu_west_1 = Environment(region="eu-west-1", account='581361757134')
ap_ne_1 = Environment(region='ap-northeast-1', account='581361757134')

vpc_ids = {
  'ireland':'vpc-0e953932de63095c4',
  'tokyo':'vpc-0280a30d9b234a71e'
}

app = NetworkingApp()

app.synth()
