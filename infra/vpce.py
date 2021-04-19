from typing import List
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    core
)


class VpcEndpointsForAWSServices(core.Construct):
  """
  Configure the Vendor Application
  """
  def __init__(self, scope: core.Construct, id: str, vpc: ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.vpc = vpc
    self.interfaces = {}

    self.security_group = ec2.SecurityGroup(
      self, 'EndpointSecurity',
      vpc=vpc,
      allow_all_outbound=True,
      description='SG for AWS Resources in isolated subnet')

    self.security_group.add_ingress_rule(
      peer=ec2.Peer.any_ipv4(),
      connection=ec2.Port(
        protocol=ec2.Protocol.ALL,
        string_representation='Any source'))

  def add_gateways(self)->None:
    self.gateways = {}
    for svc in ['s3', 'dynamodb']:
      self.gateways[svc] = ec2.GatewayVpcEndpoint(
        self, svc,
        vpc=self.vpc,
        service=ec2.GatewayVpcEndpointAwsService(
          name=svc))

  def add_ssm_support(self):
    return self.add_interfaces(services=[
      'ssm', 'ec2messages', 'ec2','ssmmessages','logs'
    ])

  def add_lambda_support(self):
    return self.add_interfaces(services=[
      'elasticfilesystem', 'lambda', 'states',
      'ecr.api', 'ecr.dkr'
    ])

  def add_storage_gateway(self):
    return self.add_interfaces(services=[
      'storagegateway'
    ])

  def add_everything(self):
    return self.add_interfaces(services=[
      'ssm', 'ec2messages', 'ec2',
      'ssmmessages', 'kms', 'elasticloadbalancing',
      'elasticfilesystem', 'lambda', 'states',
      'events', 'execute-api', 'kinesis-streams',
      'kinesis-firehose', 'logs', 'sns', 'sqs',
      'secretsmanager', 'config', 'ecr.api', 'ecr.dkr',
      'storagegateway'
    ])

  def add_interfaces(self, services:List[str]):
    for svc in services:
      if not svc in self.interfaces:
        self.interfaces[svc] = ec2.InterfaceVpcEndpoint(
          self, svc,
          vpc=self.vpc,
          service=ec2.InterfaceVpcEndpointAwsService(name=svc),
          open=True,
          private_dns_enabled=True,
          lookup_supported_azs=True,
          security_groups=[self.security_group])
    
    return self
