from typing import List
from datetime import datetime
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_route53resolver as r53,
)

class ResolverSubnet(core.Construct):
  def __init__(self, scope:core.Construct, id:str, vpc:ec2.IVpc, **kwargs):
    """
    Configure Dns Resolver
    """
    super().__init__(scope,id, **kwargs)

    self.sg = ec2.SecurityGroup(self,'SG',
      vpc=vpc,
      allow_all_outbound=True,
      description='Dns Resolver Security Group')

    self.sg.add_ingress_rule(peer= ec2.Peer.any_ipv4(),
      connection= ec2.Port.tcp(53),
      description='Allow Dns via TCP')

    self.sg.add_ingress_rule(peer= ec2.Peer.any_ipv4(),
      connection= ec2.Port.udp(53),
      description='Allow Dns via UDP')

    ipAddresses = [r53.CfnResolverEndpoint.IpAddressRequestProperty(subnet_id=x) for x in vpc.select_subnets(subnet_group_name='DnsResolver').subnet_ids]

    r53.CfnResolverEndpoint(self,'Resolver',
      direction='INBOUND',
      ip_addresses=ipAddresses,
      name='Inbound-Resolver',
      security_group_ids=[self.sg.security_group_id])
