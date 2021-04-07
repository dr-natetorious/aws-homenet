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

class CreateAttachment(core.Construct):
  def __init__(self, scope:core.Construct, id:str, owner:LandingZone,peer:LandingZone,**kwargs):
    super().__init__(scope,id, **kwargs)

    peer_region = core.Stack.of(peer).region

    owner_gateway_id = ssm.StringParameter.from_string_parameter_name(self,'OwnerGatewayId',
      string_parameter_name='/homenet/{}/transit-gateway/gateway-id'.format(owner.region))

    policy = cr.AwsCustomResourcePolicy.from_sdk_calls(
        resources= cr.AwsCustomResourcePolicy.ANY_RESOURCE)

    self.peer_gateway_id = cr.AwsCustomResource(self,'get_parameters',
      policy= policy,
      on_create=cr.AwsSdkCall(
        service='SSM',
        action='getParameter',
        parameters={
          'Name': '/homenet/{}/transit-gateway/gateway-id'.format(peer_region),
          'WithDecryption':True,
        },
        region= peer_region,
        physical_resource_id= cr.PhysicalResourceId.of(
          id='/homenet/{}/transit-gateway/gateway-id'.format(peer_region))))

    peer_gateway_id = self.peer_gateway_id.get_response_field('Parameter.Value')

    self.peering_request = cr.AwsCustomResource(self,'Peering',
      policy=policy,
      on_update= cr.AwsSdkCall(
        service='SSM',
        action='getParameter',
        parameters={
          'Name': '/homenet/{}/transit-gateway/attachment-id'.format(peer_region),
          'WithDecryption':True,
        },
        output_path='Parameter.Value',
        physical_resource_id= cr.PhysicalResourceId.from_response('Parameter.Value')),
      on_create= cr.AwsSdkCall(
        service='EC2',
        action='createTransitGatewayPeeringAttachment',
        parameters={
          'TransitGatewayId': owner_gateway_id.string_value,
          'PeerTransitGatewayId':peer_gateway_id,
          'PeerRegion': peer_region,
          'PeerAccountId':core.Stack.of(self).account,
        },
        output_path='TransitGatewayPeeringAttachment.TransitGatewayAttachmentId',
        physical_resource_id= cr.PhysicalResourceId.from_response('TransitGatewayPeeringAttachment.TransitGatewayAttachmentId')))

    ssm.CfnParameter(self,'AttachmentId',
      type='String',
      name='/homenet/{}/transit-gateway/attachment-id'.format(peer_region),
      value= self.peering_request.get_response_field('.'))

  @property
  def attachment_id(self)->str:
    return self.peering_request.get_response_field('TransitGatewayPeeringAttachment.TransitGatewayAttachmentId')

class AcceptAttachment(core.Construct):
  def __init__(self, scope:core.Construct, id:str, attachment_id:str, peer_region:str,**kwargs):
    super().__init__(scope,id, **kwargs)

    policy = cr.AwsCustomResourcePolicy.from_sdk_calls(
        resources= cr.AwsCustomResourcePolicy.ANY_RESOURCE)

    on_create = cr.AwsSdkCall(
      service='EC2',
      action='acceptTransitGatewayPeeringAttachment',
      parameters={
        'TransitGatewayAttachmentId': attachment_id,
      },
      region=peer_region,
      physical_resource_id= cr.PhysicalResourceId.of('Accept_'+id))

    self.accept = cr.AwsCustomResource(self,'AcceptRequest',
      policy= policy,
      on_create= on_create)

  @property
  def attachment_id(self)->str:
    return self.accept.get_response_field('TransitGatewayPeeringAttachment.TransitGatewayAttachmentId')

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
