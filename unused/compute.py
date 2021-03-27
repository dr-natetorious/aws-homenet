import os.path
from infra.datalake import DataLakeLayer
from aws_cdk import (
    core,
    aws_sqs as sqs,
    aws_lambda_event_sources as events,
    aws_lambda as lambda_,
    aws_ecr_assets as ecr,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_efs as efs
)

root_dir = os.path.join(os.path.dirname(__file__),'..')

class AnalyzerLambda(core.Construct):
  @property
  def datalake(self) -> DataLakeLayer:
    return self.__datalake

  def __init__(self,scope:core.Construct, id:str, datalake:DataLakeLayer, project_name:str, concurrency:int=5, **kwargs) ->None:
    super().__init__(scope,id,**kwargs)

    self.__datalake = datalake
    repo = ecr.DockerImageAsset(self,'Repo',
      directory=os.path.join(root_dir, project_name),
      repository_name=project_name)

    self.function = lambda_.DockerImageFunction(self,project_name+'-repo',
      code = lambda_.DockerImageCode.from_ecr(
        repository=repo.repository,
        tag=repo.image_uri.split(':')[-1]), # lambda_.DockerImageCode.from_image_asset(directory=os.path.join(src_root_dir,directory)),
      description='Python container lambda function for '+repo.repository.repository_name,
      timeout= core.Duration.minutes(15),
      memory_size=4096,
      tracing= lambda_.Tracing.ACTIVE, 
      # Note: This throttles the AWS S3 batch job.
      # Downloading too fast will cause f-droid to disconnect the crawler
      reserved_concurrent_executions= concurrency,
      filesystem= lambda_.FileSystem.from_efs_access_point(
        ap= self.datalake.efs.add_access_point(
          project_name,
          path='/'+project_name,
          create_acl=efs.Acl(owner_gid="0", owner_uid="0", permissions="777")),
        mount_path='/mnt/efs'
      ),
      environment={
        'EFS_MOUNT':'/mnt/efs'
      },
      vpc= self.datalake.vpc)

    for name in [
      'AmazonElasticFileSystemClientFullAccess',
      'AWSXrayWriteOnlyAccess',
      'AmazonS3FullAccess',
      'AWSCodeCommitFullAccess',
      'AmazonCodeGuruReviewerFullAccess' ]:
      self.function.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(name))

class ComputeLayer(core.Construct):
  """
  Configure the compute layer
  """
  @property
  def datalake(self) -> DataLakeLayer:
    return self.__datalake

  def __init__(self, scope: core.Construct, id: str,datalake:DataLakeLayer, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.__datalake=datalake
    self.add_devbox()
    self.add_reviewer()
    AnalyzerLambda(scope,'fdroid-scrape-repo',
      project_name='fdroid-scrape-repo',
      datalake=datalake)

    AnalyzerLambda(scope,'review-result-sanitizer',
      project_name='review-result-sanitizer',
      datalake=datalake)

    ecr.DockerImageAsset(self,'fdroid-scrape',
      directory=os.path.join(root_dir,'fdroid-scrape'),
      repository_name='fdroid-scrape')

    ecr.DockerImageAsset(self,'review-result-downloader',
      directory=os.path.join(root_dir,'review-result-downloader'),
      repository_name='review-result-downloader')

  def add_reviewer(self):
    reviewer = AnalyzerLambda(self,'review-queued-repo',
      project_name='review-queued-repo',
      concurrency= 50,
      datalake=self.datalake)

    queue = sqs.Queue(self,'PendingReviewQueue', 
      visibility_timeout= core.Duration.minutes(15))
    reviewer.function.add_event_source(events.SqsEventSource(queue=queue, batch_size=1))

  def add_devbox(self):
    """
    Create single node for development
    """
    self.devbox = ec2.Instance(self,'DevBox',
      instance_type=ec2.InstanceType('t2.medium'),
      machine_image= ec2.MachineImage.latest_amazon_linux(
        cpu_type=ec2.AmazonLinuxCpuType.X86_64,
        storage= ec2.AmazonLinuxStorage.GENERAL_PURPOSE
      ),
      vpc=self.datalake.vpc,
      allow_all_outbound=True)

    if self.datalake.efs.file_system_id == None:
      raise AssertionError('No filesystem id present')

    self.devbox.add_user_data(
      "yum check-update -y",
      "yum upgrade -y",
      "yum install -y amazon-efs-utils nfs-utils docker",
      "service docker start",
      "file_system_id_1=" + self.datalake.efs.file_system_id,
      "efs_mount_point_1=/mnt/efs/",
      "mkdir -p \"${efs_mount_point_1}\"",
      "test -f \"/sbin/mount.efs\" && echo \"${file_system_id_1}:/ ${efs_mount_point_1} efs defaults,_netdev\" >> /etc/fstab || " + "echo \"${file_system_id_1}.efs." + core.Stack.of(self).region + ".amazonaws.com:/ ${efs_mount_point_1} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0\" >> /etc/fstab", "mount -a -t efs,nfs4 defaults"
    )

    for policy in [
      'AmazonSSMManagedInstanceCore',
      'AmazonS3FullAccess',
      'AWSCodeCommitFullAccess',
      'AmazonCodeGuruReviewerFullAccess',
      'AmazonEC2ContainerRegistryPowerUser']:
      self.devbox.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(policy))
