from decimal import Decimal
from lib.enums import SecurityStatus
from typing import Any, List, Mapping
import boto3
from logging import Logger
from time import time
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from math import ceil
#from aws_xray_sdk.core import xray_recorder

logger = Logger('StateStore')
epoch = datetime(1970,1,1)
class StateStore:
  """
  Represents a storage interface for the FsiCollections Service.
  """
  def __init__(self, instrument_table_name:str, transaction_table_name:str, quotes_table_name:str, options_table_name:str, region_name:str) -> None:
    assert instrument_table_name != None, "No instrument_table_name specified"
    assert transaction_table_name != None, "No transaction_table_name specified"
    assert quotes_table_name != None, "No quotes_table_name specified"
    assert options_table_name != None, "No options_table_name specified"
    
    self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
    
    # Configure instrument_table
    self.instrument_table = self.dynamodb.Table(instrument_table_name)
    self.transaction_table = self.dynamodb.Table(transaction_table_name)
    self.quotes_table = self.dynamodb.Table(quotes_table_name)
    self.options_table = self.dynamodb.Table(options_table_name)

  @staticmethod
  def query_table(table, query_kwags:dict)->List[dict]:
    """
    Paginates across all response pages and returns one final list.
    """
    done = False
    start_key = None
    items = []
    while not done:
      if start_key:
        query_kwags['ExclusiveStartKey'] = start_key

      response = table.query(**query_kwags)
      items.extend(response.get('Items',[]))
      start_key = response.get('LastEvaluatedKey',None)
      done = start_key is None

    return items

  def retrieve_equities(self, filter_status:List[SecurityStatus]=None)->List[Mapping[str,str]]:
    query_kwags = {
      'KeyConditionExpression':Key('PartitionKey').eq('Fsi::Instruments::EQUITY'),
    }

    query = StateStore.query_table(self.instrument_table, query_kwags)
    results=[]
    for item in query:
      if not 'securityStatus' in item:
        continue

      # Get Security Type
      try:
        securityStatus = SecurityStatus[item['securityStatus'].upper()]
      except:
        securityStatus = SecurityStatus.NOTIMPLEMENTED

      if securityStatus in filter_status:
        continue
      results.append(item)

    return results

  def retrieve_optionable(self)->List[Mapping[str,str]]:
    query_kwags = {
      'KeyConditionExpression':Key('PartitionKey').eq('Fsi::Optionable')
    }

    query = StateStore.query_table(self.instrument_table, query_kwags)
    return query
    # query = self.instrument_table.query(
    #   KeyConditionExpression=Key('PartitionKey').eq('Fsi::Optionable'))

    # return query['Items']

  #@xray_recorder.capture('StateStore::set_account')
  def set_account(self, account:dict, balances:Mapping[str,dict])->None:
    with self.transaction_table.batch_writer() as batch:
      try:
        for balance_name in set(balances.keys()):
          balance = balances[balance_name]
          if balance == None:
            continue
          
          # Record the account...
          StateStore.normalize(balance)
          balance['PartitionKey']= 'Fsi::Account'
          balance['SortKey']= 'Fsi::Account::{}::{}::{}'.format(
            account['type'],
            account['accountId'],
            balance_name).upper()
          balance['Expiration']= ceil(StateStore.expiration())
          balance['last_update']= ceil(time())
          
          # Account Level properties
          balance['accountType'] = account['type']
          balance['accountId'] = account['accountId']
          balance['isClosingOnlyRestricted']= account['isClosingOnlyRestricted']
          balance['isDayTrader'] = account['isDayTrader']

          batch.put_item(Item=balance)
      except Exception as error:
        print(str(error))
        raise error

  #@xray_recorder.capture('StateStore::add_transactions')
  def add_transactions(self, account:dict, transactions:List[Mapping[str,Any]])->None:
    with self.transaction_table.batch_writer() as batch:
      try:
        for transaction in StateStore.flatten(transactions):

          # Record the transaction...
          StateStore.normalize(transaction)
          transaction['PartitionKey']= 'Fsi::Transactions'
          transaction['SortKey']= 'Fsi::Transaction::{}::{}::{}'.format(
            account['type'],
            account['accountId'],
            transaction['transactionId']).upper()
          transaction['Expiration']= ceil(StateStore.expiration(days=365 * 5))
          transaction['last_update']= ceil(time())
          batch.put_item(Item=transaction)
      except Exception as error:
        print(str(error))
        raise error
  
  #@xray_recorder.capture('StateStore::set_optionable')
  def set_optionable(self, instruments:List[dict])->None:
    with self.instrument_table.batch_writer() as batch:
      try:
        for instrument in StateStore.flatten(instruments):
          instrument['PartitionKey']= 'Fsi::Optionable'
          instrument['SortKey']= 'Fsi::Optionable::'+str(instrument['symbol']).upper()
          instrument['Expiration']= ceil(StateStore.expiration())
          instrument['last_update']= ceil(time())
          batch.put_item(Item=instrument)
      except Exception as error:
        print(str(error))
        raise error

  def set_option_chains(self, contracts:List[dict])->None:
    with self.options_table.batch_writer() as batch:
      try:
        for contract in StateStore.flatten(contracts):
          # Persist the primary record...
          symbol = str(contract['symbol']).upper()
          contract['PartitionKey']= 'Fsi::Option::{}::{}::{}::{}'.format(
            symbol,
            contract['series'],
            contract['putCall'],
            '%.2f' % contract['strike']
          )
          contract['SortKey'] = 'dte=%04d' %contract['daysToExpiration']
          contract['Expiration']= ceil(StateStore.expiration())
          contract['last_update']= ceil(time())
          StateStore.normalize(contract)
          batch.put_item(Item=contract)

          # Add Mapping record...
          record = {}
          record['PartitionKey'] = 'Fsi::Option::{}'.format(symbol)
          record['SortKey'] = contract['PartitionKey']
          record['Expiration']= ceil(StateStore.expiration())
          record['last_update']= ceil(time())

          record['strike'] = contract['strike']
          record['delta'] = contract['delta']
          record['gamma'] = contract['gamma']
          record['vega'] = contract['vega']
          record['theta'] = contract['theta']
          record['mark'] = contract['mark']
          record['underlyingPrice'] = contract['underlyingPrice']
          record['daysToExpiration'] = contract['daysToExpiration']
          StateStore.normalize(record)
          batch.put_item(Item=record)

      except Exception as error:
        print(str(error))
        raise error


  def set_quotes(self, candles:List[dict])->None:
    with self.quotes_table.batch_writer() as batch:
      try:
        for candle in StateStore.flatten(candles):
          symbol = candle['symbol'].upper()
          candle['PartitionKey']= 'Fsi::Quotes::{}'.format(symbol)
          candle['SortKey']= 'Fsi::Quote::{}::{}'.format(
            candle['frequency_type'].upper(),
            str(candle["datetime"]))
          candle['Expiration']= ceil(StateStore.expiration())
          candle['last_update']= ceil(time())
          batch.put_item(Item=candle)
      except Exception as error:
        print(str(error))
        raise error
 
  def set_fundamentals(self, fundamentals:List[dict])->None:
    with self.instrument_table.batch_writer() as batch:
      try:
        for instrument in StateStore.flatten(fundamentals):
          instrument['PartitionKey']= 'Fsi::Fundamental'
          instrument['SortKey']= 'Fsi::Fundamental::'+str(instrument['symbol']).upper()
          instrument['Expiration']= ceil(StateStore.expiration())
          instrument['last_update']= ceil(time())
          batch.put_item(Item=instrument)
      except Exception as error:
        print(str(error))
        raise error

  def clear_progress(self, component_name:str)->None:
    print('Removing marker [{}]'.format(component_name))
    return self.set_progress(component_name, marker='')

  #@xray_recorder.capture('StateStore::set_progress')
  def set_progress(self, component_name:str, marker:Any)->None:
    print('Setting ProgressMarker[{}] => [{}]'.format(component_name, marker))
    with self.instrument_table.batch_writer() as batch:
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
        raise error

  def get_progress(self, component_name:str)->Any:
    # Fetch the component marker
    query = self.instrument_table.query(
      KeyConditionExpression=Key('PartitionKey').eq('Fsi::ProgressMarker') & Key('SortKey').eq(component_name))
    items = query['Items']
    print('Retrieved ProgressMarker[{}] with value [{}]'.format(component_name, items))

    if len(items) > 1:
      raise ValueError('Multiple markers detected')

    # Unwrap the progress marker and return-it
    if len(items) == 0:
      return None

    return items[-1]

  #@xray_recorder.capture('StateStore::declare_instruments')
  def declare_instruments(self,instruments:List[dict])->None:
    try:
      with self.instrument_table.batch_writer() as batch:
        for instrument in StateStore.flatten(instruments):
          item = self.declare_instrument(instrument)
          if item == None:
            continue

          # Write the instrument record
          batch.put_item(Item=item)

          # Update the SecurityStatus index...
          record = dict(item)
          record['PartitionKey']= 'Fsi::SecurityStatus::{}'.format(StateStore.default_value(instrument,'securityStatus','None').upper())
          record['SortKey']='Fsi::Instruments::'+str(instrument['symbol']).upper()
          record['Expiration']= ceil(StateStore.expiration(days=30))
          record['last_update']=ceil(time())
          batch.put_item(Item=record)
    except Exception as error:
      print(str(error))
      raise error

  def declare_instrument(self, instrument:dict)->Mapping[str,Mapping[str,str]]:
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
        'securityStatus': StateStore.default_value(instrument,'securityStatus','None').upper()
      }
      
    except Exception as error:
      logger.error(instrument)
      logger.error(str(error))
      raise error

  @staticmethod
  def expiration(days=1460)->int:
    dt = datetime.utcnow() + timedelta(days=days)
    return round((dt-epoch).total_seconds(),0)

  @staticmethod
  def default_value(dict:dict, key:str, default:str='None')->str:
    if not key in dict:
      return default
    if len(str(dict[key])) == 0:
      return default

    return dict[key]

  @staticmethod
  def normalize(d:dict)->dict:
    for key, value in d.items():
      if type(value) is float:
        d[key] = round(Decimal(value),4)
      elif type(value) is dict:
        d[key] = StateStore.normalize(value)
      elif type(value) is list:
        for x in value:
          if type(x) is dict:
            StateStore.normalize(x)

    return d

  @staticmethod
  def flatten(results:list)->list:
    items = []
    for item in results:
      if item == None:
        continue
      elif type(item) == list:
        items.extend(item)
      elif type(item) == dict:
        items.append(item)
      else:
        raise NotImplementedError('Unable to flatten instruments')
    return items
