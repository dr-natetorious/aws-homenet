#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk.core import App, Stack, Environment, Construct, NestedStack
from infra.networking import VpcPeeringConnection, HomeNetVpn, NetworkingLayer,TransitGatewayLayer
from infra.subnets.identity import IdentitySubnet
from infra.subnets.netstore import NetStoreSubnet
from infra.subnets.vpn import VpnSubnet
from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ssm as ssm,
)

src_root_dir = os.path.join(os.path.dirname(__file__))

# https://stackoverflow.com/questions/59774627/cloudformation-cross-region-reference
vpc_ids = {
  'ireland':'vpc-015bcd20789d6fc50',
  'tokyo':'vpc-020881f58c548c5d0'
}

class LandingZone(Stack):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

    self.networking = NetworkingLayer(self,self.zone_name,
      cidr=self.cidr_block,
      subnet_configuration=self.subnet_configuration)    

  @property
  def cidr_block(self)->str:
    raise NotImplementedError()

  @property
  def zone_name(self)->str:
    raise NotImplementedError()

  @property
  def subnet_configuration(self)->List[ec2.SubnetConfiguration]:
    raise NotImplementedError()

  @property
  def vpc(self)->ec2.IVpc:
    return self.networking.vpc


class Virginia(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
    
    vpc = self.networking.vpc
    VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc)

    self.identity = IdentitySubnet(self,'Identity',vpc=vpc)
    self.netstore = NetStoreSubnet(self,'NetStore', vpc=vpc)
    self.vpn = VpnSubnet(self,'Vpn',vpc=vpc, directory=self.identity.mad)

  @property
  def cidr_block(self)->str:
    return '10.0.0.0/16'

  @property
  def zone_name(self)->str:
    return 'DataLake'

  @property
  def subnet_configuration(self)->List[ec2.SubnetConfiguration]:
    return [
        ec2.SubnetConfiguration(name='NetStore', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=24),
        ec2.SubnetConfiguration(name='Identity', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=27),
        ec2.SubnetConfiguration(name='Vpn', subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=27),
        ec2.SubnetConfiguration(name='Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=28),
        ec2.SubnetConfiguration(name='Vpn-Clients', subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=22),
        ec2.SubnetConfiguration(name='TGW', subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=28),
        #ec2.SubnetConfiguration(name='NCU', subnet_type= ec2.SubnetType.PRIVATE, cidr_mask=24)
      ]

class VpnLandingZone(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

  @property
  def subnet_configuration(self)->List[ec2.SubnetConfiguration]:
    return [
      ec2.SubnetConfiguration(name='Public', subnet_type= ec2.SubnetType.PUBLIC,cidr_mask=24),
      ec2.SubnetConfiguration(name='TGW', subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=28),
    ]

class Ireland(VpnLandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

  @property
  def cidr_block(self)->str:
    return '10.10.0.0/16'

  @property
  def zone_name(self)->str:
    return 'Ireland'  

class Tokyo(VpnLandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

  @property
  def cidr_block(self)->str:
    return '10.20.0.0/16'

  @property
  def zone_name(self)->str:
    return 'Tokyo'

class Canada(VpnLandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

  @property
  def cidr_block(self)->str:
    return '10.30.0.0/16'

  @property
  def zone_name(self)->str:
    return 'Canada'

class Oregon(VpnLandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

  @property
  def cidr_block(self)->str:
    return '10.40.0.0/16'

  @property
  def zone_name(self)->str:
    return 'Oregon'
