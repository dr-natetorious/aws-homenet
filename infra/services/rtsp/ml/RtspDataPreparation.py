from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from aws_cdk import (
  core,
  aws_s3 as s3,
  aws_sns as sns,
  aws_s3_notifications as s3n,
  aws_sns_subscriptions as subs,
  aws_sqs as sqs,
)

class RtspDataPreparation(core.Construct):
  """
  Represents the Rtsp Data Preparation Layer
  """
  @property
  def infra(self)->RtspBaseResourcesConstruct:
    return self.__infra

  def __init__(self, scope: core.Construct, id: str,infra:RtspBaseResourcesConstruct, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__infra = infra

    # Create the inventory bucket...
    self.inventories = s3.Bucket(self,'InventoryBucket',
      bucket_name='homenet-{}.rtsp-inventories.{}.virtual.world'.format(
        self.infra.landing_zone.zone_name,
        core.Stack.of(self).region
      ).lower(),
      removal_policy= core.RemovalPolicy.DESTROY,
      lifecycle_rules=[
        s3.LifecycleRule(
          id='Retain_30D',
          abort_incomplete_multipart_upload_after= core.Duration.days(7),
          expiration= core.Duration.days(30))
      ])

    # Create inventory collections for the Eufy Homebases...
    for base_name in ['Moonbase','Starbase']:
      prefix='eufy/{}.cameras.real.world/'.format(base_name).lower()
      self.infra.bucket.add_inventory(
        objects_prefix=prefix,
        inventory_id='{}-InventoryReport'.format(base_name),
        format =s3.InventoryFormat.CSV,
        frequency= s3.InventoryFrequency.DAILY,
        include_object_versions= s3.InventoryObjectVersion.CURRENT,
        destination= s3.InventoryDestination(
          bucket=self.inventories,
          bucket_owner= core.Aws.ACCOUNT_ID,
          prefix=prefix))

    # Broadcast inventory creation events...
    self.inventoryAvailable = sns.Topic(self,'InventoryAvailable',
      display_name='HomeNet-{}-Rtsp-InventoryAvailable'.format(infra.landing_zone.zone_name),
      topic_name='HomeNet-{}-Rtsp-InventoryAvailable'.format(infra.landing_zone.zone_name))

    self.inventories.add_event_notification(
      s3.EventType.OBJECT_CREATED,
      s3n.SnsDestination(topic=self.inventoryAvailable))

    # Attach debug queue to the notification
    self.inventoryAvailable.add_subscription(subs.SqsSubscription(
      queue=sqs.Queue(self,'InventoryDebugQueue',
        queue_name='{}_Debug'.format(self.inventoryAvailable.topic_name),
        removal_policy=core.RemovalPolicy.DESTROY,
        retention_period=core.Duration.days(7)),
      raw_message_delivery=True))
