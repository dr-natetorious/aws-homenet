from infra.services.rtsp.secrets import RtspCameraSecrets
from infra.services.rtsp.resources.time_stream import TimeStreamConstruct
from infra.interfaces import IVpcLandingZone
from json import loads
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_kms as kms,
  aws_s3 as s3,
  aws_ecs as ecs,
  aws_ecr as r,
  aws_ecr_assets as ecr,
  aws_logs as logs,
  aws_autoscaling as autoscale,
  aws_sns as sns,
  aws_s3_notifications as s3n,
  aws_dynamodb as ddb,
)

task_drain_time= core.Duration.minutes(0)
min_capacity = 0
max_capacity = 0

install_ssm_script="""
#!/bin/bash
yum -y update && yum -y https://s3.us-east-1.amazonaws.com/amazon-ssm-us-east-1/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl status amazon-ssm-agent
"""

class RtspBaseResourcesConstruct(core.Construct):
  @property
  def landing_zone(self)->IVpcLandingZone:
    return self.__landing_zone
  @property
  def vpc(self)->ec2.IVpc:
    return self.__landing_zone.__vpc

  @property
  def subnet_group_name(self)->str:
    return self.__subnet_group_name

  def __init__(self,scope:core.Construct, id:str, landing_zone:IVpcLandingZone, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)    
    self.__landing_zone = landing_zone
    self.__subnet_group_name = subnet_group_name

    # Init basic resources
    self.log_group = logs.LogGroup(self,'LogGroup',
      log_group_name='/homenet/video/',
      retention=logs.RetentionDays.ONE_DAY,
      removal_policy= core.RemovalPolicy.DESTROY)

    # Add security constraints
    self.security_group = landing_zone.security_group
    self.secrets = RtspCameraSecrets(self,'Secrets',landing_zone=landing_zone)
 
    # Create the stateful bucket
    self.bucket = s3.Bucket(self,'Bucket',
      removal_policy= core.RemovalPolicy.RETAIN,
      bucket_name='homenet-{}.{}.virtual.world'.format(
        'hybrid',#landing_zone.zone_name.lower(),
        core.Stack.of(self).region),
      lifecycle_rules=[
        s3.LifecycleRule(
          abort_incomplete_multipart_upload_after= core.Duration.days(1),
          expiration= core.Duration.days(365)),
        s3.LifecycleRule(
          tag_filters={'Cached':'7d'},
          expiration= core.Duration.days(7))
      ])

    # Create Notification Topics for eventing
    self.frameAnalyzed = sns.Topic(self,'FrameAnalysis',
      display_name='HomeNet-{}-Rtsp-FrameAnalysis'.format(landing_zone.zone_name),
      topic_name='HomeNet-{}-Rtsp-FrameAnalysis'.format(landing_zone.zone_name))

    self.frameUploaded = sns.Topic(self,'RtspFrameUploaded',
      display_name='HomeNet-{}-Rtsp-FrameUploaded'.format(landing_zone.zone_name),
      topic_name='HomeNet-{}-Rtsp-FrameUploaded'.format(landing_zone.zone_name))

    self.bucket.add_event_notification(
      s3.EventType.OBJECT_CREATED,
      s3n.SnsDestination(topic=self.frameUploaded))

    # Setup databases
    self.time_stream = TimeStreamConstruct(self,'TimeStream',
      landing_zone=landing_zone)

    self.face_table = ddb.Table(self,'FaceTable',
      table_name='HomeNet-{}-FaceTable'.format(landing_zone.zone_name),
      partition_key= ddb.Attribute(
        name='PartitionKey',
        type=ddb.AttributeType.STRING),
      sort_key=ddb.Attribute(
        name='SortKey',
        type=ddb.AttributeType.STRING),
      billing_mode= ddb.BillingMode.PAY_PER_REQUEST,
      point_in_time_recovery=True)
