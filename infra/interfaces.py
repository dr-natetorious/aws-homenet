from typing import List, Mapping
from aws_cdk.core import Stack, Construct
from aws_cdk import (
    core,
    aws_ec2 as ec2,
)

class IVpcEndpointsForAWSServices(core.Construct):
  def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.__interfaces = {}
    self.__gateways = {}

  @property
  def interfaces(self)->Mapping[str,ec2.IInterfaceVpcEndpoint]:
    return self.__interfaces

  @property
  def gateways(self)->Mapping[str,ec2.IGatewayVpcEndpoint]:
    return self.__gateways

class ILandingZone(Stack):
  """
  Represents an interface into a deployment environment.
  """
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)
 
  @property
  def zone_name(self)->str:
    raise NotImplementedError()


class IVpcLandingZone(ILandingZone):
  """
  Represents an interface into a deployment environment with Vpc.
  """
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope, id, **kwargs)

  @property
  def cidr_block(self)->str:
    raise NotImplementedError()
  
  @property
  def subnet_configuration(self)->List[ec2.SubnetConfiguration]:
    raise NotImplementedError()

  @property
  def vpc(self)->ec2.IVpc:
    raise NotImplementedError()

  @property
  def security_group(self)->ec2.SecurityGroup:
    raise NotImplementedError()

  @property
  def vpc_endpoints(self)->IVpcEndpointsForAWSServices:
    raise NotImplementedError()