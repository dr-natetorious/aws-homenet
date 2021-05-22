from infra.interfaces import ILandingZone
from aws_cdk import (
  core,
  aws_codeartifact as art,
  aws_route53 as r53,
  aws_codepipeline as pipe,
  aws_codepipeline_actions as actions,
)

class RtspConnectorPipeline(core.Construct):
  """
  Represents a code artifact repository.
  """
  def __init__(self, scope: core.Construct, id: str, landing_zone:ILandingZone, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.pipeline = pipe.Pipeline(self,'Pipeline',
      pipeline_name='{}-Rtsp-Connector'.format(landing_zone.zone_name))

    github_init_artifact = pipe.Artifact(artifact_name='github-init-artifact')

    self.pipeline.add_stage(
      stage_name='Build-Commit',
      actions=[
        actions.GitHubSourceAction(
          action_name='Init-from-GitHub',
          owner='dr-natetorious',
          repo='aws-homenet',
          # Note: The secret must be:
          #  1. formated non-json using the literal value from github.com/settings/tokens
          #     e.g., 1837422b*****26d31c
          #  2. referencing a token that includes scopes notifications, repo, workflow
          oauth_token=core.SecretValue.secrets_manager('GithubAccessToken'),
          output=github_init_artifact
        )]
    )

    self.build_stage = self.pipeline.add_stage(stage_name='Build')
