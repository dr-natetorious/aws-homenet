from typing import List
from aws_cdk import (
    core,
    aws_backup as backup,
    aws_iam as iam,
    aws_kms as kms,
    aws_sns as sns,
)

class BackupStrategy(core.Construct):
  def __init__(self, scope:core.Construct, id:str, **kwargs):
    """
    Configure Dns Resolver
    """
    super().__init__(scope,id, **kwargs)

    region = core.Stack.of(self).region

    self.encryption_key = kms.Key(self,'EncryptionKey',
      description='Encryption Key for BackupStrategy')

    self.topic = sns.Topic(self,'Topic')
    self.role = iam.Role(self,'Role',
      description='Account Backup Role',
      assumed_by= iam.ServicePrincipal(service='backup'))

    self.vault = backup.BackupVault(self,'Vault',
      encryption_key=self.encryption_key,
      notification_topic= self.topic,
      backup_vault_name='HomeNet_Vault',
      access_policy= iam.PolicyDocument(
        statements=[
          iam.PolicyStatement(
            effect= iam.Effect.ALLOW,
            resources=["*"],
            actions=['backup:CopyIntoBackupVault'],
            principals= [
              iam.ArnPrincipal(arn = self.role.role_arn) 
            ])
        ]))

    self.default_plan = backup.BackupPlan(self,'DefaultPlan',
      backup_vault= self.vault,
      backup_plan_name='Default Plan ' + region,
      backup_plan_rules=[
        backup.BackupPlanRule.daily(),
        backup.BackupPlanRule.weekly(),
      ])

    self.default_plan.add_selection('SelectionPolicy',
      allow_restores=True,
      role=self.role,
      resources=[
        backup.BackupResource.from_tag("backup", "true"),
        backup.BackupResource.from_tag("backup", "True"),
        backup.BackupResource.from_tag("backup", "TRUE"),
      ])
