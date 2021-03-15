from infra.datalake import DataLakeLayer
#from infra.compute import ComputeLayer
#from infra.sonarqube import SonarQubeLayer
#from infra.search import ElasticSearchLayer
def create_layers(scope):
  
  storage = DataLakeLayer(scope,'DataLake')
  #compute = ComputeLayer(scope,'Compute',datalake=storage)
  #search = ElasticSearchLayer(scope,'Elastic',datalake=storage)
  #sonar = SonarQubeLayer(scope,'SonarQube', datalake=storage)

  return [
    storage,
    #compute,
   # search,
    #sonar
  ]