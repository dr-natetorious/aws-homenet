import builtins
from typing import Any, Mapping
from aws_cdk.aws_logs import RetentionDays
from infra.services.fsi.resources import FsiSharedResources
from infra.services.fsi.collections.state_machine import FsiLongRunningCollectionProcess
from aws_cdk import (
  core,
  aws_dynamodb as ddb,
  aws_timestream as ts,
)

source_directory = 'src/fsi/collectors'
class FsiCollectionDataStoreConstruct(core.Construct):
  @property
  def component_name(self)->str:
    return FsiCollectionDataStoreConstruct.__name__

  @property
  def resources(self)->FsiSharedResources:
    return self.__resources

  def __init__(self, scope: core.Construct, id: builtins.str, resources:FsiSharedResources, subnet_group_name:str='Default') -> None:
    super().__init__(scope, id)    
    self.__resources = resources

    # Configure the Instrument State Table
    self.instrument_table = ddb.Table(self,'InstrumentTable',
      table_name='Fsi{}-Collection-Instrument'.format(resources.landing_zone.zone_name),
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
    self.instrument_table.add_global_secondary_index(
      partition_key=ddb.Attribute(name='symbol',type=ddb.AttributeType.STRING),
      sort_key=ddb.Attribute(name='SortKey',type=ddb.AttributeType.STRING),
      index_name=self.query_by_symbol_index_name,
      projection_type=ddb.ProjectionType.ALL)

    self.query_by_exchange_name = 'query-by-exchange'
    self.instrument_table.add_global_secondary_index(
      partition_key=ddb.Attribute(name='exchange',type=ddb.AttributeType.STRING),
      sort_key=ddb.Attribute(name='SortKey',type=ddb.AttributeType.STRING),
      index_name=self.query_by_exchange_name,
      projection_type=ddb.ProjectionType.ALL)

    # Configure the Transaction Audit Table
    self.transaction_table = ddb.Table(self,'TransactionTable',
      table_name='Fsi{}-Collection-Transactions'.format(resources.landing_zone.zone_name),
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

    self.timeseries_database = ts.CfnDatabase(self,'Database',
      database_name='HomeNet-Fsi{}'.format(resources.landing_zone.zone_name))

    self.quotes = ts.CfnTable(self,'QuotesTable',
      database_name= self.timeseries_database.database_name,
      table_name='Quotes',
      retention_properties = {
        "MemoryStoreRetentionPeriodInHours": str(365 * 24),
        "MagneticStoreRetentionPeriodInDays": str(365 * 200)
      })
    self.quotes.add_depends_on(self.timeseries_database)