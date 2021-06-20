from typing import Any, List, Mapping
import boto3
from logging import Logger
from time import time
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from math import ceil

logger = Logger('StateStore')
epoch = datetime(1970,1,1)
class StateStore:
  def __init__(self, table_name:str, region_name:str) -> None:
    assert table_name != None, "No table specified"
    self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
    self.table_name = table_name
    self.table = self.dynamodb.Table(self.table_name)

  def retrieve_equity(self)->List[Mapping[str,str]]:
    query = self.table.query(
      KeyConditionExpression=Key('PartitionKey').eq('Fsi::Instruments::EQUITY'))

    return query['Items']

  def set_optionable(self, instruments:List[dict])->None:
    with self.table.batch_writer() as batch:
      try:
        for instrument in instruments:
          if instrument == None:
            continue

          instrument['PartitionKey']= 'Fsi::Optionable'
          instrument['SortKey']= 'Fsi::Optionable::'+str(instrument['symbol']).upper()
          instrument['Expiration']= ceil(StateStore.expiration())
          instrument['last_update']= ceil(time())
          batch.put_item(Item=instrument)
      except Exception as error:
        print(str(error))

  def clear_progress(self, component_name:str)->None:
    return self.set_progress(component_name, marker='')

  def set_progress(self, component_name:str, marker:Any)->None:
    with self.table.batch_writer() as batch:
      try:
        progress = {}
        progress['PartitionKey']= 'Fsi::ProgressMarker'
        progress['SortKey']= component_name
        progress['Expiration']= ceil(StateStore.expiration(days=7))
        progress['last_update']= ceil(time())
        progress['marker'] = marker
        batch.put_item(Item=progress)
      except Exception as error:
        print(str(error))

  def get_progress(self, component_name:str)->Any:
    query = self.table.query(
      KeyConditionExpression=Key('PartitionKey').eq('Fsi::ProgressMarker') & Key('SortKey').eq(component_name))

    marker = query['Items']
    return marker

  def declare_instruments(self,instruments:List[dict])->None:
    try:
      with self.table.batch_writer() as batch:
        for instrument in instruments:
          item = self.declare_instrument(instrument)
          if not item == None:
            batch.put_item(Item=item)
    except Exception as error:
      print(str(error))
      raise error

  def declare_instrument(self, instrument:dict)->Mapping[str,Mapping[str,str]]:
    if StateStore.default_value(instrument,'description') == 'Symbol not found':
      return None
    if StateStore.default_value(instrument,'exchange') == 'Pink Sheet':
      return None
    if StateStore.default_value(instrument,'assertType') == 'UNKNOWN':
      return None

    # Register the instrument
    try:
      assetType = instrument['assetType']
      return {
        'PartitionKey': 'Fsi::Instruments::'+assetType,
        'SortKey': 'Fsi::Instruments::'+str(instrument['symbol']).upper(),
        'Expiration': ceil(StateStore.expiration()),
        'last_update': ceil(time()),

        # Required columns
        'symbol': instrument['symbol'],
        'assetType': assetType,

        # Optional columns
        'description': StateStore.default_value(instrument,'description'),
        'exchange': StateStore.default_value(instrument,'exchange'),
        'cusip': StateStore.default_value(instrument,'cusip'),
        }
      
    except Exception as error:
      logger.error(instrument)
      logger.error(str(error))
      raise error

  @staticmethod
  def expiration(days=90)->int:
    dt = datetime.utcnow() + timedelta(days=days)
    return round((dt-epoch).total_seconds(),0)

  @staticmethod
  def default_value(dict:dict, key:str, default:str='None')->str:
    if not key in dict:
      return default
    if len(str(dict[key])) == 0:
      return default

    return dict[key]
