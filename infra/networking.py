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

    # ssm.CfnParameter(self,'VpcId',
    #   name='/homenet/{}/vpc/id'.format(id),
    #   value=self.vpc.vpc_id,
    #   type='String')

    # ssm.CfnParameter(self,'Cidr',
    #   name='/homenet/{}/vpc/cidr'.format(id),
    #   value=self.vpc.vpc_cidr_block,
    #   type='String')

    # ssm.CfnParameter(self,'RegionVpcId',
    #   name='/homenet/{}/vpc/id'.format(core.Stack.of(self).region),
    #   value=self.vpc.vpc_id,
    #   type='String')

    # ssm.CfnParameter(self,'RegionCidr',
    #   name='/homenet/{}/vpc/cidr'.format(core.Stack.of(self).region),
    #   value=self.vpc.vpc_cidr_block,
    #   type='String')

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
