from os import environ
from lib.configuration import Configuration, get_value
from rtsp import Client
from PIL import Image
from io import BytesIO
from datetime import datetime
from random import random
from json import dumps
import boto3
from lib.rekclient import RekClient
from lib.bucket import S3Object

collection_id = get_value('REK_COLLECT_ID')
region_name = get_value('REGION')
analyzed_frame_topic_arn = get_value('FRAME_ANALYZED_TOPIC')
frame_size=(1920,1080)
sampling = 0.005

s3 = boto3.client('s3', region_name=region_name)
sns = boto3.client('sns',region_name=region_name)
rekclient = RekClient(region_name=region_name)

def include_sample()->bool:
  if random() < sampling:
    return True
  return False

class Producer:
  """
  Represents the RTSP Video Producer Component
  """
  @property
  def config(self)->Configuration:
    return self.__config

  def __init__(self, config:Configuration)->None:
    self.__config = config

  def invoke(self)->None:
    with Client(rtsp_server_uri=self.config.server_uri) as client:
      if not client.isOpened():
        print('rtsp server is not running.')
        return {
          'Error': 'rtsp server is offline'
        }

      #self.capture_video(client)

      image = client.read()
      while True:
        try:
          self.process_image(image)
          image = client.read()
        except Exception as e:
          print(e)
          return {
            'Error': 'rtsp server disconnected'+str(e)
          }

    return { 'Status': 'OK'}

  def process_image(self, image:Image):
    if not include_sample():
      return
    
    if image is None:
      print('No frame to write, skipping.')
      return

    array = BytesIO()
    image.save(array, format='PNG')

    dt = datetime.now()
    key = 'eufy/{}/{}.png'.format(
      self.config.camera_name,
      dt.strftime('%Y/%m/%d/%H/%M/%S.%f'))

    s3_object = S3Object(bucket=self.config.bucket_name, key=key)
    
    # Attempt to write the frame
    try:
      s3.put_object(
        Bucket=s3_object.bucket,
        Key=s3_object.key,
        Body=array.getvalue(),
        Metadata={
          'Camera':self.config.camera_name,
          'Year': str(dt.year),
          'Month': str(dt.month),
        })
      print('Wrote Frame {}: {}'.format(s3_object.s3_uri, image))
    except Exception as error:
      print('Unable to write frame: '+error)
      return

    # Analyze the frame
    try:
      labels = rekclient.detect_s3_labels(
        s3_object=s3_object)
    except Exception as error:
      print('Unable to DetectLabels in {} - {}'.format(s3_object.s3_uri, error))
      return

    # Find any faces within the document
    try:
      if labels.has_person:
        face_document = rekclient.detect_s3_faces(
          s3_object=s3_object, 
          collection_id=collection_id)

        for face in face_document.faces:
          meta = face.summarize(image)
          meta['S3_Uri'] = s3_object.s3_uri
          meta['Camera'] = self.config.camera_name

          response = sns.publish(
            TopicArn=analyzed_frame_topic_arn,
            Message=dumps(meta,indent=2,sort_keys=True),
            MessageAttributes={
              'Camera': {
                'DataType':'String',
                'StringValue':self.config.camera_name
              },
              'HasPerson': {
                'DataType':'String',
                'StringValue':'true'
              },
            })
        print(response)
    except Exception as error:
      print('Unable to DetectFaces in {} - {}'.format(s3_object.s3_uri, error))
      return


  # def capture_video(self, client:Client)->None:
  #   print('capture_video entered')
  #   fourcc = cv2.VideoWriter_fourcc(*'avc1') #(*'mp4v')
  #   out = cv2.VideoWriter('/tmp/output.mp4',fourcc,60,frame_size)

  #   frame_count=0
  #   while True:
  #     if frame_count > 1000:
  #       print('Reached max frames')
  #       break

  #     image = client.read(raw=False)
  #     if image is None:
  #       print ('No frame, skipping')
  #       continue

  #     frame_count += 1
  #     out.write(image)
  #     print(image)

  #   out.release()
  #   self.upload_video('/tmp/output.mp4')

  def upload_video(self, file:str):
    print('upload_video({})'.format(file))

    dt = datetime.now()
    key = 'video/{}/{}.mp4'.format(self.config.camera_name,dt.strftime('%Y/%m/%d/%H/%M.%S.%f'))
    bucket = boto3.resource('s3').Bucket(self.config.bucket_name)

    print('Uploading to s3://{}/{}'.format(
      self.config.bucket_name, key))

    bucket.upload_file(file,key)

