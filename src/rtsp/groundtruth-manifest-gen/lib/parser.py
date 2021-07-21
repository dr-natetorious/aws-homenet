import boto3
import gzip
from math import floor
from random import randint
from typing import Any, List, Mapping
from json import dumps, loads

class SourceRef:
  def __init__(self, csv_line) -> None:
    cells = [cell.strip('"') for cell in csv_line.split(',', maxsplit=2)]
    self.bucket_name = cells[0]
    self.object_key = cells[1]

  def to_dict(self)->dict:
    return {
      'source-ref': 's3://{}/{}'.format(
        self.bucket_name,
        self.object_key
      )}

class ManifestParser:
  def __init__(self, bucket_name:str, object_key:str, region_name:str) -> None:
    assert bucket_name != None, "No bucket_name"
    assert object_key != None, "No object_key"
    assert region_name != None, "No region_name"

    self.__bucket_name = bucket_name
    self.__manifest_object_key = object_key
    self.storage_client = boto3.client('s3', region_name=region_name)
    self.manifest_json = self.__fetch_manifest(object_key=object_key)

  @property
  def bucket_name(self)->str:
    return self.__bucket_name

  @property
  def manifest_object_key(self)->str:
    return self.__manifest_object_key

  @property
  def files(self)->List[str]:
    return [x['key'] for x in self.manifest_json['files']]

  def __fetch_manifest(self, object_key)->Mapping[str,Any]:
    response:dict = self.storage_client.get_object(
      Bucket=self.bucket_name,
      Key=object_key)

    contents = response['Body'].read()
    return loads(contents)

  def fetch_file(self, object_key)->List[SourceRef]:
    response = self.storage_client.get_object(
      Bucket=self.bucket_name,
      Key=object_key)

    csv_content = gzip.decompress(response['Body'].read())
    csv_content = csv_content.decode().splitlines()
    references = []
    for line in csv_content:
      references.append(SourceRef(line))

    return references

  def write_sourceref_file(self,references:List[SourceRef], object_key:str)->None:
    """
    Creates the Amazon SageMaker GrouthTruth Manifests.
    """
    assert references != None, "No references"
    assert len(references) != 0, "Empty reference list"

    # Encode for GroundTruth
    body = []
    for ref in references:
      body.append(str(ref.to_dict()).replace("'",'"'))
    body = '\n'.join(body)

    # Write the object...
    #inventory_report = ManifestParser.get_inventory_report_name()
    response = self.storage_client.put_object(
      Bucket = self.bucket_name,
      Key = object_key, #'groundtruth/{}.json'.format(inventory_report),
      Body=body.encode()
    )
    print(dumps(response))

  def smart_sample(self,references:List[SourceRef], depth:int=8, keep_percent:float=0.01)->List[SourceRef]:
    # Cluster the references using a simple prefixing scheme
    clusters:Mapping[str,List[SourceRef]] = {}
    for ref in references:
      c_id = '/'.join(ref.object_key.split('/')[0:depth])
      if not c_id in clusters:
        clusters[c_id] = [ref]
      else:
        clusters[c_id].append(ref)

    # Choose samples from the buckets
    samples = []
    cluster_keys = list(clusters.keys())
    for _ in range(0, floor(len(references)* keep_percent)):
      c_id = cluster_keys[ randint(0,len(cluster_keys)-1) ]
      s_id = randint(0, len(clusters[c_id])-1)
      samples.append(clusters[c_id][s_id])
    return list(set(samples))


  def get_inventory_report_name(self, object_key:str=None)->str:
    if object_key is None:
      object_key = self.manifest_object_key

    for part in object_key.split('/'):
      if 'InventoryReport' in part:
        return part
    raise ValueError('Unable to determine InventoryReportName')
