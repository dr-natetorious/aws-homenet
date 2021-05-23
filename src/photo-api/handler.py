import boto3
from os import environ
from json import dumps
from botocore.exceptions import ValidationError
from botocore.retries import bucket
from flask import request, redirect

dynamodb = boto3.client('dynamodb')
table_name = environ.get('TABLE_NAME')

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

@app.route('/associate/<identity>/<face_id>')
def associate_faceid(identity:str, face_id:str):
  if identity == None:
    raise ValidationError('identity')
  if face_id == None:
    raise ValidationError('face_id')
  
  dynamodb.put_item(
    TableName=table_name,
    Item={
      'PartitionKey': {'S': 'Identity'},
      'SortKey': {'S': identity},
      'FaceId': {'S': face_id},
    })

if __name__ == '__main__':
  app.run(debug=True)
