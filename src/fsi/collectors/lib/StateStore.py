from typing import List, Mapping
import boto3
from logging import Logger
from time import time
from datetime import datetime, timedelta
from math import ceil

logger = Logger('StateStore')
epoch = datetime(1970,1,1)
class StateStore:
  def __init__(self, table_name:str, region_name:str) -> None:
    assert table_name != None, "No table specified"
    self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
    self.table_name = table_name
    self.table = self.dynamodb.Table(self.table_name)

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
    if StateStore.__default_value(instrument,'description') == 'Symbol not found':
      return None
    if StateStore.__default_value(instrument,'exchange') == 'Pink Sheet':
      return None
    if StateStore.__default_value(instrument,'assertType') == 'UNKNOWN':
      return None

    # Register the instrument
    try:
      assetType = instrument['assetType']
      return {
        'PartitionKey': 'Fsi::Instruments::'+assetType,
        'SortKey': 'Fsi::Instruments::'+str(instrument['symbol']).upper(),
        'Expiration': ceil(StateStore.__default_expiration()),
        'last_update': ceil(time()),

        # Required columns
        'symbol': instrument['symbol'],
        'assetType': assetType,

        # Optional columns
        'description': StateStore.__default_value(instrument,'description'),
        'exchange': StateStore.__default_value(instrument,'exchange'),
        'cusip': StateStore.__default_value(instrument,'cusip'),
        }
      # return {
      #   'PartitionKey': {'S': 'Fsi::Instruments::'+assetType},
      #   'SortKey': {'S': instrument['symbol']},
      #   'Expiration': {'N': str(StateStore.__default_expiration()) },
      #   'record_type':{'S': 'Fsi::State::Instrument'},
      #   'last_update': {'N': str(round(time(),0)) },

      #   # Required columns
      #   'symbol': {'S': instrument['symbol']},
      #   'assetType': {'S': assetType },

      #   # Optional columns
      #   'description': {'S': StateStore.__default_value(instrument,'description')},
      #   'exchange': {'S':StateStore.__default_value(instrument,'exchange')},
      #   'cusip': {'S': StateStore.__default_value(instrument,'cusip') },
      #   }
    except Exception as error:
      logger.error(instrument)
      logger.error(str(error))
      raise error

  @staticmethod
  def __default_expiration()->int:
    dt = datetime.utcnow() + timedelta(days=90)
    return round((dt-epoch).total_seconds(),0)

  @staticmethod
  def __default_value(dict:dict, key:str, default:str='None')->str:
    if not key in dict:
      return default
    if len(str(dict[key])) == 0:
      return default

    return dict[key]
