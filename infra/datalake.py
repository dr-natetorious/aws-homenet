from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_directoryservice as ad,
    aws_eks as eks
)

StorageGatewayImage = ec2.MachineImage.generic_linux(      
  ami_map={
  'us-east-1':'ami-03ae10098c64188a7'
  })

class DataLakeLayer(core.Construct):
  """
  Configure the datalake layer
  """
  def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.add_networking()
    self.add_identity()
    self.add_efs_storage()
    self.add_storage_gateway()

  def add_networking(self):
    self.vpc = ec2.Vpc(self,'Network', cidr='10.0.0.0/16',
      enable_dns_hostnames=True,
      enable_dns_support=True,
      max_azs=2,
      nat_gateways=0,
      subnet_configuration=[
        ec2.SubnetConfiguration(name='NetStore', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=24),
        ec2.SubnetConfiguration(name='Identity', subnet_type= ec2.SubnetType.ISOLATED, cidr_mask=27)
      ])
    VpcEndpointsForAWSServices(self,'Endpoints',vpc=self.vpc)

  def add_identity(self):
    self.mad = ad.CfnMicrosoftAD(self,'ActiveDirectory',
      name='virtual.world',
      password='I-l1K3-74(oz',
      short_name='virtualworld',
      enable_sso=False,
      edition= 'Enterprise',
      vpc_settings= ad.CfnMicrosoftAD.VpcSettingsProperty(
        vpc_id=self.vpc.vpc_id,
        subnet_ids= self.vpc.select_subnets(subnet_group_name='Identity').subnet_ids
      ))

  def add_efs_storage(self):
    self.efs_sg = ec2.SecurityGroup(self,'EfsGroup',
      vpc=self.vpc,
      allow_all_outbound=True,
      description='Security Group for HomeNet EFS')

    self.efs_sg.add_ingress_rule(
      peer= ec2.Peer.any_ipv4(),
      connection=ec2.Port.all_traffic(),
      description='Allow any traffic')

    self.efs = efs.FileSystem(self,'HomeNetFs',
      vpc=self.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='NetStore'),
      file_system_name='homenet',
      security_group= self.efs_sg,
      lifecycle_policy= efs.LifecyclePolicy.AFTER_14_DAYS,
      performance_mode= efs.PerformanceMode.GENERAL_PURPOSE)

  def add_storage_gateway(self):
    storage_gateway_bucket = s3.Bucket(self,'StorageBucket',
      bucket_name='nbachmei.homenet.storage-gateway.'+ core.Stack.of(self).region)

    storage_gateway = ec2.Instance(self,'StorageGateway',
      instance_type=ec2.InstanceType.of(
        instance_class= ec2.InstanceClass.MEMORY5,
        instance_size=ec2.InstanceSize.XLARGE),
      vpc= self.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='NetStore'),
      machine_image= StorageGatewayImage,
      allow_all_outbound=True)
