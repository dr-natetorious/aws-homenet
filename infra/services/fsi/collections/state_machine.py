import builtins
from typing import Any, Mapping
from aws_cdk.aws_logs import LogGroup, RetentionDays
from infra.services.fsi.resources import FsiSharedResources
from aws_cdk import (
  core,
  aws_lambda as lambda_,
  aws_stepfunctions as sf,
  aws_stepfunctions_tasks as sft,
  aws_logs as logs,
)

class FsiLongRunningCollectionProcess(core.Construct):
  @property
  def component_name(self)->str:
    return FsiLongRunningCollectionProcess.__name__

  @property
  def resources(self)->FsiSharedResources:
    return self.__resources

  def __init__(self, scope: core.Construct, id: builtins.str, action_name:str, resources:FsiSharedResources, function:lambda_.Function) -> None:
    super().__init__(scope, id)    
    self.__resources = resources

    # Define the state machine definition...
    invoke_function = sft.LambdaInvoke(self,'InvokeFunction',
      lambda_function=function,
      invocation_type= sft.LambdaInvocationType.REQUEST_RESPONSE,
      input_path='$.Payload',
      result_path='$.Result')

    choice = sf.Choice(self,'IsComplete',
      comment='Check if theres more to process')
    choice.when(
      sf.Condition.string_equals('$.Result.Payload.Result.RunState','RunStatus.MORE_AVAILABLE'),
      invoke_function)
    choice.when(
      sf.Condition.string_equals('$.Result.Payload.Result.RunState','RunStatus.COMPLETE'),
      sf.Pass(self,'Finalize', comment='Workflow Complete'))
    choice.otherwise(
      sf.Fail(self,'NotImplemented', cause='Unknown Choice', error='NotImplementedException'))

    definition = invoke_function.next(choice)

    # Register the definition as StateMachine...
    zone_name=self.resources.landing_zone.zone_name
    self.state_machine = sf.StateMachine(self,'StateMachine',
      state_machine_name='Fsi{}-Collection_{}'.format(zone_name, id),
      state_machine_type= sf.StateMachineType.STANDARD,
      timeout=core.Duration.hours(2),
      logs= sf.LogOptions(
        destination= logs.LogGroup(self,'LogGroup',
          removal_policy= core.RemovalPolicy.DESTROY,
          retention= RetentionDays.TWO_WEEKS,
          log_group_name='/homenet/fsi-{}/states/{}/{}'.format(zone_name, self.component_name, action_name).lower())
      ),
      tracing_enabled=True,
      definition= definition)
