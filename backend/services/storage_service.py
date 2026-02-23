"""
DigitalOcean Spaces storage service.

Provides S3-compatible object storage for task completion photos
and other file uploads.
"""

import logging
import uuid
from datetime import datetime
from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Storage service for DigitalOcean Spaces (S3-compatible).

    Handles photo uploads for task completion verification.
    Falls back to local storage if DO Spaces is not configured.
    """

    def __init__(self):
        """Initialize storage service with DO Spaces credentials."""
        self.enabled = settings.do_spaces_enabled
        self.bucket = settings.do_spaces_bucket
        self.region = settings.do_spaces_region
        self.endpoint = settings.do_spaces_endpoint

        if self.enabled:
            self.client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                region_name=self.region,
                aws_access_key_id=settings.do_spaces_key,
                aws_secret_access_key=settings.do_spaces_secret,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "virtual"},
                ),
            )
            logger.info(
                f"StorageService initialized with DO Spaces: {self.bucket} ({self.region})"
            )
        else:
            self.client = None
            logger.warning(
                "StorageService: DO Spaces not configured, using mock storage"
            )

    def _generate_key(self, task_id: str, filename: str) -> str:
        """Generate a unique S3 key for a file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        ext = filename.split(".")[-1] if "." in filename else "jpg"
        return f"tasks/{task_id}/{timestamp}_{unique_id}.{ext}"

    def _get_public_url(self, key: str) -> str:
        """Get the public URL for an uploaded file."""
        # DO Spaces CDN URL format
        return f"https://{self.bucket}.{self.region}.cdn.digitaloceanspaces.com/{key}"

    async def upload_photo(
        self,
        file_data: bytes | BinaryIO,
        task_id: str,
        filename: str,
        content_type: str = "image/jpeg",
    ) -> str | None:
        """
        Upload a photo to storage.

        Args:
            file_data: File content as bytes or file-like object
            task_id: Task ID for organizing photos
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            Public URL of uploaded file, or None if upload failed
        """
        key = self._generate_key(task_id, filename)

        if not self.enabled:
            # Mock mode - return a fake URL
            mock_url = f"https://mock-storage.local/tasks/{task_id}/{filename}"
            logger.info(f"Mock upload: {mock_url}")
            return mock_url

        try:
            # Convert bytes to BytesIO if needed
            if isinstance(file_data, bytes):
                file_data = BytesIO(file_data)

            self.client.upload_fileobj(
                file_data,
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ACL": "public-read",  # Make files publicly accessible
                },
            )

            url = self._get_public_url(key)
            logger.info(f"Photo uploaded: {url}")
            return url

        except ClientError as e:
            logger.error(f"Error uploading photo: {e}")
            return None

    async def delete_photo(self, url: str) -> bool:
        """
        Delete a photo from storage.

        Args:
            url: Public URL of the file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"Mock delete: {url}")
            return True

        # Extract key from URL
        cdn_prefix = f"https://{self.bucket}.{self.region}.cdn.digitaloceanspaces.com/"
        if not url.startswith(cdn_prefix):
            logger.error(f"Invalid URL format: {url}")
            return False

        key = url[len(cdn_prefix) :]

        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Photo deleted: {key}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting photo: {e}")
            return False

    async def list_task_photos(self, task_id: str) -> list[str]:
        """
        List all photos for a task.

        Args:
            task_id: Task ID to list photos for

        Returns:
            List of public URLs
        """
        if not self.enabled:
            return []

        prefix = f"tasks/{task_id}/"

        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
            )

            urls = []
            for obj in response.get("Contents", []):
                urls.append(self._get_public_url(obj["Key"]))

            logger.info(f"Found {len(urls)} photos for task {task_id}")
            return urls

        except ClientError as e:
            logger.error(f"Error listing photos: {e}")
            return []

    def ensure_bucket_exists(self) -> bool:
        """
        Ensure the storage bucket exists.

        Creates the bucket if it doesn't exist.

        Returns:
            True if bucket exists or was created, False on error
        """
        if not self.enabled:
            return True

        try:
            # Check if bucket exists
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"Bucket {self.bucket} exists")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                # Bucket doesn't exist, create it
                try:
                    self.client.create_bucket(
                        Bucket=self.bucket,
                        CreateBucketConfiguration={
                            "LocationConstraint": self.region,
                        },
                    )
                    logger.info(f"Created bucket: {self.bucket}")
                    return True
                except ClientError as create_error:
                    logger.error(f"Error creating bucket: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False


# Default instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get or create the default storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
