from function import lambda_handler


if __name__ == '__main__':
  function = lambda_handler(
    event={
      'Step': 'createSecret',
      'SecretId':'arn:aws:secretsmanager:us-east-2:581361757134:secret:HomeNet-CoreSvc-Ameritrade-Secrets-okJ0H3',
      'ClientRequestToken':'6c160f55-3074-442b-b51b-fc2c0cd667f1'
    },
    context={}
  )