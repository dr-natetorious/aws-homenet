import builtins
from typing import Mapping
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_kms as kms,
  aws_iam as iam,
  aws_secretsmanager as sm,
  aws_finspace as space,
  aws_eks as eks,
  aws_route53 as r53,
)

class FsiSharedResources(core.Construct):
  
  @property
  def landing_zone(self)->IVpcLandingZone:
    return self.__landing_zone
  
  def __init__(self, scope: core.Construct, id: builtins.str, landing_zone:IVpcLandingZone) -> None:
    super().__init__(scope, id)
    self.__landing_zone = landing_zone

    self.dns_zone = r53.PrivateHostedZone.from_private_hosted_zone_id(self, 'DnsZone',
      private_hosted_zone_id='Z020781536ZD8Y9HV5BO8')

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

    self.fspace = space.CfnEnvironment(self,'Environment',
      name='HomeNet-Fsi',
      description="HomeNets Financial Servicing")
      
    # Setup the EKS cluster....
    master_role = iam.Role(self,'MasterRole',
      assumed_by=iam.AccountPrincipal(account_id=core.Stack.of(self).account),
      role_name='fsi-eks-master-role@HomeNet-{}.{}'.format(
        landing_zone.zone_name,
        core.Stack.of(self).region).lower())

    cluster_role = iam.Role(self,'ColusterMasterRole',
      assumed_by=iam.ServicePrincipal(service='eks-fargate-pods'),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='AmazonEKSFargatePodExecutionRolePolicy')
      ],
      role_name='fsi-eks-cluster-role@HomeNet-{}.{}'.format(
        landing_zone.zone_name,
        core.Stack.of(self).region).lower())

    self.cluster = eks.FargateCluster(self,'Cluster',
      endpoint_access= eks.EndpointAccess.PUBLIC_AND_PRIVATE,
      security_group= self.landing_zone.security_group,
      vpc= self.landing_zone.vpc,
      masters_role= master_role,
      secrets_encryption_key= self.key,
      place_cluster_handler_in_vpc=True,
      role= cluster_role,    
      vpc_subnets= [ec2.SubnetSelection(subnet_group_name='Default')],
      output_cluster_name=True,
      output_config_command=True,
      version= eks.KubernetesVersion.V1_19,
      cluster_name='HomeNet-{}-Fsi'.format(self.landing_zone.zone_name))
