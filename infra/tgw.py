from typing import List
from datetime import datetime
from infra.pmstore import ParameterReader, ParameterReaderProps
from infra.basenet import Virginia,Ireland,Tokyo,Oregon,LandingZone
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    custom_resources as cr,
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
    gateways = {}
    for lz in landing_zones:
      amazon_asn+=1
      gateways[lz] = TransitGatewayLayer.create_gateway(lz,amazon_asn)

    for owner in landing_zones:
      for peer in landing_zones:
        if owner.zone_name >= peer.zone_name:
          continue
        
        scope = core.Construct(owner,'Connect-{}-{}'.format(owner.zone_name,peer.zone_name))
        parameter = ParameterReader(scope,'PeerId',
          props= ParameterReaderProps(
            parameterName='/homenet/{}/tgw/gateway_id'.format(peer.zone_name),
            region= core.Stack.of(peer).region,
            with_decryption=True))

        resource = cr.AwsCustomResource(scope,'CreateTGWPeer',
          policy=cr.AwsCustomResourcePolicy.ANY_RESOURCE,
          on_update=cr.AwsSdkCall(
            service='ec2',
            action='CreateTransitGatewayPeeringAttachment',
            #physical_resource_id=str(datetime.now()),
            parameters={
              'TransitGatewayId': gateways[owner].ref,
              'PeerTransitGatewayId': parameter.value,
              'PeerRegion': core.Stack.of(peer).region
            }))

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

    return gateway

class NetworkingApp(core.App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    self.virginia = Virginia(self,'HomeNet', env=us_east_1)
    self.ireland = Ireland(self,'EuroNet', env=eu_west_1)
    self.tokyo = Tokyo(self,'Tokyo', env=ap_ne_1)
    #self.canada = Canada(self,'Canada', env=ca_central_1)
    self.oregon = Oregon(self,'Oregon', env=us_west_2)

    self.establish_tgw()

    self.replicate_params(
      name='vpcid',
      path='/homenet/{}/vpc/id')

    self.replicate_params(
      name='gatewayid',
      path='/homenet/{}/transit-gateway/gateway_id')

    self.replicate_params(
      name='tgw_region',
      path='/homenet/{}/transit-gateway/region')

  @property
  def zones(self)->List[LandingZone]:
    return [self.virginia, self.ireland, self.tokyo, self.oregon ] #, self.canada]

  def replicate_params(self,name,path)->None:
    for src_zone in self.zones:
      for dest_zone in self.zones:
        if src_zone == dest_zone:
          continue

        remote_value = ParameterReader(src_zone, 'PR_'+name+dest_zone.zone_name,
          props=ParameterReaderProps(
            parameterName=path.format(dest_zone.zone_name),
            region= core.Stack.of(dest_zone).region))

        ssm.CfnParameter(src_zone,'Param_'+name+'_'+dest_zone.zone_name,
          name=path.format(dest_zone.zone_name),
          value=remote_value.value,
          type='String')

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

      ssm.CfnParameter(lz,'TGW-GatewayParameter',
        name='/homenet/{}/transit-gateway/gateway_id'.format(lz.zone_name),
        value=gateway.ref,
        type='String')

      ssm.CfnParameter(lz,'TGW-RegionParameter',
        name='/homenet/{}/transit-gateway/region'.format(lz.zone_name),
        value=core.Stack.of(lz).region,
        type='String')
