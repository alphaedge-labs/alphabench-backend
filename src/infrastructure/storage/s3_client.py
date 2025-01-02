import boto3
from botocore.exceptions import ClientError
from typing import Optional
import os

from src.config.settings import settings
from src.utils.metrics import (
    S3_OPERATION_COUNT,
    S3_OPERATION_DURATION,
    track_time
)

class S3Client:
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    @track_time(S3_OPERATION_DURATION.labels(operation='upload'))
    async def upload_file_content(
        self,
        key: str,
        content: str,
        content_type: str = "text/plain"
    ) -> bool:
        """Upload string content to S3"""
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType=content_type
            )
            S3_OPERATION_COUNT.labels(
                operation='upload',
                status='success'
            ).inc()
            return True
        except ClientError as e:
            # Log error here
            S3_OPERATION_COUNT.labels(
                operation='upload',
                status='error'
            ).inc()
            raise Exception(f"Failed to upload to S3: {str(e)}")

    async def upload_file(self, file_path: str, key: str) -> bool:
        """Upload file to S3"""
        try:
            self.client.upload_file(
                file_path,
                self.bucket_name,
                key
            )
            return True
        except ClientError as e:
            # Log error here
            raise Exception(f"Failed to upload to S3: {str(e)}")

    async def download_file(self, key: str, local_path: str) -> bool:
        """Download file from S3"""
        try:
            self.client.download_file(
                self.bucket_name,
                key,
                local_path
            )
            return True
        except ClientError as e:
            # Log error here
            raise Exception(f"Failed to download from S3: {str(e)}")

    def get_file_url(self, key: str) -> str:
        """Get S3 file URL"""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=3600  # URL expires in 1 hour
            )
            return url
        except ClientError as e:
            # Log error here
            raise Exception(f"Failed to generate URL: {str(e)}")

    async def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            # Log error here
            raise Exception(f"Failed to delete from S3: {str(e)}")
