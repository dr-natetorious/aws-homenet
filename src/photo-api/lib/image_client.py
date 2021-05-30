import boto3
from io import BytesIO
from lib.s3util import S3Object
from lib.bounding_box import BoundingBox
from PIL import Image
from PIL.ImageDraw import Draw
class ImageClient:
  def __init__(self, region_name:str) -> None:
    self.storage_client = boto3.client('s3', region_name=region_name)

  def fetch_image(self, s3_uri:str, bbox:dict):
    assert s3_uri != None, "No uri specified"
    assert s3_uri.startswith('s3://'), "Wrong schema on s3_uri"
    
    s3_obj = S3Object.from_s3_uri(uri=s3_uri)
    bbox:BoundingBox = BoundingBox(bbox)

    response = self.storage_client.get_object(
      Bucket= s3_obj.bucket,
      Key=s3_obj.key)

    body = response['Body'].read()

    if bbox.is_usable:
      bio = BytesIO(body)
      image = Image.open(bio)

      shape=[(bbox.top,bbox.left),
        (bbox.top +bbox.height, bbox.left+bbox.width)]
      drawing = Draw(image)
      drawing.rectangle(shape, outline="red")
      
      bout = BytesIO()
      image.save(bout, "PNG")
      bout.seek(0)
      return bout.read()

    return body

  