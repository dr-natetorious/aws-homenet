from infra.services.rtsp.resources.base_resources import RtspBaseResourcesConstruct
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
)

task_drain_time= core.Duration.minutes(0)
min_capacity = 0
max_capacity = 0

install_ssm_script="""
#!/bin/bash
yum -y update && yum -y https://s3.us-east-1.amazonaws.com/amazon-ssm-us-east-1/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl status amazon-ssm-agent
"""
class RtspEcsClusterConstruct(core.Construct):
  def __init__(self,scope:core.Construct, id:str, infra:RtspBaseResourcesConstruct, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    
    self.container = ecs.ContainerImage.from_docker_image_asset(
      asset=ecr.DockerImageAsset(self,'RtspConnectorContainer',
        directory='src/rtsp/connector',
        file='Dockerfile'))

    self.task_role = iam.Role(self,'TaskRole',
      assumed_by=iam.ServicePrincipal(service='ecs-tasks'),
      role_name='ecs-video-producer-task@homenet-{}'.format(core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='AmazonRekognitionFullAccess')
      ],
      description='Role for VideoSubnet Tasks')

    self.execution_role = iam.Role(self,'ExecutionRole',
      assumed_by=iam.ServicePrincipal(service='ecs-tasks'),
      role_name='ecs-rtsp-cluster-execution-role@homenet-{}'.format(core.Stack.of(self).region),      
      description='ECS Execution Role for '+ RtspBaseResourcesConstruct.__name__)

    self.cluster = ecs.Cluster(self,'RtspCluster',
      vpc=self.landing_zone.vpc,
      cluster_name='{}-rtsp-services'.format(infra.landing_zone.zone_name))

    # Tag all cluster resources for auto-domain join.
    core.Tags.of(self.cluster).add('domain','virtual.world')
    
    self.autoscale_group = autoscale.AutoScalingGroup(self,'WinASG',
      security_group=infra.landing_zone.security_group,
      instance_type= ec2.InstanceType.of(
        instance_class= ec2.InstanceClass.BURSTABLE3,
        instance_size=ec2.InstanceSize.SMALL),
      machine_image= ec2.MachineImage.generic_windows(ami_map={
        'us-east-1':'ami-0f93c815788872c5d'
      }),
      vpc= infra.landing_zone.vpc,
      role= self.execution_role,
      allow_all_outbound=True,
      associate_public_ip_address=False,
      #auto_scaling_group_name='{}-Rtsp-Windows'.format(landing_zone.zone_name),
      min_capacity= min_capacity,
      max_capacity= max_capacity,
      rolling_update_configuration= autoscale.RollingUpdateConfiguration(
        min_instances_in_service=0),
      update_type= autoscale.UpdateType.REPLACING_UPDATE,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name))

    self.cluster.add_auto_scaling_group(
      auto_scaling_group= self.autoscale_group,
      can_containers_access_instance_role=True,
      task_drain_time= task_drain_time)

    # Enable management from Managed AD and SSM
    for policy in ['AmazonSSMDirectoryServiceAccess','AmazonSSMManagedInstanceCore']:
      self.autoscale_group.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name=policy))
