from infra.vpce import VpcEndpointsForAWSServices
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_directoryservice as ad,
    aws_eks as eks
)

def attach_file_steam(instance:ec2.Instance, fs:efs.FileSystem)->None:
  instance.add_user_data(
    "#!/bin/bash",
    "yum check-update -y",
    "yum upgrade -y",
    "yum install -y amazon-efs-utils nfs-utils",
    "file_system_id_1=" + fs.file_system_id,
    "efs_mount_point_1=/mnt/efs/",
    "mkdir -p \"${efs_mount_point_1}\"",
    "test -f \"/sbin/mount.efs\" && echo \"${file_system_id_1}:/ ${efs_mount_point_1} efs defaults,_netdev\" >> /etc/fstab || " + "echo \"${file_system_id_1}.efs." + fs.stack.region + ".amazonaws.com:/ ${efs_mount_point_1} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0\" >> /etc/fstab", "mount -a -t efs,nfs4 defaults"
  )

class HomeNetFs(core.Construct):
  def __init__(self, scope: core.Construct, id: str,vpc:ec2.IVpc, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.efs_sg = ec2.SecurityGroup(self,'EfsGroup',
      vpc=vpc,
      allow_all_outbound=True,
      description='Security Group for HomeNet EFS')

    self.efs_sg.add_ingress_rule(
      peer= ec2.Peer.any_ipv4(),
      connection=ec2.Port.all_traffic(),
      description='Allow any traffic')

    self.efs = efs.FileSystem(self,'HomeNetFs',
      vpc= vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='NetStore'),
      file_system_name='homenet',
      security_group= self.efs_sg,
      lifecycle_policy= efs.LifecyclePolicy.AFTER_14_DAYS,
      performance_mode= efs.PerformanceMode.GENERAL_PURPOSE)
