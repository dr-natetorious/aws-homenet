from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
)

StorageGatewayImage = ec2.MachineImage.generic_linux(      
  ami_map={
    'us-east-1':'ami-03ae10098c64188a7'
  })

class NetStoreSubnet(core.Construct):
  """
  Configure the datalake layer
  """
  def __init__(self, scope: core.Construct, id: str, vpc:ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add('backup','true')

    self.storage_gateway_bucket = s3.Bucket(self,'StorageBucket',
      bucket_name='nbachmei.homenet.storage-gateway.'+ core.Stack.of(self).region,
      versioned=False)

    # Grant permissions
    iam.CfnServiceLinkedRole(self,'StorageGatewayLinkedRole',
      aws_service_name='storagegateway.amazonaws.com',
      description='Delegation to AWS StorageGateway')

  def add_ec2_gateway(self)->None:
    self.storage_gateway = ec2.Instance(self,'StorageGateway',
      instance_type=ec2.InstanceType.of(
        instance_class= ec2.InstanceClass.MEMORY5,
        instance_size=ec2.InstanceSize.LARGE),
      vpc= vpc,
      user_data_causes_replacement=True,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='NetStore'),
      machine_image= StorageGatewayImage,
      allow_all_outbound=True)

    self.storage_gateway_bucket.grant_read_write(self.storage_gateway.role)
    for policy in [
      'AmazonSSMManagedInstanceCore' ]:
      self.storage_gateway.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(policy))

