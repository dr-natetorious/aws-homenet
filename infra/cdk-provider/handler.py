import boto3
from time import sleep
import cfnresponse
from json import dumps

client = boto3.client('ec2')

def peer_tgw_handler(event, context):
  print(dumps(event))

  transit_gateway_id = event['TransitGatewayId']
  peer_transit_gateway_id = event['PeerTransitGatewayId']
  peer_region = event['PeerRegion']
  peer_account_id = event['PeerAccountId']

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

  attachment_id = response['TransitGatewayPeeringAttachment']['TransitGatewayAttachmentId']
  state = response['TransitGatewayPeeringAttachment']['State']

  physical_id = 'Attachment_{}-{}'.format(transit_gateway_id,peer_transit_gateway_id)
  cfnresponse.send(event,context, cfnresponse.SUCCESS, {'Data':{'attachment_id':attachment_id, 'state':state}}, physical_id)
  

if __name__ == "__main__":
  payload = {
    "TransitGatewayId": "tgw-0ad92284053bbacec",
    "PeerTransitGatewayId": "tgw-061db1bf1af1f1964",
    "PeerRegion": "eu-west-1",
    "PeerAccountId":"581361757134"
  }

  peer_tgw_handler(payload,'lambda')