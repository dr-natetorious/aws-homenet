import boto3
from os import environ
from json import dumps
from botocore.exceptions import ValidationError
from botocore.retries import bucket
from flask import request, redirect
from flask.templating import render_template
from flask.wrappers import Response
from werkzeug.wrappers import response

dynamodb = boto3.client('dynamodb')
face_table_name = environ.get('FACE_TABLE')

def init_flask_for_env():
  """
  Loads flask for lambda or local debug.
  """
  from os import environ
  if 'LOCAL_DEBUG' in environ:
    from flask import Flask
    return Flask(__name__)
  else:
    from flask_lambda import FlaskLambda
    return FlaskLambda(__name__)

app = init_flask_for_env()

@app.route('/heartbeat')
def hello_world():
  return 'Hello, World!'

@app.route('/')
def homepage():
  return render_template('index.html')

@app.route('/css/<path:path>')
def get_css(path:str):
  with open('templates/css/{}'.format(path),'r') as f:
    return Response(f.read(),mimetype='text/css')

@app.route('/identities')
def get_identities():
  response = dynamodb.query(
    TableName=face_table_name,
    Select='ALL_ATTRIBUTES',
    Limit=1000,
    ReturnConsumedCapacity='NONE',
    KeyConditionExpression="PartitionKey= :partitionKey",
    ExpressionAttributeValues={
      ":partitionKey": {'S': 'Identity'},
    })
  return {
    'Identities': [x['SortKey']['S'] for x in response['Items']]
  }

@app.route('/known-faces')
def get_known_faces():
  response = dynamodb.query(
    TableName=face_table_name,
    Select='ALL_ATTRIBUTES',
    Limit=1000,
    ReturnConsumedCapacity='NONE',
    KeyConditionExpression="PartitionKey= :partitionKey",
    ExpressionAttributeValues={
      ":partitionKey": {'S': 'KnownFaceId'},
    })

  return {
    'KnownFaces': [x['SortKey']['S'] for x in response['Items']]
  }

@app.route('/associate/<identity>/<face_id>')
def associate_faceid(identity:str, face_id:str):
  if identity == None:
    raise ValidationError('identity')
  if face_id == None:
    raise ValidationError('face_id')
  
  dynamodb.put_item(
    TableName=face_table_name,
    Item={
      'PartitionKey': {'S': 'Identity'},
      'SortKey': {'S': identity.lower()},
      'display_text': {'S': identity},
    })

  dynamodb.put_item(
    TableName=face_table_name,
    Item={
      'PartitionKey': {'S': 'Identity::'+identity.lower()},
      'SortKey': {'S': face_id.lower()},
    })

if __name__ == '__main__':
  app.run(debug=True)
