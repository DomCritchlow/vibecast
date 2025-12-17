"""Storage abstraction for uploading podcast episodes to Cloudflare R2."""

import os
import boto3
from botocore.config import Config


def get_r2_client():
    """Create and return a boto3 client configured for Cloudflare R2.
    
    Requires these environment variables:
        - R2_ACCOUNT_ID: Cloudflare account ID
        - R2_ACCESS_KEY_ID: R2 API access key
        - R2_SECRET_ACCESS_KEY: R2 API secret key
    
    Returns:
        Configured boto3 S3 client for R2.
    """
    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    
    if not all([account_id, access_key, secret_key]):
        raise ValueError(
            "Missing R2 credentials. Set R2_ACCOUNT_ID, "
            "R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY environment variables."
        )
    
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    # Configure for R2 compatibility
    config = Config(
        signature_version='s3v4',
        retries={'max_attempts': 3, 'mode': 'standard'},
    )
    
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=config,
    )
    
    return client


def upload_mp3_to_r2(
    mp3_bytes: bytes,
    filename: str,
    config: dict,
) -> str:
    """Upload MP3 file to Cloudflare R2.
    
    Args:
        mp3_bytes: Raw MP3 audio data.
        filename: Filename for the uploaded file (e.g., "2025-12-13.mp3").
        config: Full configuration dictionary.
    
    Returns:
        Public URL of the uploaded file.
    """
    storage_config = config.get("storage", {})
    r2_config = storage_config.get("r2", {})
    
    bucket = r2_config.get("bucket", "vibecast")
    key_prefix = r2_config.get("key_prefix", "episodes/")
    public_base_url = r2_config.get("public_base_url", "")
    cache_control = r2_config.get("cache_control", "public, max-age=31536000, immutable")
    
    # Build the full object key
    object_key = f"{key_prefix}{filename}"
    
    # Remove double slashes if any
    object_key = object_key.replace("//", "/")
    
    # Get R2 client
    client = get_r2_client()
    
    # Upload the file
    client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=mp3_bytes,
        ContentType="audio/mpeg",
        CacheControl=cache_control,
    )
    
    # Build public URL
    if public_base_url:
        # Use configured public URL with explicit /episodes/ path
        public_url = f"{public_base_url.rstrip('/')}/episodes/{filename}"
    else:
        # Fallback to R2.dev URL pattern (if enabled on bucket)
        account_id = os.environ.get("R2_ACCOUNT_ID", "")
        public_url = f"https://{bucket}.{account_id}.r2.dev/{object_key}"
    
    return public_url


def check_r2_connection(config: dict) -> bool:
    """Verify R2 connection and bucket access.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        True if connection successful, False otherwise.
    """
    try:
        storage_config = config.get("storage", {})
        r2_config = storage_config.get("r2", {})
        bucket = r2_config.get("bucket", "vibecast")
        
        client = get_r2_client()
        
        # Try to list objects (limited to 1) to verify access
        client.list_objects_v2(Bucket=bucket, MaxKeys=1)
        
        return True
    
    except Exception as e:
        print(f"R2 connection check failed: {e}")
        return False


def list_episodes(config: dict, max_items: int = 100) -> list[dict]:
    """List existing episodes in R2 storage.
    
    Args:
        config: Full configuration dictionary.
        max_items: Maximum number of items to return.
    
    Returns:
        List of episode objects with key, size, and last_modified.
    """
    storage_config = config.get("storage", {})
    r2_config = storage_config.get("r2", {})
    
    bucket = r2_config.get("bucket", "vibecast")
    key_prefix = r2_config.get("key_prefix", "episodes/")
    
    client = get_r2_client()
    
    response = client.list_objects_v2(
        Bucket=bucket,
        Prefix=key_prefix,
        MaxKeys=max_items,
    )
    
    episodes = []
    for obj in response.get("Contents", []):
        episodes.append({
            "key": obj["Key"],
            "size": obj["Size"],
            "last_modified": obj["LastModified"].isoformat(),
        })
    
    return episodes


def delete_episode(filename: str, config: dict) -> bool:
    """Delete an episode from R2 storage.
    
    Args:
        filename: Filename of the episode to delete.
        config: Full configuration dictionary.
    
    Returns:
        True if deletion successful.
    """
    storage_config = config.get("storage", {})
    r2_config = storage_config.get("r2", {})
    
    bucket = r2_config.get("bucket", "vibecast")
    key_prefix = r2_config.get("key_prefix", "episodes/")
    
    object_key = f"{key_prefix}{filename}".replace("//", "/")
    
    client = get_r2_client()
    
    try:
        client.delete_object(Bucket=bucket, Key=object_key)
        return True
    except Exception as e:
        print(f"Failed to delete {filename}: {e}")
        return False


def upload_transcript_to_r2(
    transcript_text: str,
    filename: str,
    config: dict,
) -> str:
    """Upload transcript text file to Cloudflare R2.
    
    Args:
        transcript_text: Transcript content as string.
        filename: Filename for the uploaded file (e.g., "2025-12-13.txt").
        config: Full configuration dictionary.
    
    Returns:
        Public URL of the uploaded transcript.
    """
    storage_config = config.get("storage", {})
    r2_config = storage_config.get("r2", {})
    
    bucket = r2_config.get("bucket", "vibecast")
    public_base_url = r2_config.get("public_base_url", "")
    
    # Store transcripts in a transcripts/ folder
    object_key = f"transcripts/{filename}"
    
    # Get R2 client
    client = get_r2_client()
    
    # Upload the file
    client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=transcript_text.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
        CacheControl="public, max-age=31536000, immutable",
    )
    
    # Build public URL
    if public_base_url:
        # Use configured public URL with explicit /transcripts/ path
        public_url = f"{public_base_url.rstrip('/')}/transcripts/{filename}"
    else:
        # Fallback
        account_id = os.environ.get("R2_ACCOUNT_ID", "")
        public_url = f"https://{bucket}.{account_id}.r2.dev/{object_key}"
    
    return public_url

