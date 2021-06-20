from json import dumps
from lib.instruments import InstrumentCollector
from lib.StateStore import StateStore
from lib.ClientFactory import ClientFactory
from typing import Any, Mapping

def process_notification(event:Mapping[str,Any], _):
  print(dumps(event))

  # Check this is a valid message...
  if not 'Action' in event:
    raise ValueError('Expecting Action verb in payload')

  # Route to correct handler
  action = event['Action']
  tdclient = ClientFactory.create_client(force_refresh=True)
  state_store = StateStore(table_name='FsiCoreSvc-Collector',region_name='us-east-2')
  
  if action == 'DiscoverInstruments':
    InstrumentCollector(tdclient,state_store).run(action['AssetTypes'])
  elif action == 'DiscoverOptionable':
    print('Add DiscoverOptionable code')
  elif action == 'CollectFundamentals':
    print('Add CollectFundamentals code')
  elif action == 'CollectFinalQuotes':
    print('Add CollectFinalQuotes code')
  elif action == 'CollectTransactions':
    print('Add CollectTransactions code')
  else:
    raise NotImplementedError('Add code for Action='+action)

