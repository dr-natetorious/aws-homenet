from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_directoryservice as ad,
    aws_eks as eks
)

class NetworkingLayer(core.Construct):
  """
  Configure the networking layer
  """
  def __init__(self, scope: core.Construct, id: str,cidr:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.vpc = ec2.Vpc(self,'Network',
      cidr=cidr,
      enable_dns_hostnames=True,
      enable_dns_support=True,
      max_azs=2,
      nat_gateways=0,
      subnet_configuration=[
        ec2.SubnetConfiguration(name='NetStore', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=24),
        ec2.SubnetConfiguration(name='Identity', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=27)
        #ec2.SubnetConfiguration(name='Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=27),
        #ec2.SubnetConfiguration(name='NCU', subnet_type= ec2.SubnetType.PRIVATE, cidr_mask=24)
      ])
    VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc)

class VpcPeeringConnection(core.Construct):
  """
  Establishes a cross-vpc peering
  """
  def __init__(self, scope: core.Construct, id: str, vpc:ec2.IVpc, peer_vpc_id:str,peer_region:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.peering = ec2.CfnVPCPeeringConnection(scope,'Peer',
      peer_region=peer_region,# core.Stack.of(peer).region,
      peer_vpc_id= peer_vpc_id,# peer.vpc_id,
      vpc_id=vpc.vpc_id)