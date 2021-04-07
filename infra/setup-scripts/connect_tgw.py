import boto3
from time import sleep

account_id='581361757134'
regions = ['us-east-1','eu-west-1','ap-northeast-1','us-west-2','ca-central-1']

def create_request(owner:str, peer:str):
  ssm_o = boto3.client('ssm', region_name=owner)
  ssm_p = boto3.client('ssm', region_name=peer)

  # Attempt to find the previous run
  try:
    existing_attachment_id = ssm_o.get_parameter(
      Name= '/homenet/{}/transit-gateway/{}/attachment-id'.format(owner,peer),
      WithDecryption=True)

    return existing_attachment_id['Parameter']['Value']
  except:
    print('No previous attachment found')

  transit_gateway_id = ssm_o.get_parameter(
    Name= '/homenet/{}/transit-gateway/gateway-id'.format(owner),
    WithDecryption=True)

  peer_gateway_id = ssm_p.get_parameter(
    Name= '/homenet/{}/transit-gateway/gateway-id'.format(peer),
    WithDecryption=True)

  ec2 = boto3.client('ec2', region_name=owner)
  response = ec2.create_transit_gateway_peering_attachment(
    TransitGatewayId=transit_gateway_id['Parameter']['Value'],
    PeerTransitGatewayId=peer_gateway_id['Parameter']['Value'],
    PeerAccountId=account_id,
    PeerRegion=peer)

  attachment_id = response['TransitGatewayPeeringAttachment']['TransitGatewayAttachmentId']
  ssm_o.put_parameter(
    Name= '/homenet/{}/transit-gateway/{}/attachment-id'.format(owner,peer),
    Type='String',
    Value= attachment_id)

  return attachment_id

def wait_attachment(owner:str, attachment_id:str):
  ec2 = boto3.client('ec2', region_name=owner)
  while True:
    response = ec2.describe_transit_gateway_peering_attachments(
      TransitGatewayAttachmentIds=[attachment_id],
      MaxResults=5)

    state = response['TransitGatewayPeeringAttachments'][-1]['State']
    print('Current State: '+state)
    if state in ('pendingAcceptance','available'):
      return
    elif state in ('rollingBack','failed','rejected','rejecting','failing'):
      raise ValueError(state)
    
    sleep(5)

def accept_request(peer, attachment_id):
  ec2 = boto3.client('ec2', region_name=peer)
  response = ec2.accept_transit_gateway_peering_attachment(
    TransitGatewayAttachmentId=attachment_id)

  print('{} _> AttachmentId _> {}: {}'.format(peer, attachment_id, response['TransitGatewayPeeringAttachment']['State']))

def connect_everything():
  for owner in regions:
    for peer in regions:
      if owner >= peer:
        continue
      
      try:
        attachment_id = create_request(owner,peer)
        wait_attachment(owner, attachment_id)
        accept_request(peer, attachment_id)
      except:
        print("Unable to connect {} to {}".format(owner,peer))

if __name__ == '__main__':
  connect_everything()