# aws-homenet

Deploy my home-network as hybrid cloud environment.

## How do I deploy this code

Invoking `ship-it.bat` will build the deployment system and execute the [cdk automation](https://docs.aws.amazon.com/cdk/api/latest/python/index.html).

## How do I add more components

1. In [images/cdk-deploy/ship-it.sh](ship-it.sh) invoke your stack
2. Add your definition to [NetworkApp](app.py) to construct it
