import boto3

client = boto3.client('ec2')
def on_event(event, context):
  print(event)
  request_type = event['RequestType']
  if request_type == 'Create': return on_create(event)
  if request_type == 'Update': return on_update(event)
  if request_type == 'Delete': return on_delete(event)
  raise Exception("Invalid request type: %s" % request_type)

def on_create(event):
  props = event["ResourceProperties"]
  print("create new resource with props %s" % props)

  transit_gateway_id = props['TransitGatewayId']
  peer_transit_gateway_id = props['PeerTransitGatewayId']
  peer_region = props['PeerRegion']
  peer_account_id = props['PeerAccountId']

  response = client.create_transit_gateway_peering_attachment(
    TransitGatewayId=transit_gateway_id,
    PeerTransitGatewayId=peer_transit_gateway_id,
    PeerAccountId=peer_account_id,
    PeerRegion=peer_region,
    TagSpecifications=[
      {
        'ResourceType':'transit-gateway-attachment',
        'Tags':[
          {'Key':'Name','Value':'HomeNet'},          
        ]
      }
    ])

  # add your create code here...
  physical_id = response['TransitGatewayPeeringAttachment']['TransitGatewayAttachmentId']

  return { 'PhysicalResourceId': physical_id }

def on_update(event):
  physical_id = event["PhysicalResourceId"]
  props = event["ResourceProperties"]
  print("update resource %s with props %s" % (physical_id, props))
  

def on_delete(event):
  physical_id = event["PhysicalResourceId"]
  print("delete resource %s" % physical_id)
  response = client.delete_transit_gateway_peering_attachment(
    TransitGatewayAttachmentId=physical_id)

  return {
    'Data': {
        'State': response['TransitGatewayPeeringAttachment']['State']
      }
  }