import builtins
from typing import Any, Mapping
from aws_cdk.aws_logs import RetentionDays
from infra.services.fsi.resources import FsiSharedResources
from aws_cdk import (
  core,
  aws_dynamodb as ddb,
  aws_ecr_assets as assets,
  aws_lambda as lambda_,
  aws_events as events,
  aws_events_targets as targets,
  aws_iam as iam,
  aws_ec2 as ec2,
  aws_ssm as ssm,
  aws_sqs as sqs,
)


source_directory = 'src/fsi/collectors'
class FsiCollectorConstruct(core.Construct):
  @property
  def component_name(self)->str:
    return FsiCollectorConstruct.__name__

  @property
  def resources(self)->FsiSharedResources:
    return self.__resources

  def __init__(self, scope: core.Construct, id: builtins.str, resources:FsiSharedResources, subnet_group_name:str='Default') -> None:
    super().__init__(scope, id)    
    self.__resources = resources

    self.table = ddb.Table(self,'Table',
      table_name='Fsi{}-Collector'.format(resources.landing_zone.zone_name),
      billing_mode= ddb.BillingMode.PAY_PER_REQUEST,
      point_in_time_recovery=True,
      partition_key=ddb.Attribute(
        name='PartitionKey',
        type=ddb.AttributeType.STRING),
      sort_key=ddb.Attribute(
        name='SortKey',
        type=ddb.AttributeType.STRING),
      time_to_live_attribute='Expiration',
    )

    self.query_by_symbol_index_name = 'query-by-symbol'
    self.table.add_global_secondary_index(
      partition_key=ddb.Attribute(name='symbol',type=ddb.AttributeType.STRING),
      sort_key=ddb.Attribute(name='SortKey',type=ddb.AttributeType.STRING),
      index_name=self.query_by_symbol_index_name,
      projection_type=ddb.ProjectionType.ALL)

    self.query_by_exchange_name = 'query-by-exchange'
    self.table.add_global_secondary_index(
      partition_key=ddb.Attribute(name='exchange',type=ddb.AttributeType.STRING),
      sort_key=ddb.Attribute(name='SortKey',type=ddb.AttributeType.STRING),
      index_name=self.query_by_exchange_name,
      projection_type=ddb.ProjectionType.ALL)

    # Configure role...
    role = iam.Role(self,'Role',
      assumed_by=iam.ServicePrincipal(service='lambda'),
      description='Ameritrade Data Collection Lambda via '+self.component_name,
      role_name='{}@homenet-{}.{}'.format(
        self.component_name,
        resources.landing_zone.zone_name,
        core.Stack.of(self).region),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
          managed_policy_name='service-role/AWSLambdaVPCAccessExecutionRole')        
      ])

    resources.tda_secret.grant_read(role)
    self.table.grant_read_write_data(role)

    # Configure the lambda...
    self.repo = assets.DockerImageAsset(self,'Repo',
      directory=source_directory)

    code = lambda_.DockerImageCode.from_ecr(
      repository=self.repo.repository,
      tag=self.repo.image_uri.split(':')[-1])    

    self.function = lambda_.DockerImageFunction(self,'Function',
      code = code,
      role= role,
      function_name='HomeNet-Fsi{}-{}'.format(
        resources.landing_zone.zone_name,
        self.component_name),
      description='Python container function for '+self.component_name,
      timeout= core.Duration.minutes(15),
      tracing= lambda_.Tracing.ACTIVE,
      vpc= resources.landing_zone.vpc,
      log_retention= RetentionDays.TWO_WEEKS,
      memory_size=512,
      allow_all_outbound=True,
      vpc_subnets=ec2.SubnetSelection(subnet_group_name=subnet_group_name),
      security_groups=[resources.landing_zone.security_group],
      environment={
        'REGION':core.Stack.of(self).region,
        'TDA_SECRET_ID': resources.tda_secret.secret_arn,
        'TDA_REDIRECT_URI':  ssm.StringParameter.from_string_parameter_name(self,'TDA_REDIRECT_URI',
          string_parameter_name='/HomeNet/Amertitrade/redirect_uri').string_value,
        'TDA_CLIENT_ID': ssm.StringParameter.from_string_parameter_name(self, 'TDA_CLIENT_ID',
          string_parameter_name='/HomeNet/Ameritrade/client_id').string_value,
        'STATE_TABLE_NAME': self.table.table_name,
      }
    )

    self.add_schedule('DiscoverInstruments',
      schedule=events.Schedule.cron(week_day='SUN',hour="0", minute="0"),
      payload={
        'AssetTypes' : [
          "EQUITY",
          "ETF",
          "FOREX",
          "FUTURE",
          "FUTURE_OPTION",
          "INDEX",
          "INDICATOR",
          # "MUTUAL_FUND",
          "OPTION",
          # "UNKNOWN"
        ]
      })

    self.add_schedule('DiscoverOptionable',
      schedule=events.Schedule.cron(week_day='SUN',hour="1", minute="0"))

    self.add_schedule('CollectFundamentals',
      schedule=events.Schedule.cron(week_day='SUN',hour="2", minute="0"))

    self.add_schedule('CollectFinalQuotes',
      schedule=events.Schedule.cron(week_day='MON-FRI',hour="23", minute="0"))
    
    self.add_schedule('CollectTransactions',
      schedule=events.Schedule.cron(week_day='SUN-FRI', minute="30"))

  def add_schedule(self, action:str, schedule:events.Schedule, payload:Mapping[str,Any]=None)->None:
    """
    Creates a collection schedule
    """
    if payload == None:
      payload={}
    payload['Action']=action

    # Create schedules...
    events.Rule(self,action+'Rule',
      rule_name='Fsi{}-Collector_{}'.format(self.resources.landing_zone.zone_name, action),
      description='Fsi Collector '+action,
      schedule= schedule,
      #schedule= events.Schedule.rate(core.Duration.minutes(1)),
      targets=[
        targets.LambdaFunction(
          handler=self.function,
          dead_letter_queue=sqs.Queue(self,'{}_dlq'.format(action),
            queue_name='Fsi{}-Collector_{}_dlq'.format(
              self.resources.landing_zone.zone_name,
              action),
            removal_policy= core.RemovalPolicy.DESTROY),
          event=events.RuleTargetInput.from_object(payload))
      ])
