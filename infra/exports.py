from infra.networking import NetworkingLayer
from infra.subnets.identity import IdentitySubnet
from infra.subnets.netstore import NetStoreSubnet

def create_layers(scope):
  """
  Create the application layers.
  """  
  networking = NetworkingLayer(scope,'DataLake')
  identity = IdentitySubnet(scope,'Identity',vpc=networking.vpc)
  netstore = NetStoreSubnet(scope,'NetStore', vpc=networking.vpc)

  return [
    networking,
    identity,
    netstore,
  ]