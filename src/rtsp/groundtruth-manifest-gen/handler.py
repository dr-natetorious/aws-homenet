from lib.parser import ManifestParser
from os import environ, path
from typing import Any, Mapping
from json import dumps, loads
from logging import Logger

# Initialize the environment
logger = Logger(name='LambdaFunction')
MAX_CLUSTERING_DEPTH = 8 
SMART_SAMPLING_RATE = 0.01

def create_manifest_parser(record:dict)->ManifestParser:
  region_name = record['awsRegion']
  bucket_name = record['s3']['bucket']['name']
  object_key = record['s3']['object']['key']
  return ManifestParser(bucket_name, object_key, region_name)

def process_notification(event:Mapping[str,Any],_=None):
  """
  Amazon Lambda Function entry point.
  """
  print(dumps(event))
  references = []
  for record in event['Records']:
    parser = create_manifest_parser(record)
    for file in parser.files:
      references.extend(parser.fetch_file(file))

    # Write the inventory reports...
    inventory_report_name = parser.get_inventory_report_name()
    parser.write_sourceref_file(references, 
      object_key='groundtruth/{}-full.json'.format(inventory_report_name))

    parser.write_sourceref_file(
      object_key='groundtruth/{}-sample.json'.format(inventory_report_name),
      references= parser.smart_sample(references, 
        MAX_CLUSTERING_DEPTH,
        SMART_SAMPLING_RATE))

def read_example_file(filename:str)->Mapping[str,Any]:
  example_dir = path.join(path.dirname(__file__),'examples')
  file = path.join(example_dir, filename)

  with open(file, 'r') as f:
    return loads(f.read())

if __name__ == '__main__':
  sns_notification = read_example_file('sns_notification.json')
  process_notification(sns_notification)