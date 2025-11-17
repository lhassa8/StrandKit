"""
AWS Client wrapper for StrandKit.

This module provides a thin wrapper around boto3 that handles:
- AWS credential management (profiles, regions)
- Session caching
- Consistent error handling
- Client creation for various AWS services

The AWSClient class is designed to be simple and predictable,
making it easy for AI coding assistants to generate correct usage.
"""

from typing import Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class AWSClient:
    """
    AWS Client wrapper that manages boto3 sessions and service clients.

    This class provides a centralized way to create AWS service clients
    with consistent credential handling and error management.

    Attributes:
        profile: AWS profile name (uses default if None)
        region: AWS region (uses profile default if None)
        session: Cached boto3 Session object

    Example:
        >>> client = AWSClient(profile="dev", region="us-east-1")
        >>> logs_client = client.get_client("logs")
        >>> response = logs_client.describe_log_groups()
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        region: Optional[str] = None,
        session: Optional[boto3.Session] = None
    ):
        """
        Initialize AWS client wrapper.

        Args:
            profile: AWS CLI profile name. If None, uses default profile.
            region: AWS region name. If None, uses profile's default region.
            session: Optional pre-configured boto3 Session. If provided,
                    profile and region are ignored.

        Raises:
            NoCredentialsError: If AWS credentials cannot be found.
        """
        if session is not None:
            self.session = session
            self.profile = session.profile_name
            self.region = session.region_name
        else:
            # Create session with optional profile and region
            self.profile = profile
            self.region = region
            self.session = boto3.Session(
                profile_name=profile,
                region_name=region
            )

        # Validate that we have credentials by attempting to get them
        try:
            credentials = self.session.get_credentials()
            if credentials is None:
                raise NoCredentialsError()
        except Exception as e:
            raise NoCredentialsError() from e

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """
        Pydantic v2 schema generator for AWSClient.

        This tells Pydantic/Strands to treat AWSClient as optional and not serialize it.
        Agents don't create AWSClient objects - they're for library users only.
        """
        from pydantic_core import core_schema

        # Return a schema that accepts None and creates a default AWSClient
        return core_schema.no_info_after_validator_function(
            lambda x: None if x is None else x,
            core_schema.nullable_schema(core_schema.any_schema())
        )

    def get_client(self, service_name: str) -> Any:
        """
        Get a boto3 client for the specified AWS service.

        Args:
            service_name: Name of AWS service (e.g., "logs", "cloudformation", "iam")

        Returns:
            boto3 service client

        Raises:
            ClientError: If client creation fails

        Example:
            >>> client = AWSClient(region="us-west-2")
            >>> logs = client.get_client("logs")
            >>> groups = logs.describe_log_groups()
        """
        return self.session.client(service_name)

    def get_resource(self, service_name: str) -> Any:
        """
        Get a boto3 resource for the specified AWS service.

        Args:
            service_name: Name of AWS service (e.g., "s3", "dynamodb")

        Returns:
            boto3 service resource

        Raises:
            ClientError: If resource creation fails
        """
        return self.session.resource(service_name)
