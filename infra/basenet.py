#!/usr/bin/env python3
from infra.subnets.fs import NetworkFileSystems
from infra.subnets.jumpbox import JumpBoxConstruct
import os.path
from typing import List
from aws_cdk.core import Construct, Environment, Stack, Tags
from infra.networking import NetworkingLayer
from infra.subnets.resolver import HostedZones, ResolverSubnet
from infra.subnets.identity import CertificateAuthority, DirectoryServicesConstruct
from infra.subnets.netstore import NetStoreSubnet
from infra.subnets.video import VideoSubnet
from infra.subnets.vpn import VpnSubnet
from infra.services.backup import BackupStrategyConstruct
from infra.interfaces import ILandingZone, IVpcLandingZone, IVpcEndpointsForAWSServices
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

  @property
  def zone_name(self)->str:
    raise NotImplementedError()

class VpcLandingZone(IVpcLandingZone):
  """
  Represents a deployment environment with VPC
  """
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
    Tags.of(self).add('landing_zone',self.zone_name)

    self.networking = NetworkingLayer(self,self.zone_name,
      cidr=self.cidr_block,
      subnet_configuration=self.subnet_configuration)

    self.backup_policy = BackupStrategyConstruct(self,'Backup',
      landing_zone=self)

    self.security_group = ec2.SecurityGroup(self,'SecurityGroup',
      description='Default-SG for {} landing zone'.format(self.zone_name),
      vpc= self.vpc,
      allow_all_outbound=True)
    
    for address in ('72.88.152.62/24', '10.0.0.0/8','192.168.0.0/16'):
      self.security_group.add_ingress_rule(
        peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.all_traffic(),
        description='Grant any from '+address)

      self.security_group.add_ingress_rule(
        peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.all_icmp(),
        description='Grant icmp from '+address)

      self.security_group.add_ingress_rule(
        peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.tcp(3389),
        description='Grant rdp from '+address)

      self.security_group.add_ingress_rule(
        peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.tcp(22),
        description='Grant ssh from '+address)

  @property
  def security_group(self) -> ec2.ISecurityGroup:
    return self.__security_group

  @security_group.setter
  def security_group(self,value:ec2.ISecurityGroup):
    self.__security_group = value

  @property
  def vpc_endpoints(self)->IVpcEndpointsForAWSServices:
    return self.__vpc_e

  @vpc_endpoints.setter
  def vpc_endpoints(self, value:IVpcEndpointsForAWSServices):
    self.__vpc_e = value

  @property
  def cidr_block(self)->str:
    raise NotImplementedError()  

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

  @property
  def vpc(self)->ec2.IVpc:
    return self.networking.vpc

class Hybrid(VpcLandingZone):
  """
  Represents the default landing environment for HomeNet Hybrid
  """
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
    
    vpc = self.networking.vpc
    
    # Add endpoints...
    self.vpc_endpoints = VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc)
    self.vpc_endpoints.add_ssm_support()
    self.vpc_endpoints.add_apigateway_support()

    # Add Core Services...

    ds = DirectoryServicesConstruct(self,'Identity',landing_zone=self)
    ca = CertificateAuthority(self,'Certificates', common_name='cert.virtual.world')

    # Setup name resolutions...
    hosts = HostedZones(self,'HostedZones',landing_zone=self)
    ResolverSubnet(self,'NameResolution', landing_zone=self)    

    # Add filesystems...
    nfs = NetworkFileSystems(self,'NetFs',landing_zone=self, ds=ds)
    nfs.configure_dns(hosts.virtual_world)

    # Add app-level services...
    video = VideoSubnet(self,'Cameras', landing_zone=self)
    video.configure_dns(zone=hosts.virtual_world, ca=ca)

    # Add JumpBox
    JumpBoxConstruct(self,'JumpBox',landing_zone=self)

  @property
  def cidr_block(self)->str:
    return '10.10.0.0/16'

  @property
  def zone_name(self)->str:
    return 'Hybrid'

class CoreServices(VpcLandingZone):
  """
  Represents dedicated environment with shared services
  This avoids lengthy deployments and reduces costs
  """
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
    
    vpc = self.networking.vpc
    
    # Add endpoints...
    self.vpc_endpoints = VpcEndpointsForAWSServices(self,'Endpoints',vpc=vpc)
    self.vpc_endpoints.add_ssm_support()

    # Add services...
    #DirectoryServicesConstruct(self,'Identity',landing_zone=self,subnet_group_name='Default')

    # Add JumpBox
    #JumpBoxConstruct(self,'DevBox',landing_zone=self)

  @property
  def cidr_block(self)->str:
    return '10.20.0.0/16'

  @property
  def zone_name(self)->str:
    return 'CoreSvc'

class Chatham(ILandingZone):
  """
  Represents the Site-to-Site for House
  """
  @property
  def zone_name(self)->str:
    raise 'Chatham'

  def __init__(self, scope: core.Construct, id: str,vpc:ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    ip_address='72.88.152.62'
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


class VpcPeeringOwner(LandingZone):
  """
  Establishes a cross-vpc peering
  """
  def __init__(self, scope: core.Construct, id: str, vpc_id:str, peer_vpc_id:str,peer_region:str,peer_cidr:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    owner = ec2.Vpc.from_lookup(self,'OwnerVpc',vpc_id=vpc_id)
    self.peering = ec2.CfnVPCPeeringConnection(self,'PeerConnection',
      peer_region=peer_region,# core.Stack.of(peer).region,
      peer_vpc_id= peer_vpc_id,# peer.vpc_id,
      vpc_id=vpc_id)

    # Add route from owner to the peer
    for iter in owner.private_subnets:
      ec2.CfnRoute(self, iter.subnet_id,
        route_table_id=iter.route_table.route_table_id,
        destination_cidr_block=peer_cidr,
        vpc_peering_connection_id= self.peering.ref)

  @property
  def zone_name(self) -> str:
    return 'Peering'

class VpcPeeringReceiver(LandingZone):
  def __init__(self, scope: core.Construct, id: str, vpc_id:str, peer_vpc_id:str,owner_cidr:str, vpc_peering_connection_id:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    # Add route from owner to the peer
    peer = ec2.Vpc.from_lookup(self,'PeerVpc',vpc_id=peer_vpc_id)
    for iter in peer.private_subnets:
      ec2.CfnRoute(self, iter.subnet_id,
        route_table_id=iter.route_table.route_table_id,
        destination_cidr_block=owner_cidr,
        vpc_peering_connection_id= vpc_peering_connection_id)

  @property
  def zone_name(self) -> str:
    return 'Hybrid-Receiver'
