from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_directoryservice as ad,
    aws_eks as eks,
    aws_logs as logs,
    aws_directoryservice as mad,
)

class VpnSubnet(core.Construct):
  """
  Configure the networking layer
  """
  def __init__(self, scope: core.Construct, id: str, vpc:ec2.IVpc, directory:mad.CfnMicrosoftAD, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    log_group = logs.LogGroup(self,'LogGroup',
      log_group_name='/homenet/vpn',
      removal_policy= core.RemovalPolicy.DESTROY,
      retention= logs.RetentionDays.ONE_MONTH)

    log_stream = logs.LogStream(self,'LogStream',
      log_group= log_group,
      log_stream_name='vpn-connection-logs')

    security_group = ec2.SecurityGroup(self,'SecurityGroup',
      vpc = vpc,
      allow_all_outbound=True,
      description='VPN clients')

    endpoint = ec2.CfnClientVpnEndpoint(self,'VpnEp',
      vpc_id=vpc.vpc_id,
      vpn_port=443,
      self_service_portal='enabled',
      split_tunnel=True,
      client_cidr_block='10.1.8.0/22',
      server_certificate_arn='arn:aws:acm:us-east-1:581361757134:certificate/14e094b5-fd1d-4031-b0cc-4be1b77e5955',
      description='HomeNet vpc:endpoint',
      security_group_ids=[security_group.security_group_id],
      authentication_options= [
        ec2.CfnClientVpnEndpoint.ClientAuthenticationRequestProperty(
          type='directory-service-authentication',
          active_directory=ec2.CfnClientVpnEndpoint.DirectoryServiceAuthenticationRequestProperty(
            directory_id= directory.ref)),
      ],
      connection_log_options= 
        ec2.CfnClientVpnEndpoint.ConnectionLogOptionsProperty(
          enabled=True,
          cloudwatch_log_group= log_group.log_group_name,
          cloudwatch_log_stream= log_stream.log_stream_name))

    count=0
    for net in vpc.select_subnets(subnet_group_name='Vpn-Clients').subnets:
      count += 1
      ec2.CfnClientVpnTargetNetworkAssociation(self,'Network-'+str(count),
        client_vpn_endpoint_id=endpoint.ref,
        subnet_id= net.subnet_id)
        
    # ec2.CfnClientVpnTargetNetworkAssociation(self,'NetworkAssociation',
    #   client_vpn_endpoint_id=endpoint.ref,
    #   subnet_id= 'subnet-07f0e80d0ed1c1a27')

    ec2.CfnClientVpnAuthorizationRule(self,'ClientAuthorization',
      authorize_all_groups=True,
      target_network_cidr='10.0.0.0/8',
      client_vpn_endpoint_id= endpoint.ref,
      description='Allow everyone/everywhere')