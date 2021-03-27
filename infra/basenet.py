#!/usr/bin/env python3
import os.path
from abc import abstractmethod
from typing import List
from aws_cdk.core import App, Stack, Environment, Construct, NestedStack
from infra.exports import create_layers, landing_zone
from infra.networking import VpcPeeringConnection, HomeNetVpn
from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_directoryservice as ad,
    aws_eks as eks
)

src_root_dir = os.path.join(os.path.dirname(__file__))

us_east_1 = Environment(region="us-east-1", account='581361757134')
eu_west_1 = Environment(region="eu-west-1", account='581361757134')
ap_ne_1 = Environment(region='ap-northeast-1', account='581361757134')

vpc_ids = {
  'ireland':'vpc-0e953932de63095c4',
  'tokyo':'vpc-0280a30d9b234a71e'
}

class LandingZone(Stack):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

  #   self.vpc = ec2.Vpc(self,'Network',
  #     cidr=self.cidr_block,
  #     enable_dns_hostnames=True,
  #     enable_dns_support=True,
  #     max_azs=2,
  #     nat_gateways=1,
  #     subnet_configuration=self.subnet_configuration)
  #   VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc)

  # @property
  # @abstractmethod
  # def cidr_block(self) -> str:
  #   raise NotImplementedError()

  # @property
  # @abstractmethod
  # def subnet_configuration(self) -> List[ec2.SubnetConfiguration]:
  #   raise NotImplementedError()

class Virginia(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

    self.networking = landing_zone(self,'DataLake','10.0.0.0/16')
    create_layers(self,self.networking)

  @property
  def cidr_block(self)->str:
    return '10.0.0.0/16'

class Ireland(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

    self.networking = landing_zone(self,'Ireland',cidr='10.10.0.0/16')

class Tokyo(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

    self.networking = landing_zone(self,'Tokyo',cidr='10.20.0.0/16')

class NetworkingApp(App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    self.virginia = Virginia(self,'HomeNet', env=us_east_1)
    self.ireland = Ireland(self,'EuroNet', env=eu_west_1)
    self.tokyo = Tokyo(self,'Tokyo', env=ap_ne_1)