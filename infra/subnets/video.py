from infra.vpce import VpcEndpointsForAWSServices
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
  aws_ssm as ssm,
  aws_lambda as lambda_,
  aws_ecr_assets as assets,
  aws_events as events,
  aws_events_targets as targets,
)

cameras=['live'+str(x) for x in range(0,3)]

class Infra(core.Construct):
  @property
  def vpc(self)->ec2.IVpc:
    return self.__vpc

  @property
  def subnet_group_name(self)->str:
    return self.__subnet_group_name

  def __init__(self,scope:core.Construct, id:str, vpc:ec2.IVpc, subnet_group_name:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__vpc = vpc
    self.__subnet_group_name = subnet_group_name

    self.log_group = logs.LogGroup(self,'LogGroup',
      log_group_name='/homenet/video/',
      retention=logs.RetentionDays.TWO_WEEKS,
      removal_policy= core.RemovalPolicy.DESTROY)

    self.container = ecs.ContainerImage.from_docker_image_asset(
      asset=ecr.DockerImageAsset(self,'VideoProducerContainer',
        directory='src/video-producer',
        file='Dockerfile',
        repository_name='homenet-video-producer-ecs'))

    self.bucket = s3.Bucket(self,'Bucket',
      bucket_name='nbachmei.personal.video.'+core.Stack.of(self).region,
      removal_policy= core.RemovalPolicy.DESTROY,
      lifecycle_rules=[
        s3.LifecycleRule(
          abort_incomplete_multipart_upload_after= core.Duration.days(1),
          expiration= core.Duration.days(90))
      ])

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
      vpc=vpc,
      allow_all_outbound=True,
      description='VideoSubnet Components')

    self.cluster = ecs.Cluster(self,'Cluster',
      vpc=vpc,
      cluster_name='nbachmei-personal-video-'+core.Stack.of(self).region,
      capacity_providers=[
        'FARGATE_SPOT'
      ])

    self.cluster.add_capacity('DefaultCapacity',
      instance_type= ec2.InstanceType.of(
        instance_class= ec2.InstanceClass.BURSTABLE3,
        instance_size=ec2.InstanceSize.NANO),
      allow_all_outbound=True,
      associate_public_ip_address=False,
      min_capacity=1,
      desired_capacity=2,
      max_capacity=3,
      update_type= autoscale.UpdateType.REPLACING_UPDATE,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name))

class VideoProducerFunctions(core.Construct):
  def __init__(self, scope: core.Construct, id: str, 
    infra:Infra,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__infra = infra

    self.repo = assets.DockerImageAsset(self,'Repo',
      directory='src/video-producer',
      file='Dockerfile.lambda',
      repository_name='homenet-video-producer')

    code = lambda_.DockerImageCode.from_ecr(
        repository=self.repo.repository,
        tag=self.repo.image_uri.split(':')[-1])

    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='Role for RTSP Video Producer',
      role_name='video-producer-function@homenet-{}'.format(core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole'
      )])

    self.function = lambda_.DockerImageFunction(self,'VideoProducer',
      code = code,
      role= role,
      function_name='HomeNet-RTSP-VideoProducer',
      description='Python container lambda function for VideoProducer',
      timeout= core.Duration.minutes(1),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= infra.vpc,
      memory_size=128,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=infra.subnet_group_name),
      security_groups=[infra.security_group]
    )

    infra.bucket.grant_write(role)

    self.schedule = events.Schedule.rate(core.Duration.minutes(1))
    camera_targets = [
      targets.LambdaFunction(
        handler=self.function,
        event= events.RuleTargetInput.from_object({
          'SERVER_URI':'rtsp://admin:EYE_SEE_YOU@192.168.0.70/'+camera_name,
          'CAMERA':camera_name,
          'BUCKET':infra.bucket.bucket_name,
        })) for camera_name in cameras]

    self.rule = events.Rule(self,'RTSP-VideoProducer',
        description='Check for updates on HomeNet cameras: ',
        targets=camera_targets,
        enabled=False,
        schedule=self.schedule,
        rule_name='HomeNet-RTSP-VideoProducer')

class VideoProducerService(core.Construct):
  def __init__(self, scope: core.Construct, id: str, 
    infra:Infra,
    camera_name:str,
    **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__infra = infra
    core.Tags.of(self).add('Camera',camera_name)

    definition = ecs.TaskDefinition(self,'ProducerTask',
      compatibility= ecs.Compatibility.EC2,
      cpu='128', memory_mib='128',
      task_role= infra.task_role,
      execution_role= infra.execution_role,
      network_mode= ecs.NetworkMode.AWS_VPC)

    definition.add_container('DefaultContainer',
      memory_reservation_mib=128,
      image = infra.container,
      logging= ecs.AwsLogDriver(
        stream_prefix='video-producer/{}/'.format(camera_name),
        log_group=infra.log_group),
      # secrets= {
      #   'BASE_URI': ecs.Secret.from_ssm_parameter(
      #       ssm.StringParameter.from_string_parameter_name(
      #         self,'BaseUriParam',
      #         string_parameter_name='/homenet/{}/videosubnet/camera-base-uri'.format(
      #           core.Stack.of(self).region)))
      # },
      environment={
        'SERVER_URI':'rtsp://admin:EYE_SEE_YOU@192.168.0.70/'+camera_name,
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
      desired_count=1)

class VideoSubnet(core.Construct):
  def __init__(self, scope: core.Construct, id: str, vpc:ec2.IVpc, subnet_group_name:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    self.__vpc = vpc
    self.__subnet_group_name = subnet_group_name
    core.Tags.of(self).add('Component','VideoSubnet')

    self.infra = Infra(self,'Infra',
      vpc=vpc,
      subnet_group_name=subnet_group_name)

    self.compute = VideoProducerFunctions(self,'Functions',infra=self.infra)

    self.cameras = {}
    for camera in [2]:#range(0,3):
      camera_name='live'+str(camera)
      self.cameras[camera_name] = VideoProducerService(
        self,camera_name,
        infra=self.infra,
        camera_name=camera_name)
