from infra.services.core.resolver import HostedZones
from infra.interfaces import IVpcLandingZone
from infra.services.core.identity import DirectoryServicesConstruct
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_fsx as fsx,
    aws_efs as efs,
    aws_route53 as r53,
    aws_route53_targets as r53t,
)

class NetworkFileSystemsConstruct(core.Construct):
  """
  Configure an AWS Storage Gateway.
  """
  def __init__(self, scope: core.Construct, id: str, landing_zone:IVpcLandingZone, ds:DirectoryServicesConstruct, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add(key='Source',value=NetworkFileSystemsConstruct.__name__)

    subnet_ids = landing_zone.vpc.select_subnets(subnet_group_name=subnet_group_name).subnet_ids
    single_subnet = subnet_ids[0:1]
    preferred_subnet_id = single_subnet[0]
    self.windows_storage = fsx.CfnFileSystem(self,'WinFs',
      subnet_ids = single_subnet,
      file_system_type='WINDOWS',
      security_group_ids=[ landing_zone.security_group.security_group_id],
      # HDD min = 2TB / SSD = 32
      storage_type='SSD',
      storage_capacity= 500,
      tags=[
        core.CfnTag(key='Name',value='winfs.virtual.world'),
      ],
      windows_configuration= fsx.CfnFileSystem.WindowsConfigurationProperty(
        weekly_maintenance_start_time='1:11:00', # Mon 6AM (UTC-5)
        # 2^n MiB/s with n between 8 and 2048
        throughput_capacity=16,
        active_directory_id=ds.mad.ref,
        automatic_backup_retention_days=30,
        copy_tags_to_backups=True,
        deployment_type='SINGLE_AZ_2', # MULTI_AZ_1,
        preferred_subnet_id= preferred_subnet_id))

    self.app_data = efs.FileSystem(self,'AppData',
      vpc = landing_zone.vpc,
      enable_automatic_backups=True,
      file_system_name='app-data.efs.virtual.world',
      security_group= landing_zone.security_group,      
      vpc_subnets= ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
      removal_policy= core.RemovalPolicy.SNAPSHOT)

    # self.homenet = efs.FileSystem(self,'HomeNet',
    #   vpc = landing_zone.vpc,
    #   enable_automatic_backups=True,
    #   file_system_name='homenet.virtual.world',
    #   security_group= landing_zone.security_group,
    #   vpc_subnets= ec2.SubnetSelection(subnet_group_name=subnet_group_name),
    #   lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
    #   removal_policy= core.RemovalPolicy.SNAPSHOT)

    # self.homenet_ap_nateb = self.homenet.add_access_point('data',
    #   path='/data',
    #   posix_user=efs.PosixUser(gid='1000', uid='10010'),
    #   create_acl= efs.Acl(owner_uid='0',owner_gid='0',permissions='0777'))

  def configure_dns(self, zone:r53.IHostedZone)->None:
    r53.ARecord(self,'DnsRecord',
      zone=zone,
      comment='Name Record for '+NetworkFileSystemsConstruct.__name__,
      record_name='winfs.{}'.format(zone.zone_name),
      ttl=core.Duration.seconds(60),
      target=r53.RecordTarget(
        values= ['10.10.35.85'] ))

    r53.ARecord(self,'DnsRecord',
      zone=zone,
      comment='Name Record for '+NetworkFileSystemsConstruct.__name__,
      record_name='amznfsxkw4byw3j.{}'.format(zone.zone_name),
      ttl=core.Duration.seconds(60),
      target=r53.RecordTarget(
        values= ['10.10.35.85'] ))
    
    # Add efs sources...
    for entry in [
      # ('homenet.efs.virtual.world', self.homenet.file_system_id), 
      ('app-data.efs.virtual.world', self.app_data.file_system_id)]:
      name, target = entry
      r53.CnameRecord(self,name,
        domain_name='{}.efs.{}.amazonaws.com'.format(
          target,
          core.Stack.of(self).region),
        zone = zone,
        record_name=name,
        ttl=core.Duration.minutes(1))

