"""Storage abstraction for uploading podcast assets to Cloudflare R2.

All uploads go through a single cached client and one `upload_bytes` helper,
so key layout, cache headers, and public-URL construction live in one place.

Cache policy: episode assets are keyed by date and are occasionally
re-uploaded to fix a bad episode, so they get a 1-day cache instead of
`immutable` (which would let CDNs mask corrections forever).
"""

import functools
import json
import logging
import os

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

DEFAULT_CACHE_CONTROL = "public, max-age=86400"


@functools.lru_cache(maxsize=1)
def get_r2_client():
    """Create (once) and return a boto3 client configured for Cloudflare R2.

    Requires these environment variables:
        - R2_ACCOUNT_ID: Cloudflare account ID
        - R2_ACCESS_KEY_ID: R2 API access key
        - R2_SECRET_ACCESS_KEY: R2 API secret key
    """
    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")

    if not all([account_id, access_key, secret_key]):
        raise ValueError(
            "Missing R2 credentials. Set R2_ACCOUNT_ID, "
            "R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY environment variables."
        )

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def _r2_settings(config: dict) -> dict:
    r2_config = (config.get("storage") or {}).get("r2") or {}
    return {
        "bucket": r2_config.get("bucket", "vibecast"),
        "public_base_url": r2_config.get("public_base_url", ""),
        "cache_control": r2_config.get("cache_control", DEFAULT_CACHE_CONTROL),
        "key_prefix": r2_config.get("key_prefix", "episodes/"),
    }


def public_url_for_key(object_key: str, config: dict) -> str:
    """Build the public URL for an object key."""
    settings = _r2_settings(config)
    if settings["public_base_url"]:
        return f"{settings['public_base_url'].rstrip('/')}/{object_key}"
    # Fallback to R2.dev URL pattern (if enabled on bucket)
    account_id = os.environ.get("R2_ACCOUNT_ID", "")
    return f"https://{settings['bucket']}.{account_id}.r2.dev/{object_key}"


def upload_bytes(
    object_key: str,
    body: bytes,
    content_type: str,
    config: dict,
    cache_control: str | None = None,
    content_disposition: str | None = None,
) -> str:
    """Upload raw bytes to R2 and return the public URL."""
    settings = _r2_settings(config)
    object_key = object_key.replace("//", "/")

    extra = {}
    if content_disposition:
        extra["ContentDisposition"] = content_disposition

    get_r2_client().put_object(
        Bucket=settings["bucket"],
        Key=object_key,
        Body=body,
        ContentType=content_type,
        CacheControl=cache_control or settings["cache_control"],
        **extra,
    )

    url = public_url_for_key(object_key, config)
    logger.debug("Uploaded %s (%d bytes) -> %s", object_key, len(body), url)
    return url


def upload_mp3_to_r2(mp3_bytes: bytes, filename: str, config: dict) -> str:
    """Upload an episode MP3 (e.g. "2025-12-13.mp3") and return its public URL."""
    key_prefix = _r2_settings(config)["key_prefix"]
    return upload_bytes(f"{key_prefix}{filename}", mp3_bytes, "audio/mpeg", config)


def upload_transcript_to_r2(transcript_text: str, filename: str, config: dict) -> str:
    """Upload an episode transcript text file and return its public URL."""
    return upload_bytes(
        f"transcripts/{filename}",
        transcript_text.encode("utf-8"),
        "text/plain; charset=utf-8",
        config,
    )


def upload_artwork_to_r2(episode_id: str, image_bytes: bytes, config: dict) -> str:
    """Upload AI-generated episode artwork to episodes/{episode_id}/episode-art.png."""
    r2_prefix = (config.get("artwork") or {}).get("r2_prefix", "episodes")
    return upload_bytes(
        f"{r2_prefix}/{episode_id}/episode-art.png", image_bytes, "image/png", config
    )


def upload_artwork_metadata_to_r2(
    episode_id: str, metadata: dict, prompt: str, config: dict
) -> None:
    """Upload artwork metadata and prompt to R2 for debugging/reproducibility."""
    r2_prefix = (config.get("artwork") or {}).get("r2_prefix", "episodes")
    base = f"{r2_prefix}/{episode_id}/episode-art"
    upload_bytes(
        f"{base}.meta.json",
        json.dumps(metadata, indent=2).encode("utf-8"),
        "application/json",
        config,
    )
    upload_bytes(f"{base}.prompt.txt", prompt.encode("utf-8"), "text/plain; charset=utf-8", config)


def upload_newspaper_to_r2(episode_id: str, pdf_bytes: bytes, config: dict) -> str:
    """Upload the newspaper PDF to episodes/{episode_id}/newspaper.pdf."""
    return upload_bytes(
        f"episodes/{episode_id}/newspaper.pdf",
        pdf_bytes,
        "application/pdf",
        config,
        content_disposition='inline; filename="vibecast-newspaper.pdf"',
    )


def get_fallback_artwork_url(config: dict) -> str:
    """Public URL of the static fallback artwork used when generation fails."""
    fallback_key = (config.get("artwork") or {}).get(
        "r2_fallback_key", "static/default-episode-art.png"
    )
    return public_url_for_key(fallback_key, config)


def upload_fallback_artwork_to_r2(image_bytes: bytes, config: dict) -> str:
    """One-time upload of the static fallback artwork image."""
    fallback_key = (config.get("artwork") or {}).get(
        "r2_fallback_key", "static/default-episode-art.png"
    )
    return upload_bytes(fallback_key, image_bytes, "image/png", config)


def check_r2_connection(config: dict) -> bool:
    """Verify R2 connection and bucket access."""
    try:
        bucket = _r2_settings(config)["bucket"]
        get_r2_client().list_objects_v2(Bucket=bucket, MaxKeys=1)
        return True
    except Exception as e:
        logger.error("R2 connection check failed: %s", e)
        return False


def list_episodes(config: dict, max_items: int = 100) -> list[dict]:
    """List existing episode objects in R2 storage."""
    settings = _r2_settings(config)
    response = get_r2_client().list_objects_v2(
        Bucket=settings["bucket"],
        Prefix=settings["key_prefix"],
        MaxKeys=max_items,
    )
    return [
        {
            "key": obj["Key"],
            "size": obj["Size"],
            "last_modified": obj["LastModified"].isoformat(),
        }
        for obj in response.get("Contents", [])
    ]


def delete_episode(filename: str, config: dict) -> bool:
    """Delete an episode object from R2 storage."""
    settings = _r2_settings(config)
    object_key = f"{settings['key_prefix']}{filename}".replace("//", "/")
    try:
        get_r2_client().delete_object(Bucket=settings["bucket"], Key=object_key)
        return True
    except Exception as e:
        logger.error("Failed to delete %s: %s", filename, e)
        return False
