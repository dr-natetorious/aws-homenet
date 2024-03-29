import builtins
from typing import Mapping
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_kms as kms,
  aws_iam as iam,
  aws_secretsmanager as sm,
  aws_eks as eks,
  aws_route53 as r53,
  aws_s3 as s3,
  aws_route53_targets as dns_targets,
)

class FinSpaceEnvironment:
  def __init__(self) -> None:
    self.environment_name = 'HomeNet-FsiCoreSvc'
    self.endpoint_url = 'https://7k6oetkcorie4purjw4p7l.us-east-2.amazonfinspace.com'

class FsiSharedResources(core.Construct):
  
  @property
  def landing_zone(self)->IVpcLandingZone:
    return self.__landing_zone
  
  def __init__(self, scope: core.Construct, id: builtins.str, landing_zone:IVpcLandingZone) -> None:
    super().__init__(scope, id)
    self.__landing_zone = landing_zone

    # Setup DNS...
    self.trader_dns_zone = r53.PrivateHostedZone(self,'Trader',
      zone_name='trader.fsi'.format(
        landing_zone.zone_name.lower()),
      vpc=landing_zone.vpc,
      comment='HomeNet Financial Services Domain')

    # Create a key and delegate access to IAM...
    self.key = kms.Key(self,'Key',
      alias='homenet/fsi',
      enable_key_rotation=True,
      policy=iam.PolicyDocument(
        statements=[
          iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            principals=[iam.AccountPrincipal(
              core.Stack.of(self).account)
            ],
            actions=['kms:*'],
            resources=['*']
          )
        ]
      ))

    # Create central resources...
    self.tda_secret = sm.Secret(self,'AmeritradeSecrets',
      removal_policy=core.RemovalPolicy.DESTROY,
      secret_name='HomeNet-{}-Ameritrade-Secrets'.format(self.landing_zone.zone_name))

    self.bucket = s3.Bucket(self,'Bucket',
      bucket_name='homenet-{}.{}.trader.fsi'.format(
        self.landing_zone.zone_name,
        core.Stack.of(self).region).lower(),
      versioned=True)

    r53.ARecord(self,'BucketAlias',
      zone=self.trader_dns_zone,
      record_name=self.bucket.bucket_domain_name,
      target= r53.RecordTarget.from_alias(dns_targets.BucketWebsiteTarget(self.bucket)))

    # self.fspace = space.CfnEnvironment(self,'Finspace',
    #   name='HomeNet-FsiCoreSvc',
    #   kms_key_id= self.key.key_id,
    #   description="HomeNet Financial Servicing Catalog")
    self.finspace = FinSpaceEnvironment()
    self.key.grant_admin(iam.ServicePrincipal(service='finspace'))
      
    # Setup the EKS cluster....
    # master_role = iam.Role(self,'MasterRole',
    #   assumed_by=iam.AccountPrincipal(account_id=core.Stack.of(self).account),
    #   managed_policies=[
    #     iam.ManagedPolicy.from_aws_managed_policy_name(
    #       managed_policy_name='AmazonEKSClusterPolicy')
    #   ],
    #   role_name='fsi-eks-master-role@HomeNet-{}.{}'.format(
    #     landing_zone.zone_name,
    #     core.Stack.of(self).region).lower())

    # cluster_role = iam.Role(self,'ClusterMasterRole',
    #   assumed_by=iam.ServicePrincipal(service='eks-fargate-pods'),
    #   managed_policies=[
    #     iam.ManagedPolicy.from_aws_managed_policy_name(
    #       managed_policy_name='AmazonEKSFargatePodExecutionRolePolicy'),
    #     iam.ManagedPolicy.from_aws_managed_policy_name(
    #       managed_policy_name='AmazonEKSClusterPolicy')
    #   ],
    #   role_name='fsi-eks-cluster-role@HomeNet-{}.{}'.format(
    #     landing_zone.zone_name,
    #     core.Stack.of(self).region).lower())

    # self.cluster = eks.FargateCluster(self,'Cluster',
    #   endpoint_access= eks.EndpointAccess.PUBLIC_AND_PRIVATE,
    #   security_group= self.landing_zone.security_group,
    #   vpc= self.landing_zone.vpc,
    #   masters_role= master_role,
    #   secrets_encryption_key= self.key,
    #   place_cluster_handler_in_vpc=True,
    #   role= cluster_role,    
    #   vpc_subnets= [ec2.SubnetSelection(subnet_group_name='Default')],
    #   output_cluster_name=True,
    #   output_config_command=True,
    #   version= eks.KubernetesVersion.V1_19,
    #   cluster_name='HomeNet-{}-Fsi'.format(self.landing_zone.zone_name))
