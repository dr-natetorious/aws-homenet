from datetime import datetime
from lib.enums import RunStatus, SecurityStatus
from typing import Any, List
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError, NotFndError, NotNulError
from time import sleep
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore

class Collector:
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    assert tdclient != None, "No tdclient"
    assert state_store != None, "No state store"

    self.__tdclient= tdclient
    self.__state_store = state_store

  @property
  def tdclient(self)->TDClient:
    return self.__tdclient

  @property
  def state_store(self)->TDClient:
    return self.__state_store

  def run(self)->RunStatus:
    raise NotImplementedError()

  def ignore_instrument(self,instrument)->bool:
    if not 'symbol' in instrument:
      return True

    return Collector.is_garbage_symbol(instrument['symbol'])

  def get_progress_marker(self)->str:
    progress = self.state_store.get_progress(self.__class__.__name__)
    if progress != None and "marker" in progress:
      marker = progress['marker']
    else:
      marker = ''
    return marker

  def fetch_known_symbols(self)->List[dict]:
    equities = self.state_store.retrieve_equities(
      filter_status=SecurityStatus.standard_ignore_list())

    without_pinksheets = [e for e in equities if not e['exchange'] == 'Pink Sheet']
    return without_pinksheets
    

  def create_symbol_queue_from_marker(self)->RateLimitQueue:
     # Check if the progress marker exists...
    marker = self.get_progress_marker()

     # Populate the unfinished tasks list...
    queue = RateLimitQueue(calls=100, per=60, fuzz=0.5)
    ignored = []
    completed_items = []
    for instrument in self.fetch_known_symbols():
      # Check this is valid record
      symbol = StateStore.default_value(instrument,'symbol',default=None)
      if symbol == None:
        continue
      
      # Check if the derived class wants to ignore
      if self.ignore_instrument(instrument):
        ignored.append(symbol)
        continue
      
      # Check if the progress marker wants to skip
      if symbol < marker:
        completed_items.append(symbol)
        continue
      
      # All checks pass add into the job list
      queue.put(instrument)
    
    if len(ignored)>0:
      print('CreateQueue: Ignoring: {}'.format(len(ignored)))
    if len(completed_items)>0:
      print('CreateQueue: Completed Items: {}'.format(len(completed_items)))
    return queue

  @staticmethod
  def is_garbage_symbol(symbol:str)->bool:
    for ch in symbol:
      if ch.isdigit():
        return True
      elif ch == '-':
        return True
      elif ch == ' ':
        return True
    return False

  @staticmethod
  def attempt_with_retry(action, retry_count:int=3)->Any:
    """
    Perform an action and automatically retry failures.
    """
    attempts = 0
    while attempts < retry_count:
      try:
        return action()
      except ExdLmtError as throttled:
        print('Throttled Detected - Sleep additional 5 seconds')
        sleep(5)
      except NotFndError as error:
        print('Resource not found')
        return None
      except NotNulError as error:
        print('[NotNulError] This cryptic error means batch sizing too big...')
        raise error
      except Exception as error:
        print(str(error))
        attempts += 1

      print('Retry sleep {}sec'.format(attempts * attempts))
      sleep(attempts * attempts)

    # Validate the response is valid
    raise GeneralError(
      'Unable to {} within {} attempts.'.format(action, retry_count))

class QueuedCollector(Collector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  def process_instrument(self,instrument:dict)->Any:
    raise NotImplementedError()

  def persist_batch(self,batch:List[Any])->None:
    raise NotImplementedError()

  @property
  def batch_size(self)->int:
    return 25

  def choose_progress_marker_from_batch(self,instrument, batch:list)->str:
    last_item = [x for x in batch if not x == None][-1]
    if type(last_item) is list:
      last_item = last_item[-1]

    return last_item['symbol']    

  #@xray_recorder.capture('OptionableDiscovery::run')
  def run(self, max_items:int=99999)->RunStatus:
    """
    Discovers which symbols are optionable.
    """
    queue = self.create_symbol_queue_from_marker()
    if queue.unfinished_tasks == 0:
      raise ValueError('No tasks discovered; this is likely a defect.')

    # Process the queue until empty...
    responses = []
    completed = 0
    skipped = 0
    total = queue.unfinished_tasks
    while queue.qsize() >0:
      try:
        # Perform the instrument assessment...
        instrument = queue.get()
        count = queue.unfinished_tasks
        assessment = self.process_instrument(instrument)
        completed += 1
        
        # Handle scenario where more work enters the queue...
        additions = queue.unfinished_tasks - count
        total += additions

        # Determine what to do with the response..
        if assessment == None:
          skipped += 1
        elif type(assessment) == list and len(assessment) == 0:
          skipped += 1
        else:
          responses.append(assessment)
        
        # Periodically checkpoint and display progress
        if len(responses) >0 and len(responses) % self.batch_size == 0:
          self.persist_batch(responses)
          self.state_store.set_progress(
            component_name=self.__class__.__name__, 
            marker=self.choose_progress_marker_from_batch(instrument, responses))

          responses.clear()
          print('[{}] Completed {} / {} [{}%]'.format(
            datetime.now(), 
            completed, 
            total, 
            round(completed/total*100,2),
            skipped))

        # Check if we reached the run limit
        if completed >= max_items:
          return RunStatus.MORE_AVAILABLE
      except ExdLmtError as error:
        print('Error (sleep 5): '+str(error))
        sleep(5)
        queue.put(instrument)
        continue
      except Exception as error:
        print('Unhandled Error: '+str(error))
        raise error

    # Publish any remaining items in the buffer
    if len(responses) > 0:
      self.persist_batch(responses)
    self.state_store.clear_progress(self.__class__.__name__)
    return RunStatus.COMPLETE
