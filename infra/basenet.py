#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk.core import App, Stack, Environment, Construct, NestedStack
from infra.exports import create_layers, landing_zone
from infra.networking import VpcPeeringConnection, HomeNetVpn, NetworkingLayer,TransitGatewayLayer
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

    create_layers(self,self.networking)

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
      ec2.SubnetConfiguration(name='Vpn-Clients', subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=22),
      ec2.SubnetConfiguration(name='Identity',subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=27),
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

class NetworkingApp(App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    self.virginia = Virginia(self,'HomeNet', env=us_east_1)
    self.ireland = Ireland(self,'EuroNet', env=eu_west_1)
    self.tokyo = Tokyo(self,'Tokyo', env=ap_ne_1)

    #self.enable_peering()
    self.establish_tgw()

  @property
  def zones(self)->List[LandingZone]:
    return [self.virginia, self.ireland, self.tokyo]

  def establish_tgw(self)->None:
    
    amazon_asn=64512
    for lz in self.zones:
      amazon_asn+=1
      gateway = ec2.CfnTransitGateway(lz,'TransitGateway',
        amazon_side_asn=amazon_asn,
        auto_accept_shared_attachments='enable',
        default_route_table_association='enable',
        default_route_table_propagation='enable',
        description='HomeNet TransitGateway',
        dns_support='enable',
        vpn_ecmp_support='enable',
        tags=[
          core.CfnTag(key='Name',value='HomeNet/TGW')
        ])

      ec2.CfnTransitGatewayAttachment(lz,'TGWAttachment',
        subnet_ids=lz.vpc.select_subnets(subnet_group_name='TGW').subnet_ids,
        transit_gateway_id=gateway.ref,
        vpc_id= lz.vpc.vpc_id,
        tags=[core.CfnTag(key='Name',value='HomeNet')])

    # tgw_id = 'tgw-07adabd18626cda96'

    # for lz in self.get_zones():      
    #   ec2.CfnTransitGatewayAttachment(lz,'TGWAttachment',
    #     subnet_ids=lz.vpc.select_subnets(subnet_group_name='TGW').subnet_ids,
    #     transit_gateway_id=tgw_id,
    #     vpc_id= lz.vpc.vpc_id,
    #     tags=[core.CfnTag(key='Name',value='HomeNet')])

  def enable_peering(self):
    VpcPeeringConnection(self.virginia,'Connection/Ireland',
      peer_name='Ireland',
      vpc=self.virginia.vpc,
      peer_vpc_id=vpc_ids['ireland'],
      peer_region='eu-west-1')

    VpcPeeringConnection(self.virginia,'Connection/Tokyo',
      peer_name='Tokyo',
      vpc=self.virginia.vpc,
      peer_vpc_id=vpc_ids['tokyo'],
      peer_region='ap-northeast-1')