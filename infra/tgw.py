from typing import List
from datetime import datetime
from infra.pmstore import ParameterReader, ParameterReaderProps
from infra.basenet import LandingZone
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_logs as logs,
    custom_resources as cr,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ecr_assets as assets,
    aws_cloudformation as cf,
    custom_resources as cr,
)

class RegionalGatewayLayer(core.Construct):
  def __init__(self, scope:core.Construct, id:str, landing_zone:LandingZone, peers:List[LandingZone], amazon_asn:int, **kwargs):
    """
    Configure the Transit Gateways
    """
    super().__init__(scope,id, **kwargs)
    self.landing_zone = landing_zone
    self.peers = peers
    
    self.gateway = ec2.CfnTransitGateway(self,'TransitGateway',
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

    entries = []
    for peer in peers:
      if peer == landing_zone:
        continue
      entries.append(ec2.CfnPrefixList.EntryProperty(cidr=peer.cidr_block,description=peer.zone_name))

    ec2.CfnPrefixList(self,'PeerPrefix',
      address_family='IPv4',
      entries= entries,
      max_entries=100,
      prefix_list_name='nbachmei.homenet.tgw-peers',
      tags=[core.CfnTag(key='Name',value='HomeNet TGW Prefixes')])

    ec2.CfnTransitGatewayAttachment(self,'VpcAttachment',
      subnet_ids= landing_zone.vpc.select_subnets(subnet_group_name='TGW').subnet_ids,
      transit_gateway_id= self.gateway.ref,
      vpc_id= landing_zone.vpc.vpc_id,
      tags=[core.CfnTag(key='Name',value='HomeNet')])

    ssm.CfnParameter(self,'RegionalGatewayParameter',
      name='/homenet/{}/transit-gateway/gateway-id'.format(landing_zone.region),
      value=self.gateway.ref,
      type='String')

    self.__add_peers()

  def __add_peers(self)->None:
    for peer in self.peers:
      if peer == self.landing_zone:
        continue

      net_counter=0
      isolated = len(peer.vpc.isolated_subnets)
      private= len(peer.vpc.private_subnets)
      routes = core.Construct(self,'{}-I.{}/Pr.{}'.format(peer.zone_name,isolated, private))
      for net in self.landing_zone.vpc.isolated_subnets:
        net_counter+= 1
        ec2.CfnRoute(routes,'I.{}'.format(net_counter),
          route_table_id= net.route_table.route_table_id,
          destination_cidr_block=peer.cidr_block,
          transit_gateway_id=self.gateway.ref)
      for net in self.landing_zone.vpc.private_subnets:
        net_counter+= 1
        ec2.CfnRoute(routes,'Pr.{}'.format(net_counter),
          route_table_id= net.route_table.route_table_id,
          destination_cidr_block=peer.cidr_block,
          transit_gateway_id=self.gateway.ref)
