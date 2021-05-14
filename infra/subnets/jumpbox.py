from typing import List
from infra.interfaces import ILandingZone
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam,
)


class JumpBoxConstruct(core.Construct):
  def __init__(self, scope:core.Construct, id:str, landing_zone:ILandingZone, **kwargs):
    """
    Configure Dns Resolver
    """
    super().__init__(scope,id, **kwargs)

    # Only required for debugging the jumpbox
    key_pair_name = None #'nbachmei.personal.'+core.Stack.of(self).region

    self.security_group = ec2.SecurityGroup(self,'SecurityGroup',
      description='JumpBox Security Group', 
      vpc= landing_zone.vpc,
      allow_all_outbound=True)

    # Configure firewall...
    for address in ('72.88.152.62/24', '10.0.0.0/8','192.168.0.0/16'):
      self.security_group.add_ingress_rule(
        peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.all_traffic(),
        description='Grant any from '+address)

      self.security_group.add_ingress_rule(
        peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.all_icmp(),
        description='Grant icmp from '+address)

      self.security_group.add_ingress_rule(
        peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.tcp(3389),
        description='Grant rdp from '+address)

    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(
        service='ec2',
        region=core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'),
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMDirectoryServiceAccess'),
      ])

    self.instance = ec2.Instance(self,'Instance',
      role= role,
      vpc= landing_zone.vpc,
      key_name= key_pair_name,
      instance_type=ec2.InstanceType.of(
        instance_class= ec2.InstanceClass.BURSTABLE3,
        instance_size=ec2.InstanceSize.SMALL),
      allow_all_outbound=True,
      user_data_causes_replacement=True,
      security_group= self.security_group,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      machine_image= ec2.MachineImage.generic_windows(ami_map={
        'us-east-1': 'ami-0f93c815788872c5d',
        'us-east-2': 'ami-0b697c4ae566cad55',
        'eu-west-1': 'ami-03b9a7c8f0fc1808e',
        'us-west-2': 'ami-0b7ebdd52b84c244d',
      }))
    core.Tags.of(self.instance).add('domain','virtual.world')
