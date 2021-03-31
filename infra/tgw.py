from typing import List
from infra.basenet import Virginia,Ireland,Tokyo,Oregon,LandingZone
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ssm as ssm,
)

us_east_1 = core.Environment(region="us-east-1", account='581361757134')
eu_west_1 = core.Environment(region="eu-west-1", account='581361757134')
ap_ne_1 = core.Environment(region='ap-northeast-1', account='581361757134')
us_west_2 = core.Environment(region='us-west-2', account='581361757134')
ca_central_1 =core.Environment(region='ca-central-1', account='581361757134')

class TransitGatewayLayer:
  def __init__(self, landing_zones:List[LandingZone]):
    """
    Configure the Transit Gateways
    """
    amazon_asn=64512
    for lz in landing_zones:
      amazon_asn+=1
      TransitGatewayLayer.create_gateway(lz,amazon_asn)

  @staticmethod
  def create_gateway(lz:LandingZone, amazon_asn:int)->None:
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

    ssm.CfnParameter(lz,'TGW-Parameter',
      name='/homenet/{}/tgw/gateway_id'.format(lz.zone_name),
      value=gateway.ref,
      type='String')

class NetworkingApp(core.App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    self.virginia = Virginia(self,'HomeNet', env=us_east_1)
    self.ireland = Ireland(self,'EuroNet', env=eu_west_1)
    self.tokyo = Tokyo(self,'Tokyo', env=ap_ne_1)
    #self.canada = Canada(self,'Canada', env=ca_central_1)
    self.oregon = Oregon(self,'Oregon', env=us_west_2)

    #self.enable_peering()
    self.establish_tgw()

  @property
  def zones(self)->List[LandingZone]:
    return [self.virginia, self.ireland, self.tokyo, self.oregon ] #, self.canada]

  def establish_tgw(self)->None:
    """
    Configure the Transit Gateways
    """
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

      ssm.CfnParameter(lz,'TGW-Parameter',
        name='/homenet/{}/tgw/gateway_id'.format(lz.zone_name),
        value=gateway.ref,
        type='String')

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