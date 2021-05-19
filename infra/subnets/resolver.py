from typing import List
from infra.interfaces import IVpcLandingZone
from json import loads
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_route53 as r53,
    aws_route53resolver as r53rsv,
)

class HostedZones(core.Construct):
  """
  Represents the Domain Name service records...
  """
  def __init__(self, scope:core.Construct, id:str,landing_zone:IVpcLandingZone, **kwargs):
    super().__init__(scope,id, **kwargs)
    
    # Create the primary domain
    self.virtual_world = r53.PrivateHostedZone(self,'VirtualWorld',
      zone_name='virtual.world',
      vpc=landing_zone.vpc,
      comment='Primary domain name')

    # Create the real world
    self.real_world = r53.PrivateHostedZone(self,'RealWorld',
      zone_name='real.world',
      vpc=landing_zone.vpc,
      comment='Name resolution back to physical realm')

    # Add the public records...
    with open('chatham.json','r') as f:
      json = loads(f.read())
      for zone in [self.real_world]:
        for entry in json:
          ip = entry['ip']
          name = entry['name']
          record_name = '{}.{}'.format(name,zone.zone_name)
          r53.ARecord(self,record_name,
            zone=self.real_world,
            record_name=record_name,
            target= r53.RecordTarget.from_ip_addresses(ip))

class ResolverSubnet(core.Construct):
  """
  Deploys the Dns Service endpoints used by Chatham
  """
  def __init__(self, scope:core.Construct, id:str, landing_zone:IVpcLandingZone,subnet_group_name:str='Default', **kwargs):
    super().__init__(scope,id, **kwargs)
    self.sg = ec2.SecurityGroup(self,'SG',
      vpc=landing_zone.vpc,
      allow_all_outbound=True,
      description='Dns Resolver Security Group')

    for address in ['10.0.0.0/8', '192.168.0.0/16', '72.88.152.62/32']:
      self.sg.add_ingress_rule(peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.tcp(53),
        description='Allow Dns via TCP from '+address)

      self.sg.add_ingress_rule(peer= ec2.Peer.ipv4(address),
        connection= ec2.Port.udp(53),
        description='Allow Dns via UDP from '+address)

    ipAddresses = [r53rsv.CfnResolverEndpoint.IpAddressRequestProperty(subnet_id=x) 
      for x in landing_zone.vpc.select_subnets(subnet_group_name=subnet_group_name).subnet_ids]

    self.in_resolver = r53rsv.CfnResolverEndpoint(self,'Resolver',
      direction='INBOUND',
      ip_addresses=ipAddresses,
      name='Inbound-Resolver',
      security_group_ids=[self.sg.security_group_id])
