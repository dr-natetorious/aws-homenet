from typing import List
from os import path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from aws_cdk.aws_route53 import IHostedZone
from cryptography import x509
from cryptography.x509 import NameAttribute, NameOID
from infra.interfaces import IVpcLandingZone
from aws_cdk import (
  core,
  aws_ec2 as ec2,
  aws_directoryservice as ad,
  aws_acmpca as ca,
  aws_ssm as ssm,
  aws_certificatemanager as cm,
)

cert_path = path.join(path.dirname(__file__), '../../../certs')

class JoinDomainConstruct(core.Construct):
  @property
  def mad(self)->ad.CfnMicrosoftAD:
    return self.__mad

  def __init__(self, scope: core.Construct, id: str, mad:ad.CfnMicrosoftAD, targets:List[str], **kwargs) -> None:
    super().__init__(scope, id, **kwargs)  
    self.__mad = mad

    document_name='Join_HomeNet_Domain_'+self.mad.ref
    self.domain_join_document = ssm.CfnDocument(self,'JoinDomainDocument',
      name= document_name,
      content={
        "schemaVersion": "1.0",
        "description": "Domain Join {}".format(self.mad.ref),
        "runtimeConfig": {
          "aws:domainJoin": {
            "properties": {
              "directoryId": self.mad.ref,
              "directoryName": "virtual.world",
              "dnsIpAddresses": self.mad.attr_dns_ip_addresses
            }
          }
        }
      })

    self.association = ssm.CfnAssociation(self,'JoinTagAssociation',
      association_name='joindomain_by_tags_'+self.mad.ref,
      name= document_name,
      targets= [
        ssm.CfnAssociation.TargetProperty(
          key='tag:domain',
          values= targets)
      ])

    self.domain_join_document.add_depends_on(mad)
    self.association.add_depends_on(self.domain_join_document)

class DirectoryServicesConstruct(core.Construct):
  """
  Represents the Directory and Certification Services
  """
  def __init__(self, scope: core.Construct, id: str, landing_zone:IVpcLandingZone, subnet_group_name:str='Default', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add('Owner',DirectoryServicesConstruct.__name__)
    vpc = landing_zone.vpc

    self.admin = 'admin'
    self.password = 'I-l1K3-74(oz'
    self.mad = ad.CfnMicrosoftAD(self,'ActiveDirectory',
      name='virtual.world',
      password=self.password,
      short_name='virtualworld',
      enable_sso=False,
      edition= 'Enterprise',
      vpc_settings= ad.CfnMicrosoftAD.VpcSettingsProperty(
        vpc_id= vpc.vpc_id,
        subnet_ids= vpc.select_subnets(subnet_group_name=subnet_group_name).subnet_ids
      ))

    JoinDomainConstruct(self,'JoinDomain', mad=self.mad, targets=[self.mad.name, self.mad.short_name])

class CertificateAuthority(core.Construct):
  def __init__(self, scope: core.Construct, id: str, common_name:str='cert.virtual.world', **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    core.Tags.of(self).add('Owner',DirectoryServicesConstruct.__name__)

    self.cert_auth = ca.CfnCertificateAuthority(self,'CertAuth',
      key_algorithm='RSA_2048',
      signing_algorithm='SHA256WITHRSA',
      type='ROOT',
      subject=ca.CfnCertificateAuthority.SubjectProperty(
        common_name=common_name,
        country='US',
        state='NJ',
        organization='HomeNet',
        locality='virtual.world'))

  def create_certificate(self, domain_name:str)->ca.CfnCertificate:
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    filename= path.join('certs',domain_name+'.csr')
    if not path.exists(filename):
      csr = (x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain_name)]))
        .sign(key, hashes.SHA256(), default_backend())
      )
      with open(filename, 'w+') as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM).decode())
    
    with open(filename, 'r') as f:
      csr = f.read()

    certificate = ca.CfnCertificate(self,domain_name,
      certificate_authority_arn= self.cert_auth.ref,
      signing_algorithm='SHA256WITHRSA',
      certificate_signing_request=csr,
      validity= ca.CfnCertificate.ValidityProperty(
        type='YEARS',
        value=1))

    return certificate
