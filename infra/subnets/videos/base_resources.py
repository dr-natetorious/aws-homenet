from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_kms as kms,
  aws_s3 as s3,
  aws_ecs as ecs,
  aws_ecr_assets as ecr,
  aws_logs as logs,
  aws_autoscaling as autoscale,
  aws_sns as sns,
  aws_s3_notifications as s3n,
)

cameras=['live'+str(x) for x in range(0,3)]

install_ssm_script="""
#!/bin/bash
yum -y update && yum -y https://s3.us-east-1.amazonaws.com/amazon-ssm-us-east-1/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl status amazon-ssm-agent
"""

class Infra(core.Construct):
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

    self.log_group = logs.LogGroup(self,'LogGroup',
      log_group_name='/homenet/video/',
      retention=logs.RetentionDays.ONE_DAY,
      removal_policy= core.RemovalPolicy.DESTROY)

    self.container = ecs.ContainerImage.from_docker_image_asset(
      asset=ecr.DockerImageAsset(self,'VideoProducerContainer',
        directory='src/rtsp-connector',
        file='Dockerfile',
        repository_name='homenet-rtsp-connector'))

    self.frameAnalyzed = sns.Topic(self,'FrameAnalyzed',
      display_name='HomeNet-VideoFrame-Analyzed',
      topic_name='HomeNet-VideoFrame-Analyzed')

    self.frameUploaded = sns.Topic(self,'VideoFrameUploaded',
      display_name='HomeNet-VideoFrame-Uploaded',
      topic_name='HomeNet-VideoFrame-Uploaded')

    self.bucket = s3.Bucket(self,'Bucket',
      bucket_name='nbachmei.personal.video.v2.'+core.Stack.of(self).region,
      removal_policy= core.RemovalPolicy.DESTROY,
      lifecycle_rules=[
        s3.LifecycleRule(
          abort_incomplete_multipart_upload_after= core.Duration.days(1),
          expiration= core.Duration.days(30))
      ])

    self.bucket.add_event_notification(
      s3.EventType.OBJECT_CREATED,
      s3n.SnsDestination(topic=self.frameUploaded))

    self.task_role = iam.Role(self,'TaskRole',
      assumed_by=iam.ServicePrincipal(service='ecs-tasks'),
      role_name='ecs-video-producer-task@homenet-{}'.format(core.Stack.of(self).region),
      description='Role for VideoSubnet Tasks')

    self.execution_role = iam.Role(self,'ExecutionRole',
      assumed_by=iam.ServicePrincipal(service='ecs-tasks'),
      role_name='ecs-video-producer-execution@homenet-{}'.format(core.Stack.of(self).region),      
      description='Role for Launching VideoSubnet Tasks')

    self.bucket.grant_write(self.task_role)

    self.security_group = ec2.SecurityGroup(self,'SecurityGroup',
      vpc=self.landing_zone.vpc,
      allow_all_outbound=True,
      description='VideoSubnet Components')

    self.cluster = ecs.Cluster(self,'Cluster',
      vpc=self.landing_zone.vpc,
      cluster_name='nbachmei-personal-video-'+core.Stack.of(self).region,
      capacity_providers=[
        'FARGATE_SPOT'
      ])

    self.autoscale_group = self.cluster.add_capacity('DefaultCapacity',
      instance_type= ec2.InstanceType.of(
        instance_class= ec2.InstanceClass.BURSTABLE3,
        instance_size=ec2.InstanceSize.NANO),
      machine_image= ec2.MachineImage.generic_linux(
        user_data=ec2.UserData.for_linux(shebang=install_ssm_script.strip()),
        ami_map={
          'us-east-1':'ami-0d5eff06f840b45e9',
          'us-east-2':'ami-077e31c4939f6a2f3',
          'us-west-2':'ami-0cf6f5c8a62fa5da6',
      }),
      allow_all_outbound=True,
      associate_public_ip_address=False,
      min_capacity=1,
      #desired_capacity=2,
      max_capacity=3,
      update_type= autoscale.UpdateType.REPLACING_UPDATE,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name))

    self.autoscale_group.role.add_managed_policy(
      iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='AmazonSSMManagedInstanceCore'))

    #self.autoscale_group.add_user_data(install_ssm_script)
