from aws_cdk.aws_lambda import Function
from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
from infra.services.rtsp.analyzers.analysis_function import RtspAnalysisFunction
from aws_cdk import (
  core,
  aws_s3 as s3,
  aws_sns as sns,
  aws_s3_notifications as s3n,
  aws_sns_subscriptions as subs,
  aws_sqs as sqs,
  aws_iam as iam,
  aws_s3objectlambda as s3ol,
)

class RtspGroundTruthManifestGenerationFunction(RtspAnalysisFunction):
  """
  Deploys the Lambda Function that responds to S3 Inventory reports 
  ... and generating Amazon SageMaker GroundTruth manifests.
  """
  @property
  def source_directory(self) -> str:
    return 'src/rtsp/ml/groundtruth-manifest-gen'

  @property
  def function_timeout(self) -> core.Duration:
    return core.Duration.minutes(10)

  @property
  def component_name(self) -> str:
    return 'RtspGroundTruthManGen'

  @property
  def topic(self) -> sns.ITopic:
    return self.__topic
  
  def __init__(self, scope: core.Construct, id: str, infra: RtspBaseResourcesConstruct, topic:sns.ITopic, **kwargs) -> None:
    self.__topic = topic
    super().__init__(scope, id, infra, **kwargs)

class RtspNormalizeImageAccessPointFunction(RtspAnalysisFunction):
  """
  Deploys the Amazon S3 Object Lambda for normalizing images.
  """
  @property
  def source_directory(self) -> str:
    return 'src/rtsp/ml/norm-image-ap'

  @property
  def function_timeout(self) -> core.Duration:
    return core.Duration.minutes(10)

  @property
  def component_name(self) -> str:
    return 'RtspNormImage'

  @property
  def topic(self) -> sns.ITopic:
    return self.__topic
  
  def __init__(self, scope: core.Construct, id: str, infra: RtspBaseResourcesConstruct, **kwargs) -> None:
    super().__init__(scope, id, infra, **kwargs)

class RtspNormalizeImageAccessPoint(core.Construct):
  def __init__(self, scope: core.Construct, infra:RtspBaseResourcesConstruct, id: str) -> None:
    super().__init__(scope, id)
    
    # Create S3 Object Lambda
    normalize_function = RtspNormalizeImageAccessPointFunction(self,'NormalizeImage',
      infra=infra)
    
    accesspoint = s3.CfnAccessPoint(self,'S3-AccessPoint',
      bucket= infra.bucket.bucket_name,
      name='Normalize-Image',
      vpc_configuration= s3.CfnAccessPoint.VpcConfigurationProperty(
        vpc_id= self.infra.vpc.vpc_id
      ))

    # lambda_bind = s3ol.CfnAccessPoint(self,'Lambda-AccessPoint',
    #   name='RtspNormalizeImages',
    #   object_lambda_configuration= s3ol.CfnAccessPoint.ObjectLambdaConfigurationProperty(
    #     supporting_access_point= accesspoint.ref,
    #     cloud_watch_metrics_enabled=True,
    #     transformation_configurations=[
    #       s3ol.CfnAccessPoint.TransformationConfigurationProperty(
    #         actions=['GetObject'],
    #         content_transformation={
    #           'FunctionArn':normalize_function.function.function_arn
    #         }
    #       )
    #     ]
    #   ))

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
      cors= [
        s3.CorsRule(
          allowed_methods=[s3.HttpMethods.GET],
          allowed_origins=['*'])
      ],
      lifecycle_rules=[
        s3.LifecycleRule(
          id='Transition-to-IA-after-30D',
          prefix='eufy/',
          abort_incomplete_multipart_upload_after= core.Duration.days(7),
          transitions=[s3.Transition(
            storage_class= s3.StorageClass.INFREQUENT_ACCESS,
            transition_after= core.Duration.days(30)
          )])
      ])

    # Create inventory collections for the Eufy Homebases...
    self.infra.bucket.add_inventory(
      objects_prefix='eufy/',
      inventory_id='{}-InventoryReport'.format('EufyFull'),
      format =s3.InventoryFormat.CSV,
      frequency= s3.InventoryFrequency.DAILY,
      include_object_versions= s3.InventoryObjectVersion.CURRENT,
      destination= s3.InventoryDestination(
        bucket=self.inventories,
        bucket_owner= core.Aws.ACCOUNT_ID,
        prefix=None))

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
          prefix=None))

    # Broadcast inventory creation events...
    self.inventoryAvailable = sns.Topic(self,'InventoryAvailable',
      display_name='HomeNet-{}-Rtsp-InventoryAvailable'.format(infra.landing_zone.zone_name),
      topic_name='HomeNet-{}-Rtsp-InventoryAvailable'.format(infra.landing_zone.zone_name))

    self.inventories.add_event_notification(
      s3.EventType.OBJECT_CREATED,
      s3n.SnsDestination(topic=self.inventoryAvailable),
      s3.NotificationKeyFilter(suffix='manifest.json'))

    # Attach debug queue to the notification
    self.inventoryAvailable.add_subscription(
      subs.SqsSubscription(
        raw_message_delivery=True,
        queue=sqs.Queue(self,'InventoryDebugQueue',
          removal_policy=core.RemovalPolicy.DESTROY,
          retention_period=core.Duration.days(7),
          queue_name='HomeNet-{}-RtspInventoryAvailable_Debug'.format(
            infra.landing_zone.zone_name)          
        )))

    # Subscribe the GroundTruth Manifest Generator
    groundtruth = RtspGroundTruthManifestGenerationFunction(self,'GroundTruthManifest',
      infra=infra,
      topic=self.inventoryAvailable)
    
    self.inventories.grant_read_write(groundtruth.function.role)

    # Create the RtspNormalizeImage S3 Object Lambda
    #RtspNormalizeImageAccessPoint(self,'NormalizeImage', infra=infra)

    