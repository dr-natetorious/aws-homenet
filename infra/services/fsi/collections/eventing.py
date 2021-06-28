import builtins
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_events as e,
)

class FsiCollectionsEventing(core.Construct):
  def __init__(self, scope: core.Construct, id: builtins.str, landing_zone:IVpcLandingZone) -> None:
    super().__init__(scope, id)
    core.Tags.of(self).add('Component', FsiCollectionsEventing.__name__)

    self.event_bus = e.EventBus(self,'EventBus',
      event_bus_name='Fsi{}-Collections'.format(landing_zone.zone_name))

    self.archive = e.Archive(self,'ArchiveEverything',
      source_event_bus=self.event_bus,
      archive_name='Persist-Everything',
      description='Default FsiCollections backup rule',
      retention=core.Duration.days(90),
      event_pattern= e.EventPattern(
      ))
