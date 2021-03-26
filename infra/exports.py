from infra.networking import NetworkingLayer
from infra.subnets.identity import IdentitySubnet
from infra.subnets.netstore import NetStoreSubnet
from infra.subnets.vpn import VpnSubnet

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
  vpn = VpnSubnet(scope,'Vpn',vpc=networking.vpc, directory=identity.mad)

  return [
    networking,
    identity,
    netstore,
    vpn,
  ]
