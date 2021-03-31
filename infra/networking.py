from infra.vpce import VpcEndpointsForAWSServices
from typing import List
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_directoryservice as ad,
    aws_eks as eks,
    aws_ssm as ssm,
)

class NetworkingLayer(core.Construct):
  """
  Configure the networking layer
  """
  def __init__(self, scope: core.Construct, id: str,cidr:str,subnet_configuration:List[ec2.SubnetConfiguration], **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.vpc = ec2.Vpc(self,'Network',
      cidr=cidr,
      enable_dns_hostnames=True,
      enable_dns_support=True,
      max_azs=2,
      nat_gateways=1,
      subnet_configuration=subnet_configuration)
    
    ssm.CfnParameter(self,'VpcId',
      name='/homenet/{}/vpc/id'.format(id),
      value=self.vpc.vpc_id,
      type='String')

class VpcPeeringConnection(core.Construct):
  """
  Establishes a cross-vpc peering
  """
  def __init__(self, scope: core.Construct, id: str, peer_name:str, vpc:ec2.IVpc, peer_vpc_id:str,peer_region:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.peering = ec2.CfnVPCPeeringConnection(scope,'Peer/'+peer_name,
      peer_region=peer_region,# core.Stack.of(peer).region,
      peer_vpc_id= peer_vpc_id,# peer.vpc_id,
      vpc_id=vpc.vpc_id,
      tags=[
        core.CfnTag(key='Name',value='Peer('+peer_name+')')
      ])

class TransitGatewayLayer(core.Construct):
  def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.gateway = ec2.CfnTransitGateway(self,'TransitGateway',
      amazon_side_asn=64512,
      auto_accept_shared_attachments='enable',
      default_route_table_association='enable',
      default_route_table_propagation='enable',
      description='HomeNet TransitGateway',
      dns_support='enable',
      vpn_ecmp_support='enable',
      tags=[
        core.CfnTag(key='Name',value='HomeNet/TGW')
      ])

class HomeNetVpn(core.Construct):
  """
  Establish the vpn connection
  """
  def __init__(self, scope: core.Construct, id: str,vpc:ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    customer_gateway = ec2.CfnCustomerGateway(self,'CustomerGateway',
      ip_address='173.54.122.113',
      bgp_asn=65000,
      type='ipsec.1',
      tags=[core.CfnTag(key='Name',value='TP-Link Vpn Router')])

    vpn_gateway = ec2.CfnVPNGateway(self,'VpnGateway',
      amazon_side_asn=64512,
      type='ipsec.1',
      tags=[core.CfnTag(key='Name',value='HomeNetGateway')])

    ec2.CfnVPCGatewayAttachment(self,'HomeNetGatewayAttachment',
      vpc_id=vpc.vpc_id,
      vpn_gateway_id=vpn_gateway.ref)

    # [net.route_table.id for net in vpc.select_subnets(subnet_group_name='Vpn').subnets]
    routes = ec2.CfnVPNGatewayRoutePropagation(self,'VpnGatewayRouteProp',
      route_table_ids=['rtb-08ca4caec9e6fcc65','rtb-0112514ba8d55834c'],
      vpn_gateway_id= vpn_gateway.ref)
    routes.add_depends_on(vpn_gateway)
    
    ec2.CfnVPNConnection(self,'Site2Site',
      customer_gateway_id=customer_gateway.ref,
      static_routes_only=True,
      type='ipsec.1',
      vpn_gateway_id= vpn_gateway.ref)