from lib.bounding_box import BoundingBox
from typing import Any, List, Mapping
from lib.image_client import ImageClient
import boto3
from os import environ
from flask import  redirect
from flask.helpers import make_response
from flask.templating import render_template
from flask.wrappers import Response
from lib.face_table_client import FaceTableClient

# Initialize the clients...
face_table_client = FaceTableClient(
  face_table_name=environ.get('FACE_TABLE'),
  region_name= environ.get('REGION'))

image_client = ImageClient(
  region_name= environ.get('REGION'))

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
def default_page():
  return redirect('/-/home')

@app.route('/-/home')
def homepage():
  return render_template('index.html')

@app.route('/-/identities')
def identities_page():
  return render_template('identities.html')

@app.route('/-/faces')
def faces_page():
  faces = get_known_faces()
  return render_template('faces.html', faces=faces['KnownFaces'])

@app.route('/-/face/preview/<faceid>')
def get_face_preview(faceid:str):
  images:List[Mapping[str,Any]] = face_table_client.get_face_images(faceid)['Images']
  best_image = images[-1]

  content = image_client.fetch_image(best_image['s3_uri'])
  bbox = BoundingBox(best_image['bounding_box'])
  if bbox.is_usable:
    content = image_client.cut_bounding_box(content, bbox)
    content = image_client.resize_image(content,(64,64))
  else:
    content = image_client.resize_image(content,(64,64))

  response = make_response(content.read())
  response.headers.set('Content-Type', 'image/png')
  return response

  # with open('templates/pict.png','rb')  as f:
  #   image = f.read()
  #   response = make_response(image)
  #   response.headers.set('Content-Type', 'image/png')
  #   return response

@app.route('/css/<path:path>')
def get_css(path:str):
  with open('templates/css/{}'.format(path),'r') as f:
    return Response(f.read(),mimetype='text/css')

@app.route('/identities')
def get_identities():
  return face_table_client.get_identities()

@app.route('/known-faces')
def get_known_faces():
  return face_table_client.get_known_faces()

@app.route('/identity-face/<identity>/<face_id>')
def associate_faceid(identity:str, face_id:str):
  return face_table_client.identify_faceid(identity,face_id)

@app.route('/face-images/<face_id>')
def get_face_images(face_id:str):
  return face_table_client.get_face_images(face_id)

if __name__ == '__main__':
  app.run(debug=True)
