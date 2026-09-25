import os

from app.aws.clients import export_credentials
from app.config import Settings


def test_env_keys_reach_boto3_but_never_override_the_environment(monkeypatch):
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_BEARER_TOKEN_BEDROCK"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "from-shell")
    settings = Settings(_env_file=None, aws_access_key_id="from-dotenv",
                        aws_secret_access_key="from-dotenv", aws_bearer_token_bedrock="")
    export_credentials(settings)
    assert os.environ["AWS_ACCESS_KEY_ID"] == "from-dotenv"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "from-shell"
    assert "AWS_BEARER_TOKEN_BEDROCK" not in os.environ   # blank -> IAM role on EC2
    assert "from-dotenv" not in repr(settings)
