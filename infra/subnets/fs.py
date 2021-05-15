from infra.subnets.resolver import HostedZones
from infra.interfaces import IVpcLandingZone
from infra.subnets.identity import DirectoryServicesConstruct
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_fsx as fsx,
    aws_efs as efs,
    aws_route53 as r53,
)

class NetworkFileSystems(core.Construct):
  """
  Configure an AWS Storage Gateway.
  """
  def __init__(self, scope: core.Construct, id: str, landing_zone:IVpcLandingZone, ds:DirectoryServicesConstruct, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add(key='Source',value=NetworkFileSystems.__name__)

    subnet_ids = landing_zone.vpc.select_subnets(subnet_group_name=subnet_group_name).subnet_ids

    single_subnet = subnet_ids[0:1]
    preferred_subnet_id = single_subnet[0]

    self.cold_storage = fsx.CfnFileSystem(self,'WinFs',
      subnet_ids = single_subnet,
      file_system_type='WINDOWS',
      security_group_ids=[ landing_zone.security_group.security_group_id],
      storage_type='HDD', # 'SDD',
      storage_capacity= 2000,
      tags=[
        core.CfnTag(key='Name',value='cold-store'),
      ],
      windows_configuration= fsx.CfnFileSystem.WindowsConfigurationProperty(
        weekly_maintenance_start_time='1:11:00', # Mon 6AM (UTC-5)
        throughput_capacity=8,
        active_directory_id=ds.mad.ref,
        automatic_backup_retention_days=30,
        copy_tags_to_backups=True,
        deployment_type='SINGLE_AZ_2', # MULTI_AZ_1,
        preferred_subnet_id= preferred_subnet_id))

    self.app_data = efs.FileSystem(self,'AppData',
      vpc = landing_zone.vpc,
      enable_automatic_backups=True,
      file_system_name='app-data.virtual.world',
      security_group= landing_zone.security_group,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
      removal_policy= core.RemovalPolicy.SNAPSHOT)

    self.homenet = efs.FileSystem(self,'HomeNet',
      vpc = landing_zone.vpc,
      enable_automatic_backups=True,
      file_system_name='nfs.virtual.world',
      security_group= landing_zone.security_group,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
      removal_policy= core.RemovalPolicy.SNAPSHOT)

    self.homenet.add_access_point('nateb',
      path='/nate-data',
      posix_user=efs.PosixUser(gid='1000', uid='10010'),
      create_acl= efs.Acl(owner_uid='10010',owner_gid='1000',permissions='0755'))

    self.homenet.add_access_point('chu',
      path='/chu',
      posix_user=efs.PosixUser(gid='1000', uid='10020'),
      create_acl= efs.Acl(owner_uid='10020',owner_gid='1000',permissions='0755'))

  def add_alias(self, hosts:r53.PrivateHostedZone)->None:
    # Add efs sources...
    for entry in [('efs', self.homenet.file_system_id), ('app-data', self.app_data.file_system_id)]:
      name, target = entry
      r53.CnameRecord(self,name,
        domain_name='{}.efs.{}.amazonaws.com'.format(
          target,
          core.Stack.of(self).region),
        zone = hosts,
        record_name=name,
        ttl=core.Duration.minutes(5))

    # r53.CnameRecord(self,name,
    #     domain_name=self.cold_storage.attr_lustre_mount_name,
    #     zone = hosts,
    #     record_name=name,
    #     ttl=core.Duration.minutes(5))

