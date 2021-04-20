#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk.core import App, Stack, Environment, Construct, NestedStack
from infra.networking import NetworkingLayer
from infra.subnets.resolver import ResolverSubnet
from infra.subnets.identity import IdentitySubnet
from infra.subnets.netstore import NetStoreSubnet
from infra.subnets.vpn import VpnSubnet
from infra.services.backup import BackupStrategy
from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ssm as ssm,
)

src_root_dir = os.path.join(os.path.dirname(__file__))

class LandingZone(Stack):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

    self.networking = NetworkingLayer(self,self.zone_name,
      cidr=self.cidr_block,
      subnet_configuration=self.subnet_configuration)

    self.backup_policy = BackupStrategy(self,'Backup')

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
    VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc
      ).add_ssm_support().add_storage_gateway()

    self.identity = IdentitySubnet(self,'Identity',vpc=vpc)
    self.netstore = NetStoreSubnet(self,'NetStore', vpc=vpc)
    self.vpn = VpnSubnet(self,'Vpn',vpc=vpc, directory=self.identity.mad)
    self.dns = ResolverSubnet(self,'Dns', vpc=vpc)

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
        ec2.SubnetConfiguration(name='DnsResolver', subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=28),
      ]

class VpnLandingZone(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

    VpcEndpointsForAWSServices(self,'VpcEndpointsForAWSServices',vpc=self.vpc).add_ssm_support()

  @property
  def subnet_configuration(self)->List[ec2.SubnetConfiguration]:
    return [
      ec2.SubnetConfiguration(name='Public', subnet_type= ec2.SubnetType.PUBLIC,cidr_mask=24),
      ec2.SubnetConfiguration(name='TGW', subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=28),
      ec2.SubnetConfiguration(name='Bastion', subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=28)
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

class Chatham(core.Stack):
  """
  Establish the vpn connection
  """
  def __init__(self, scope: core.Construct, id: str,vpc:ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    ip_address='100.8.114.6'

    core.Tags.of(self).add('Name','Chatham: '+ip_address)

    customer_gateway = ec2.CfnCustomerGateway(self,'CustomerGateway',
      ip_address=ip_address,
      bgp_asn=65000,
      type='ipsec.1',
      tags=[core.CfnTag(key='Name',value='TP-Link Vpn Router')])

    vpn_gateway = ec2.CfnVPNGateway(self,'VpnGateway',
      amazon_side_asn=64512,
      type='ipsec.1',
      tags=[core.CfnTag(key='Name',value='HomeNetGateway')])

    if vpc != None:
      ec2.CfnVPCGatewayAttachment(self,'HomeNetGatewayAttachment',
        vpc_id=vpc.vpc_id,
        vpn_gateway_id=vpn_gateway.ref)

      ec2.CfnVPNGatewayRoutePropagation(self,'PrivateGatewayRoutes',
        route_table_ids=[net.route_table.route_table_id for net in vpc.private_subnets],
        vpn_gateway_id= vpn_gateway.ref)

      ec2.CfnVPNGatewayRoutePropagation(self,'IsolatedGatewayRoutes',
        route_table_ids=[net.route_table.route_table_id for net in vpc.isolated_subnets],
        vpn_gateway_id= vpn_gateway.ref)
    
    ec2.CfnVPNConnection(self,'Site2Site',
      customer_gateway_id=customer_gateway.ref,
      static_routes_only=True,
      type='ipsec.1',
      vpn_gateway_id= vpn_gateway.ref)