from infra.networking import NetworkingLayer
from infra.subnets.identity import IdentitySubnet
from infra.subnets.netstore import NetStoreSubnet

def landing_zone(scope,name:str,cidr:str):
  """
  """
  networking = NetworkingLayer(scope,name,cidr)
  return networking

def create_layers(scope, networking:NetworkingLayer):
  """
  Create the application layers.
  """  
  identity = IdentitySubnet(scope,'Identity',vpc=networking.vpc)
  netstore = NetStoreSubnet(scope,'NetStore', vpc=networking.vpc)

  return [
    networking,
    identity,
    netstore,
  ]
