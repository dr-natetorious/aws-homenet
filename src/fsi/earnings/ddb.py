import boto3
from  boto3.dynamodb.conditions import Key, Attr
import typing
from models import EarningReport
from datetime import datetime

class CalendarCacheClient:

  def __init__(self, table_name:str) -> None:
    self.table = boto3.resource('dynamodb').Table(table_name)
  
  def get_for_date(self, date:datetime=None, date_str=None) -> typing.List[EarningReport]:
    partition_key = CalendarCacheClient.__get_date_partitionkey(date,date_str)
    response = self.table.query(
      KeyConditionExpression=Key('PartitionKey').eq(partition_key))

    return [EarningReport.from_hash(result) for result in response['Items']]

  def put_for_date(self, reports:typing.List[EarningReport], date:datetime=None, date_str=None):
    partition_key = CalendarCacheClient.__get_date_partitionkey(date,date_str)

    with self.table.batch_writer() as batch:
      for report in reports:
        item = report.to_hash()
        item['PartitionKey'] = partition_key
        item['SortKey'] = item.symbol
        batch.put_item(item)

  @staticmethod
  def __get_date_partitionkey(date:datetime=None, date_str:str=None) -> str:
    if date is None:
      if date_str is None:
        raise AssertionError("Neither date or data_str are set")
      else:
        date = datetime.strptime(date_str,"%Y-%m-%d")

    return "{y}-{m}-{d}".format(d=date.day,m=date.month, y=date.year)