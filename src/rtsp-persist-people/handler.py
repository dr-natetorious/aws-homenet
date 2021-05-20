import boto3
from json import dumps, loads
from lib.message import Message

def process_notification(event,context):
  print(dumps(event))

  for record in event['Records']:
    message = Message(loads(record['Sns']['Message']))
    print('{} is {}'.format(
      message.face_id,
      ', '.join(message.filter_emotions())))