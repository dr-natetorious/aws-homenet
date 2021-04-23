from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_s3 as s3,
  aws_ecs as ecs,
  aws_ecr_assets as ecr,
  aws_logs as logs,
  aws_autoscaling as autoscale,
)

class Infra(core.Construct):
  @property
  def vpc(self)->ec2.IVpc:
    return self.__vpc

  @property
  def subnet_group_name(self)->str:
    return self.__subnet_group_name

  def __init__(self,scope:core.Construct, id:str, vpc:ec2.IVpc, subnet_group_name:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__vpc = vpc,
    self.__subnet_group_name = subnet_group_name

    self.log_group = logs.LogGroup(self,'LogGroup',
      log_group_name='/homenet/video/',
      retention=logs.RetentionDays.TWO_WEEKS,
      removal_policy= core.RemovalPolicy.DESTROY)

    self.container = ecs.ContainerImage.from_docker_image_asset(
      asset=ecr.DockerImageAsset(self,'VideoProducerContainer',
        directory='src/video-producer',
        repository_name='homenet-video-producer'))

    self.bucket = s3.Bucket(self,'Bucket',
      bucket_name='nbachmei.personal.video.'+core.Stack.of(self).region,
      removal_policy= core.RemovalPolicy.DESTROY,
      lifecycle_rules=[
        s3.LifecycleRule(
          abort_incomplete_multipart_upload_after= core.Duration.days(1),
          expiration= core.Duration.days(90))
      ])

    self.security_group = ec2.SecurityGroup(self,'SecurityGroup',
      vpc=vpc,
      allow_all_outbound=True,
      description='VideoSubnet Components')

    self.cluster = ecs.Cluster(self,'Cluster',
      vpc=vpc,
      cluster_name='nbachmei-personal-video-'+core.Stack.of(self).region,
      capacity_providers=[
        'FARGATE_SPOT'
      ])

class VideoProducer(core.Construct):
  
  def __init__(self, scope: core.Construct, id: str, 
    infra:Infra,
    camera_name:str,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__infra = infra
    core.Tags.of(self).add('Camera',camera_name)

    definition = ecs.TaskDefinition(self,'ProducerTask',
      compatibility= ecs.Compatibility.EC2_AND_FARGATE,
      cpu='256', memory_mib='512',
      network_mode= ecs.NetworkMode.AWS_VPC)

    definition.add_container('DefaultContainer',
      memory_reservation_mib=512,
      image = infra.container,
      logging= ecs.AwsLogDriver(
        stream_prefix='video-producer/camera_name/',
        log_group=infra.log_group),
      # secrets= {
      #   'PASSWORD': ecs.Secret.from_ssm_parameter(
      #     parameter='/homenet/{}/video/cam{}/password'.format(
      #       core.Stack.of(self).region,
      #       camera))
      # },
      environment={
        'USER': 'admin',
        'PASSWORD': 'Password',
        'RSTP_HOST': '192.168.0.70',
        'CAMERA':camera_name,
        'BUCKET':infra.bucket.bucket_name,
      })

    ecs.Ec2Service(self,'ProducerService',
      service_name='homenet-producer-'+camera_name,
      task_definition= definition,
      assign_public_ip=False,
      cluster= infra.cluster,
      deployment_controller=ecs.DeploymentController(type=ecs.DeploymentControllerType.ECS),
      security_group= infra.security_group,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name=infra.subnet_group_name),
      desired_count=0)

class VideoSubnet(core.Construct):
  def __init__(self, scope: core.Construct, id: str, vpc:ec2.IVpc, subnet_group_name:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__vpc = vpc
    self.__subnet_group_name = subnet_group_name
    core.Tags.of(self).add('Component','VideoSubnet')

    self.infra = Infra(self,'Infra',
      vpc=vpc,
      subnet_group_name=subnet_group_name)    

    self.infra.cluster.add_capacity('DefaultCapacity',
      instance_type= ec2.InstanceType.of(
        instance_class= ec2.InstanceClass.BURSTABLE3,
        instance_size=ec2.InstanceSize.SMALL),
      allow_all_outbound=True,
      associate_public_ip_address=False,
      min_capacity=1,
      desired_capacity=1,
      max_capacity=1,
      spot_price='1.00',
      update_type= autoscale.UpdateType.REPLACING_UPDATE,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name))

    self.cameras = {}
    for camera in range(0,3):
      camera_name='live'+str(camera)
      self.cameras[camera_name] = VideoProducer(
        self,camera_name,
        infra=self.infra,
        camera_name=camera_name)
