from lib.image_prep import ImagePrep
import requests
import boto3
from os import environ, path
from typing import Any, Mapping
from json import dumps, loads
from logging import Logger

# Initialize the environment
logger = Logger(name='LambdaFunction')
def process_notification(event:Mapping[str,Any],_=None):
  print(event)

  object_get_context = event["getObjectContext"]
  request_route = object_get_context["outputRoute"]
  request_token = object_get_context["outputToken"]
  s3_url = object_get_context["inputS3Url"]

  # Get object from S3
  response = requests.get(s3_url)
  
  # Transform object
  normalizer = ImagePrep(response.content)
  
  # Write object back to S3 Object Lambda
  s3 = boto3.client('s3')
  s3.write_get_object_response(
      Body=normalizer.response_body,
      RequestRoute=request_route,
      RequestToken=request_token)

  return {'status_code': 200}

def read_example_file(filename:str)->Mapping[str,Any]:
  example_dir = path.join(path.dirname(__file__),'examples')
  file = path.join(example_dir, filename)

  with open(file, 'r') as f:
    return loads(f.read())

if __name__ == '__main__':
  sns_notification = read_example_file('sns_notification.json')
  process_notification(sns_notification)