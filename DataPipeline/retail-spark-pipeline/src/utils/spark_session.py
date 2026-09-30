"""Reusable, S3A-configured SparkSession factory.

IMPORTANT: The Hadoop AWS connector + AWS SDK versions below must be
compatible with the installed Spark/Hadoop build (see README "Spark S3A
configuration" section). Override via environment variables if your Spark
distribution ships a different Hadoop version.

This project's pinned PySpark (4.x) bundles Hadoop client 3.5.0, which
requires org.apache.hadoop:hadoop-aws:3.5.0. Hadoop 3.4+ moved hadoop-aws to
the AWS SDK v2 "bundle" artifact (software.amazon.awssdk:bundle) instead of
the older v1 com.amazonaws:aws-java-sdk-bundle used by Hadoop 3.3.x. If your
Spark ships an older Hadoop (3.3.x), set HADOOP_AWS_VERSION=3.3.4 and
AWS_JAVA_SDK_GROUP/AWS_JAVA_SDK_ARTIFACT/AWS_JAVA_SDK_VERSION to the v1
coordinates (com.amazonaws / aws-java-sdk-bundle / 1.12.262).
"""

import os
import sys

from pyspark.sql import SparkSession

from src.config.config import Settings

# On Windows, Spark's Python workers shell out to bare "python"/"python3" on
# PATH unless told otherwise, which can hit the Microsoft Store alias stub
# instead of the real interpreter. Pin both to the interpreter running this
# process so driver and worker always match.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

# Defaults matched to Hadoop 3.5.x (AWS SDK v2 "bundle" artifact).
_DEFAULT_HADOOP_AWS_VERSION = "3.5.0"
_DEFAULT_AWS_SDK_GROUP = "software.amazon.awssdk"
_DEFAULT_AWS_SDK_ARTIFACT = "bundle"
_DEFAULT_AWS_SDK_VERSION = "2.29.52"


def build_spark_session(settings: Settings) -> SparkSession:
    """Create (or fetch) a SparkSession configured for S3A access.

    Credentials are resolved through the AWS SDK v2 DefaultCredentialsProvider
    chain (env vars -> system properties -> ~/.aws/credentials profile ->
    web identity token -> EC2/ECS/EKS instance role) -- no secret is ever
    read or set here directly. Override AWS_CREDENTIALS_PROVIDER if your
    Hadoop-AWS build needs a different provider classname.
    """
    hadoop_aws_version = os.getenv("HADOOP_AWS_VERSION", _DEFAULT_HADOOP_AWS_VERSION)
    aws_sdk_group = os.getenv("AWS_JAVA_SDK_GROUP", _DEFAULT_AWS_SDK_GROUP)
    aws_sdk_artifact = os.getenv("AWS_JAVA_SDK_ARTIFACT", _DEFAULT_AWS_SDK_ARTIFACT)
    aws_sdk_version = os.getenv("AWS_JAVA_SDK_VERSION", _DEFAULT_AWS_SDK_VERSION)
    credentials_provider = os.getenv(
        "AWS_CREDENTIALS_PROVIDER", "software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider"
    )

    builder = (
        SparkSession.builder.appName(settings.spark_app_name)
        .config(
            "spark.jars.packages",
            f"org.apache.hadoop:hadoop-aws:{hadoop_aws_version},"
            f"{aws_sdk_group}:{aws_sdk_artifact}:{aws_sdk_version}",
        )
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", credentials_provider)
        .config("spark.hadoop.fs.s3a.endpoint.region", settings.aws_region)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", str(settings.spark_shuffle_partitions))
        # createDataFrame(list[dict]) otherwise infers nested dicts (e.g. the
        # sales "items" list) as MapType<string,string> instead of a proper
        # struct, which breaks "item.*" expansion in Silver's transform_sales.
        .config("spark.sql.pyspark.inferNestedDictAsStruct.enabled", "true")
        # Dynamic partition overwrite lets reruns replace only the touched
        # tenant_id/date partitions instead of the whole dataset.
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
    )

    # AWS_PROFILE, if set, is picked up automatically by S3A's default
    # credential provider chain -- nothing to configure explicitly here.

    return builder.getOrCreate()

