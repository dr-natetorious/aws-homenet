from json import dumps
from lib.optionable import OptionableDiscovery
from os import environ
from lib.instruments import InstrumentDiscovery
from lib.StateStore import StateStore
from lib.ClientFactory import ClientFactory
from typing import Any, Mapping

state_table_name = environ.get('STATE_TABLE_NAME')
if state_table_name == None:
  raise ValueError('No STATE_TABLE_NAME specified')

def process_notification(event:Mapping[str,Any], _):
  print(dumps(event))

  # Check this is a valid message...
  if not 'Action' in event:
    raise ValueError('Expecting Action verb in payload')

  # Route to correct handler
  action = event['Action']
  tdclient = ClientFactory.create_client(force_refresh=True)
  state_store = StateStore(table_name=state_table_name,region_name='us-east-2')
  
  if action == 'DiscoverInstruments':
    InstrumentDiscovery(tdclient,state_store).run(event['AssetTypes'])
  elif action == 'DiscoverOptionable':
    OptionableDiscovery(tdclient, state_store).run()
  elif action == 'CollectFundamentals':
    print('Add CollectFundamentals code')
  elif action == 'CollectFinalQuotes':
    print('Add CollectFinalQuotes code')
  elif action == 'CollectTransactions':
    print('Add CollectTransactions code')
  else:
    raise NotImplementedError('Add code for Action='+action)

