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
  def __init__(self, scope:core.Construct, id:str, landing_zone:LandingZone, amazon_asn:int, **kwargs):
    """
    Configure the Transit Gateways
    """
    super().__init__(scope,id, **kwargs)
    
    gateway = ec2.CfnTransitGateway(self,'TransitGateway',
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

    ec2.CfnTransitGatewayAttachment(self,'VpcAttachment',
      subnet_ids= landing_zone.vpc.select_subnets(subnet_group_name='TGW').subnet_ids,
      transit_gateway_id=gateway.ref,
      vpc_id= landing_zone.vpc.vpc_id,
      tags=[core.CfnTag(key='Name',value='HomeNet')])

    ssm.CfnParameter(self,'RegionalGatewayParameter',
      name='/homenet/{}/transit-gateway/gateway-id'.format(landing_zone.region),
      value=gateway.ref,
      type='String')
