from datetime import datetime
from dateutil.tz import tzutc
from os import environ, path
from typing import Any, Mapping
from json import dumps, loads
from logging import Logger
from lib.message import Message
from lib.facetable import FaceTable

# Initialize the environment
logger = Logger(name='LambdaFunction')
face_table = FaceTable(
  table_name=environ.get('TABLE_NAME'),
  region_name=environ.get('REGION'))


def process_notification(event:Mapping[str,Any],_=None):
  """
  Amazon Lambda Function entry point.
  """
  print(dumps(event))
  for record in event['Records']:
    message = Message(record)
    print('Processing Camera[{}]: FaceId [{}]'.format(
      message.camera_name,
      message.face_id))

    face_table.update(message)

def read_example_file(filename:str)->Mapping[str,Any]:
  example_dir = path.join(path.dirname(__file__),'examples')
  file = path.join(example_dir, filename)

  with open(file, 'r') as f:
    return loads(f.read())

if __name__ == '__main__':
  sns_notification = read_example_file('sns_notification.json')
  sns_notification['Records'][0]['Sns']['Timestamp'] = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
  process_notification(sns_notification)