from json import dumps
from lib.interfaces import RunStatus
from lib.transactions import TransactionAudit
from lib.optionable import OptionableDiscovery
from os import environ
from math import floor
from lib.instruments import InstrumentDiscovery
from lib.StateStore import StateStore
from lib.ClientFactory import ClientFactory
from typing import Any, Mapping

# Configure the StateStore...
instrument_table_name = environ.get('INSTRUMENT_TABLE_NAME')
if instrument_table_name == None:
  raise ValueError('No INSTRUMENT_TABLE_NAME specified')
transaction_table_name = environ.get('TRANSACTION_TABLE_NAME')
if transaction_table_name == None:
  raise ValueError('No TRANSACTION_TABLE_NAME specified')
state_store = StateStore(
    instrument_table_name=instrument_table_name,
    transaction_table_name=transaction_table_name,
    region_name='us-east-2')

# Determine how much time we have...
def get_time_available_seconds(context):
  return floor(context.get_remaining_time_in_millis() / 1000)

is_success = {
  'Result': {
    'RunState': str(RunStatus.COMPLETE)
  }
}


# Amazon Lambda Function Entrypoint ...
def process_notification(event:Mapping[str,Any], context):
  print(dumps(event))

  # Check this is a valid message...
  if not 'Action' in event:
    raise ValueError('Expecting Action verb in payload')

  # 100 calls per minute that utilizes at most 75% time available
  max_tda_calls = floor(get_time_available_seconds(context) / 60.0 * 100.0 * 0.75)
  
  # Initialize shared arguments...
  action = event['Action']
  tdclient = ClientFactory.create_client(force_refresh=True)
  
  # Route to the correct extensions...
  if action == 'DiscoverInstruments':
    # Handle weekly instrument discovery process
    InstrumentDiscovery(tdclient,state_store).run(event['AssetTypes'])
  elif action == 'DiscoverOptionable':
    # Handle weekly optionable discovery process
    result = OptionableDiscovery(tdclient, state_store).run(max_items=max_tda_calls)
    return {
      'Result': {
        'RunState': str(result)
      }
    }
  elif action == 'CollectFundamentals':
    print('Add CollectFundamentals code')
  elif action == 'CollectFinalQuotes':
    print('Add CollectFinalQuotes code')
  elif action == 'CollectTransactions':
    # Handle Updating transactions
    lookback_days=7
    if "lookback_days" in event:
      lookback_days= int(event['lookback_days'])
    
    TransactionAudit(tdclient,state_store).run(lookback_days)
    return is_success
  else:
    raise NotImplementedError('Add code for Action='+action)

