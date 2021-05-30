from typing import Tuple
import boto3
from io import BytesIO
from lib.s3util import S3Object
from lib.bounding_box import BoundingBox
from PIL import Image
from PIL.ImageDraw import Draw
class ImageClient:
  def __init__(self, region_name:str) -> None:
    self.storage_client = boto3.client('s3', region_name=region_name)

  def fetch_image(self, s3_uri:str) -> BytesIO:
    assert s3_uri != None, "No uri specified"
    assert s3_uri.startswith('s3://'), "Wrong schema on s3_uri"
    
    s3_obj = S3Object.from_s3_uri(uri=s3_uri)

    response = self.storage_client.get_object(
      Bucket= s3_obj.bucket,
      Key=s3_obj.key)

    body = response['Body'].read()
    return BytesIO(body)

  def draw_bounding_box(self,bio:BytesIO, bbox:BoundingBox)->BytesIO:
    if not bbox.is_usable:
      return (bio, False)

    image = Image.open(bio)
    #shape=[(bbox.left,bbox.top),
    #  (bbox.left +bbox.width, bbox.top+bbox.height)]
    drawing = Draw(image)
    drawing.rectangle(bbox.shape, outline="red")
    
    bout = BytesIO()
    image.save(bout, "PNG")
    bout.seek(0)
    return bout

  def cut_bounding_box(self,bio:BytesIO, bbox:BoundingBox)->BytesIO:
    image = Image.open(bio)
    left, top = bbox.shape[0]
    right,bottom = bbox.shape[1]
    
    cropped = image.crop((left,top,right,bottom))
    
    bout = BytesIO()
    cropped.save(bout, "PNG")
    bout.seek(0)
    return bout

  def resize_image(self, bio:BytesIO, size:Tuple[int,int])->BytesIO:
    image = Image.open(bio)
    resized = image.resize(size=size)

    bout = BytesIO()
    resized.save(bout, "PNG")
    bout.seek(0)
    return bout

  