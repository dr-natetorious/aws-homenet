#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk.core import Construct, Tags
from infra.networking import NetworkingLayer
from infra.subnets.resolver import ResolverSubnet
from infra.subnets.identity import IdentitySubnet
from infra.subnets.netstore import NetStoreSubnet
from infra.subnets.video import VideoSubnet
from infra.subnets.vpn import VpnSubnet
from infra.services.backup import BackupStrategyConstruct
from infra.interfaces import ILandingZone
from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ssm as ssm,
)

src_root_dir = os.path.join(os.path.dirname(__file__))

class LandingZone(ILandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
    Tags.of(self).add('landing_zone',self.zone_name)

    self.networking = NetworkingLayer(self,self.zone_name,
      cidr=self.cidr_block,
      subnet_configuration=self.subnet_configuration)

    self.backup_policy = BackupStrategyConstruct(self,'Backup',
      landing_zone=self)

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

class HomeNet(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
    
    vpc = self.networking.vpc
    VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc
      ).add_ssm_support().add_storage_gateway()

    self.identity = IdentitySubnet(self,'Identity',vpc=vpc)
    self.netstore = NetStoreSubnet(self,'NetStore', vpc=vpc)
    self.vpn = VpnSubnet(self,'Vpn',vpc=vpc, directory=self.identity.mad)
    # self.dns = ResolverSubnet(self,'Dns', vpc=vpc)
    self.video = VideoSubnet(self,'Video',vpc=vpc, subnet_group_name='Vpn-Clients')

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
      ec2.SubnetConfiguration(name='Vpn', subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=27),
      ec2.SubnetConfiguration(name='Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=28),
      ec2.SubnetConfiguration(name='Vpn-Clients', subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=22),
      ec2.SubnetConfiguration(name='TGW', subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=28),
      ec2.SubnetConfiguration(name='DnsResolver', subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=28),
    ]

class Hybrid(LandingZone):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
    
    vpc = self.networking.vpc
    
    # Add endpoints...
    vpce = VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc)
    vpce.add_ssm_support()

  @property
  def cidr_block(self)->str:
    return '10.10.0.0/16'

  @property
  def zone_name(self)->str:
    return 'Hybrid'

  @property
  def subnet_configuration(self)->List[ec2.SubnetConfiguration]:
    return [      
      # 16k addresses x 2 AZ
      ec2.SubnetConfiguration(name='Default', subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=18),
      
      # 8k addresses x 2 AZ
      ec2.SubnetConfiguration(name='Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=19),
      
      # 8k addresses x 2 AZ
      ec2.SubnetConfiguration(name='Reserved', subnet_type=ec2.SubnetType.ISOLATED, cidr_mask=19),
    ]

class Chatham(core.Stack):
  """
  Represents the Site-to-Site for House
  """
  def __init__(self, scope: core.Construct, id: str,vpc:ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    ip_address='100.8.119.43'
    core.Tags.of(self).add('Name','Chatham: '+ip_address)

    customer_gateway = ec2.CfnCustomerGateway(self,'CustomerGateway',
      ip_address=ip_address,
      bgp_asn=65000,
      type='ipsec.1',
      tags=[core.CfnTag(key='Name',value='TP-Link Vpn Router')])

    vpn_gateway = ec2.CfnVPNGateway(self,'VpnGateway',
      amazon_side_asn=64512,
      type='ipsec.1',
      tags=[core.CfnTag(key='Name',value='HomeNet-Gateway')])

    if vpc != None:
      attachment = ec2.CfnVPCGatewayAttachment(self,'HomeNetGatewayAttachment',
        vpc_id=vpc.vpc_id,
        vpn_gateway_id=vpn_gateway.ref)      

      networks = []
      # Reserved
      for net in vpc.isolated_subnets:
        if net is None:
          continue
        networks.append(net)
      # Default
      for net in vpc.private_subnets:
        if net is None:
          continue
        networks.append(net)
      # Public
      for net in vpc.public_subnets:
        if net is None:
          continue
        networks.append(net)

      routes = ec2.CfnVPNGatewayRoutePropagation(self,'GatewayRoutes',
        route_table_ids=[net.route_table.route_table_id for net in networks],
        vpn_gateway_id= vpn_gateway.ref)

      routes.add_depends_on(attachment)
    
    connection = ec2.CfnVPNConnection(self,'Site2Site',
      customer_gateway_id=customer_gateway.ref,
      static_routes_only=True,
      type='ipsec.1',
      tags=[core.CfnTag(key='Name',value='Chatham')],
      vpn_gateway_id= vpn_gateway.ref,
      vpn_tunnel_options_specifications=[
        ec2.CfnVPNConnection.VpnTunnelOptionsSpecificationProperty(
          pre_shared_key='EYE_SEE_YOU',
          tunnel_inside_cidr='169.254.50.92/30'),
        ec2.CfnVPNConnection.VpnTunnelOptionsSpecificationProperty(
          pre_shared_key='EYE_SEE_YOU',
          tunnel_inside_cidr='169.254.51.92/30'),
      ])

    ec2.CfnVPNConnectionRoute(self,'RouteHomebound',
      destination_cidr_block='192.168.0.0/16',
      vpn_connection_id= connection.ref)
