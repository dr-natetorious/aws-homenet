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

class IdentitySubnet(core.Construct):
  def __init__(self, scope: core.Construct, id: str, vpc:ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.mad = ad.CfnMicrosoftAD(self,'ActiveDirectory',
      name='virtual.world',
      password='I-l1K3-74(oz',
      short_name='virtualworld',
      enable_sso=False,
      edition= 'Enterprise',
      vpc_settings= ad.CfnMicrosoftAD.VpcSettingsProperty(
        vpc_id= vpc.vpc_id,
        subnet_ids= vpc.select_subnets(subnet_group_name='Identity').subnet_ids
      ))