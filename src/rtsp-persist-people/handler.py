from datetime import datetime
from dateutil.tz import tzutc
from os import environ, path
from typing import Any, Mapping
from dateutil.parser import isoparse
from json import dumps, loads
from logging import Logger
from lib.message import Message
from lib.series_writer import Dimension, Measurement, Record, SeriesWriter, TimeStamp, ValueType, WriteRecordsRequest, TableName

# Initialize the environment
region_name = environ.get('REGION')
logger = Logger(name='LambdaFunction')
table = TableName(
  database_name= environ.get('DATABASE_NAME'),
  table_name= environ.get('TABLE_NAME'))

# Construct the writer
writer = SeriesWriter(region_name=region_name)

def write_message(message:Message)->None:
  """
  Writes one message to Amazon Timestream
  """
  request = WriteRecordsRequest(
    table=table,
    common_attributes=Record(
      time_stamp=TimeStamp(
        value= isoparse(message.time_stamp)),
      dimensions=[
        Dimension('FaceId',message.face_id),
        Dimension('CameraName',message.camera_name),
        Dimension('BaseName',message.base_name),
      ]))

  # Add emotional responses
  for emotion in message.emotions:
    request.add_record(Record(
      measurement=Measurement(
        name=emotion.type,
        value=round(emotion.confidence,2),
        value_type= ValueType.DOUBLE)))

  # Add Age Range
  for key in message.age_range.keys():
    request.add_record(Record(
      measurement=Measurement(
        name='AgeRange'+key,
        value= round(message.age_range[key],2),
        value_type= ValueType.BIGINT)))

  # Add quality metrics
  for key in message.quality.keys():
    request.add_record(Record(
      measurement=Measurement(
        name='Quality'+key,
        value= round(message.quality[key],2),
        value_type= ValueType.DOUBLE)))

  return writer.write_records(request)

def process_notification(event:Mapping[str,Any],_=None):
  """
  Amazon Lambda Function entry point.
  """
  print(dumps(event))
  for record in event['Records']:
    message = Message(record)
    print('{} is {}'.format(
      message.face_id,
      ', '.join(message.filter_emotions())))

    write_message(message)

def read_example_file(filename:str)->Mapping[str,Any]:
  example_dir = path.join(path.dirname(__file__),'examples')
  file = path.join(example_dir, filename)

  with open(file, 'r') as f:
    return loads(f.read())

if __name__ == '__main__':
  sns_notification = read_example_file('sns_notification.json')
  sns_notification['Records'][0]['Sns']['Timestamp'] = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
  process_notification(sns_notification)