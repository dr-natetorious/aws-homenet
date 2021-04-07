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

class TransitGatewayPeeringProvider(core.Construct):
  def __init__(self, scope:core.Construct, id:str, **kwargs):
    super().__init__(scope,id,**kwargs)

    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='infra/cdk-provider',
      repository_name='cdk-CreateTransitGatewayPeeringAttachment')

    onEvent = lambda_.DockerImageFunction(self,'PeeringHandler',
      function_name='cdk-CreateTransitGatewayPeeringAttachment',
      initial_policy= [
        iam.PolicyStatement(
          effect= iam.Effect.ALLOW,
          actions=["ec2:*"],
          resources=["*"])
      ],
      description='Invoke CreateTransitGatewayPeeringAttachment',
      log_retention= logs.RetentionDays.ONE_WEEK,
      code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1]),
      timeout= core.Duration.minutes(1))

    self.provider = cr.Provider(self,'PeeringProvider',
      on_event_handler=onEvent,
      log_retention= logs.RetentionDays.ONE_WEEK)
    

class TGW_TGW_Attachment(core.Construct):
  def __init__(self, scope:core.Construct, id:str, owner:LandingZone, peer:LandingZone, **kwargs):
    super().__init__(scope,id,**kwargs)

    self.peer_region = core.Stack.of(peer).region

    self.owner_gateway_id = ssm.StringParameter.from_string_parameter_name(self,'OwnerGatewayId',
      string_parameter_name='/homenet/{}/transit-gateway/gateway-id'.format(owner.region))

    self.peer_gateway_id = ParameterReader(self, 'PeerGatewayId',
      props=ParameterReaderProps(
        parameterName='/homenet/{}/transit-gateway/gateway-id'.format(self.peer_region),
        region= self.peer_region))

    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='infra/cdk-provider',
      repository_name='cdk-CreateTransitGatewayPeeringAttachment')

    self.provider = lambda_.DockerImageFunction(self,'PeeringProvider',
      function_name='cdk-provider-CreateTransitGatewayPeeringAttachment',
      initial_policy= [
        iam.PolicyStatement(
          effect= iam.Effect.ALLOW,
          actions=["ec2:*"],
          resources=["*"])
      ],
      description='Invoke CreateTransitGatewayPeeringAttachment',
      code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1]),
      timeout= core.Duration.minutes(1))

    raise NotImplementedError('left off here')
    # core.CustomResource(self,'Resource',
    #   service_token= self.provider.function_arn,
    #   resource_type='Custom::TGWTGWAttachment',
    #   #provider= core.CustomResourceProvider(self,handler=self.provider),
    #   properties={
    #     'TransitGatewayId': self.owner_gateway_id.string_value,
    #     'PeerTransitGatewayId':self.peer_gateway_id.value,
    #     'PeerAccountId':core.Stack.of(owner).account,
    #     'PeerRegion': self.peer_region,
    #   })

    # self.resource = cr.AwsCustomResource(self,'Peering',
    #   policy= cr.AwsCustomResourcePolicy.from_sdk_calls(
    #     resources= cr.AwsCustomResourcePolicy.ANY_RESOURCE),
    #   on_create=cr.AwsSdkCall(
    #     service='lambda',
    #     action='InvokeFunction',
    #     parameters={
    #       'TransitGatewayId': self.owner_gateway_id.string_value,
    #       'PeerTransitGatewayId':self.peer_gateway_id.value,
    #       'PeerRegion': self.peer_region,
    #       'PeerAccountId':core.Stack.of(owner).account,
    #     },
    #     #region= core.Stack.of(owner).region,
    #     #output_path='transitGatewayPeeringAttachment.transitGatewayAttachmentId',
    #     physical_resource_id= cr.PhysicalResourceId.of(
    #       id='Attachment_{}-{}'.format(owner.zone_name,peer.zone_name))))

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
