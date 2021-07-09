from json import dumps
from typing import Mapping, Any

def rotate_secret(event:Mapping[str,Any], context):
  print(dumps(event))
