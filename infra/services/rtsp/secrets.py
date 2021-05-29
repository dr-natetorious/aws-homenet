from infra.interfaces import ILandingZone
from aws_cdk import (
  core,
  aws_iam as iam,
  aws_secretsmanager as sm,
)

class RtspCameraSecrets(core.Construct):
  """
  Represents an ECS service for collecting RTSP frames.
  """
  def __init__(self, scope: core.Construct, id: str,landing_zone:ILandingZone, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    
    self.__secrets = {}
    for itr in [ 
        ('moonbase','moonbase.cameras.real.world'), 
        ('starbase','starbase.cameras.real.world') ]:
      name, url = itr
      self.__secrets[url] = sm.Secret(self,name,
        description=name+' connection identity',
        removal_policy= core.RemovalPolicy.DESTROY,
        secret_name='homenet-{}-{}-connection-secret'.format(
          landing_zone.zone_name,
          name).lower())

  def grant_read(self, grantee:iam.IGrantable)->None:
    for name in self.__secrets.keys():
      secret:sm.Secret = self.__secrets[name]
      secret.grant_read(grantee=grantee)
