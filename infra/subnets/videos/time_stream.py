from infra.interfaces import ILandingZone
from aws_cdk import (
  core,
  aws_timestream as ts,
)

class TimeStreamConstruct(core.Construct):
  def __init__(self,scope:core.Construct, id:str, landing_zone:ILandingZone, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.database = ts.CfnDatabase(self,'Database',
      database_name='HomeNet-{}-rtsp'.format(landing_zone.zone_name))

    self.people_table = ts.CfnTable(self,'People',
      database_name= self.database.database_name,
      table_name='people')

    self.people_table.add_depends_on(self.database)

      