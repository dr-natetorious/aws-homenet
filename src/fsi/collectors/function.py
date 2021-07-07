from json import dumps
from lib.point_in_time.options import OptionsCollection
from lib.quotes import QuoteCollection
from lib.point_in_time.fundamentals import FundamentalCollection
from lib.interfaces import RunStatus
from lib.transactions import TransactionAudit
from lib.discovery.optionable import OptionableDiscovery
from os import environ
from math import floor
from lib.discovery.instruments import InstrumentDiscovery
from lib.StateStore import StateStore
from lib.ClientFactory import ClientFactory
from typing import Any, Mapping

# Configure the StateStore...
state_store = StateStore(
    instrument_table_name=environ.get('INSTRUMENT_TABLE_NAME'),
    transaction_table_name=environ.get('TRANSACTION_TABLE_NAME'),
    quotes_table_name=environ.get('QUOTES_TABLE_NAME'),
    options_table_name=environ.get('OPTIONS_TABLE_NAME'),
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
    extension = lambda: InstrumentDiscovery(tdclient,state_store).run(max_items=max_tda_calls)    
  elif action == 'DiscoverOptionable':
    extension = lambda: OptionableDiscovery(tdclient, state_store).run(max_items=max_tda_calls)
  elif action == 'CollectFundamentals':
    extension = lambda: FundamentalCollection(tdclient, state_store).run(max_items=max_tda_calls)    
  elif action == 'CollectQuotes':
    candle_config = StateStore.default_value(event,'CandleConfiguration', None)
    extension= lambda: QuoteCollection(tdclient, state_store, candle_config).run(max_items=max_tda_calls)
  elif action == 'CollectOptions':
    extension= lambda: OptionsCollection(tdclient, state_store).run(max_items=max_tda_calls)
  elif action == 'CollectTransactions':
    lookback_days=7
    if "lookback_days" in event:
      lookback_days= int(event['lookback_days'])
    extension = lambda: TransactionAudit(tdclient,state_store).run(lookback_days)    
  else:
    raise NotImplementedError('Add code for Action='+action)

  # Finally, execute the extension... 
  result = extension()
  return {
      'Result': {
        'RunState': str(result)
      }
    }
