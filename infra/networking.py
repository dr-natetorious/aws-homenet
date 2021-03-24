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
  Configure the datalake layer
  """
  def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.vpc = ec2.Vpc(self,'Network', cidr='10.0.0.0/16',
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



# class Foo:
#   def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
#     super().__init__(scope, id, **kwargs)

#     self.add_networking()
#     self.add_identity()
#     self.add_storage_gateway()
#     self.add_ncu()

#   def add_networking(self):
#     self.vpc = ec2.Vpc(self,'Network', cidr='10.0.0.0/16',
#       enable_dns_hostnames=True,
#       enable_dns_support=True,
#       max_azs=2,
#       nat_gateways=1,
#       subnet_configuration=[
#         ec2.SubnetConfiguration(name='NetStore', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=24),
#         ec2.SubnetConfiguration(name='Identity', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=27),
#         ec2.SubnetConfiguration(name='Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=27),
#         ec2.SubnetConfiguration(name='NCU', subnet_type= ec2.SubnetType.PRIVATE, cidr_mask=24)
#       ])
#     VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc)

#   def add_identity(self):
#     self.mad = ad.CfnMicrosoftAD(self,'ActiveDirectory',
#       name='virtual.world',
#       password='I-l1K3-74(oz',
#       short_name='virtualworld',
#       enable_sso=False,
#       edition= 'Enterprise',
#       vpc_settings= ad.CfnMicrosoftAD.VpcSettingsProperty(
#         vpc_id=self.vpc.vpc_id,
#         subnet_ids= self.vpc.select_subnets(subnet_group_name='Identity').subnet_ids
#       ))



#   def add_ncu(self):
#     ncu_bucket = s3.Bucket(self,'NCU',
#       bucket_name='nbachmei.homenet.ncu.'+core.Stack.of(self).region)