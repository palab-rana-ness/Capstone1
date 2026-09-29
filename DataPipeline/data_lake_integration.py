"""
Data Lake Ingestion Examples

This module contains example code for ingesting data from the Retail Mock API
into a data lake using PySpark.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


class RetailAPIClient:
    """Client for interacting with Retail Mock API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", tenant_id: str = "tenant_001"):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.headers = {"X-Tenant-ID": tenant_id}
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request."""
        url = f"{self.base_url}/api/v1{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def extract_all_pages(self, endpoint: str, page_size: int = 1000, 
                         updated_since: Optional[str] = None) -> List[Dict]:
        """Extract all pages of data from an endpoint."""
        all_data = []
        offset = 0
        
        while True:
            params = {
                "limit": page_size,
                "offset": offset
            }
            if updated_since:
                params["updated_since"] = updated_since
            
            response = self._make_request(endpoint, params=params)
            data = response.get("data", [])
            all_data.extend(data)
            
            has_more = response.get("pagination", {}).get("has_more", False)
            if not has_more:
                break
            
            offset += page_size
        
        return all_data
    
    def get_products(self, updated_since: Optional[str] = None) -> List[Dict]:
        """Get all products."""
        return self.extract_all_pages("/products", updated_since=updated_since)
    
    def get_suppliers(self, updated_since: Optional[str] = None) -> List[Dict]:
        """Get all suppliers."""
        return self.extract_all_pages("/suppliers", updated_since=updated_since)
    
    def get_sales_orders(self, updated_since: Optional[str] = None) -> List[Dict]:
        """Get all sales orders."""
        return self.extract_all_pages("/sales/orders", updated_since=updated_since)
    
    def get_inventory(self, updated_since: Optional[str] = None) -> List[Dict]:
        """Get all inventory."""
        return self.extract_all_pages("/inventory", updated_since=updated_since)
    
    def get_promotions(self, updated_since: Optional[str] = None) -> List[Dict]:
        """Get all promotions."""
        return self.extract_all_pages("/promotions", updated_since=updated_since)


# ============================================================================
# PySpark Integration Examples
# ============================================================================

def ingest_products_to_data_lake(spark, tenant_id: str = "tenant_001", 
                                output_path: str = "s3://data-lake/bronze/products"):
    """
    Extract products from API and load into Bronze layer.
    
    Args:
        spark: Spark Session
        tenant_id: Tenant identifier
        output_path: S3 or local path to write Parquet
    """
    # Initialize API client
    client = RetailAPIClient(tenant_id=tenant_id)
    
    # Extract data
    print(f"Extracting products for {tenant_id}...")
    products = client.get_products()
    print(f"Extracted {len(products)} products")
    
    # Create DataFrame
    df = spark.createDataFrame(products)
    
    # Show sample
    print("Sample data:")
    df.show(5, truncate=False)
    
    # Write to Bronze layer
    df.write.mode("overwrite").parquet(output_path)
    print(f"Loaded {len(products)} products to {output_path}")
    
    return df


def ingest_suppliers_to_data_lake(spark, tenant_id: str = "tenant_001",
                                 output_path: str = "s3://data-lake/bronze/suppliers"):
    """Extract suppliers from API and load into Bronze layer."""
    client = RetailAPIClient(tenant_id=tenant_id)
    
    print(f"Extracting suppliers for {tenant_id}...")
    suppliers = client.get_suppliers()
    print(f"Extracted {len(suppliers)} suppliers")
    
    df = spark.createDataFrame(suppliers)
    df.write.mode("overwrite").parquet(output_path)
    print(f"Loaded {len(suppliers)} suppliers to {output_path}")
    
    return df


def ingest_sales_orders_to_data_lake(spark, tenant_id: str = "tenant_001",
                                    output_path: str = "s3://data-lake/bronze/sales_orders"):
    """Extract sales orders from API and load into Bronze layer."""
    client = RetailAPIClient(tenant_id=tenant_id)
    
    print(f"Extracting sales orders for {tenant_id}...")
    orders = client.get_sales_orders()
    print(f"Extracted {len(orders)} sales orders")
    
    df = spark.createDataFrame(orders)
    df.write.mode("overwrite").parquet(output_path)
    print(f"Loaded {len(orders)} sales orders to {output_path}")
    
    return df


def ingest_inventory_to_data_lake(spark, tenant_id: str = "tenant_001",
                                 output_path: str = "s3://data-lake/bronze/inventory"):
    """Extract inventory from API and load into Bronze layer."""
    client = RetailAPIClient(tenant_id=tenant_id)
    
    print(f"Extracting inventory for {tenant_id}...")
    inventory = client.get_inventory()
    print(f"Extracted {len(inventory)} inventory records")
    
    df = spark.createDataFrame(inventory)
    df.write.mode("overwrite").parquet(output_path)
    print(f"Loaded {len(inventory)} inventory records to {output_path}")
    
    return df


def ingest_promotions_to_data_lake(spark, tenant_id: str = "tenant_001",
                                  output_path: str = "s3://data-lake/bronze/promotions"):
    """Extract promotions from API and load into Bronze layer."""
    client = RetailAPIClient(tenant_id=tenant_id)
    
    print(f"Extracting promotions for {tenant_id}...")
    promotions = client.get_promotions()
    print(f"Extracted {len(promotions)} promotions")
    
    df = spark.createDataFrame(promotions)
    df.write.mode("overwrite").parquet(output_path)
    print(f"Loaded {len(promotions)} promotions to {output_path}")
    
    return df


def ingest_all_entities(spark, tenant_id: str = "tenant_001",
                       base_output_path: str = "s3://data-lake/bronze"):
    """Ingest all retail entities to Bronze layer."""
    
    entities = [
        ("products", lambda: ingest_products_to_data_lake(spark, tenant_id, f"{base_output_path}/products")),
        ("suppliers", lambda: ingest_suppliers_to_data_lake(spark, tenant_id, f"{base_output_path}/suppliers")),
        ("sales_orders", lambda: ingest_sales_orders_to_data_lake(spark, tenant_id, f"{base_output_path}/sales_orders")),
        ("inventory", lambda: ingest_inventory_to_data_lake(spark, tenant_id, f"{base_output_path}/inventory")),
        ("promotions", lambda: ingest_promotions_to_data_lake(spark, tenant_id, f"{base_output_path}/promotions")),
    ]
    
    results = {}
    for entity_name, ingest_func in entities:
        try:
            print(f"\n{'='*60}")
            print(f"Ingesting {entity_name}...")
            print(f"{'='*60}")
            df = ingest_func()
            results[entity_name] = {
                "status": "success",
                "record_count": df.count()
            }
        except Exception as e:
            print(f"ERROR ingesting {entity_name}: {str(e)}")
            results[entity_name] = {
                "status": "failed",
                "error": str(e)
            }
    
    return results


def perform_incremental_ingestion(spark, tenant_id: str = "tenant_001",
                                 watermark_file: str = ".watermark",
                                 base_output_path: str = "s3://data-lake/bronze"):
    """
    Perform incremental ingestion using CDC pattern.
    
    Args:
        spark: Spark Session
        tenant_id: Tenant identifier
        watermark_file: File to store last extraction timestamp
        base_output_path: Base output path for data lake
    """
    
    # Read previous watermark
    try:
        with open(watermark_file, "r") as f:
            last_extraction = f.read().strip()
        print(f"Last extraction: {last_extraction}")
    except FileNotFoundError:
        # First run - get data from 7 days ago
        last_extraction = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
        print(f"First run - extracting from: {last_extraction}")
    
    client = RetailAPIClient(tenant_id=tenant_id)
    
    # Extract incremental data for each entity
    entities = {
        "products": "/products",
        "suppliers": "/suppliers",
        "sales_orders": "/sales/orders",
        "inventory": "/inventory",
        "promotions": "/promotions"
    }
    
    for entity_name, endpoint in entities.items():
        print(f"\nIngesting {entity_name}...")
        
        try:
            # Extract changed data
            data = client.extract_all_pages(endpoint, updated_since=last_extraction)
            print(f"  Extracted {len(data)} changed records")
            
            if data:
                # Create DataFrame
                df = spark.createDataFrame(data)
                
                # Write to Bronze (append mode for delta tables, overwrite for Parquet)
                output_path = f"{base_output_path}/{entity_name}"
                df.write.mode("append").parquet(output_path)
                print(f"  ✓ Wrote to {output_path}")
            else:
                print(f"  No changes for {entity_name}")
        
        except Exception as e:
            print(f"  ERROR: {str(e)}")
    
    # Update watermark
    new_watermark = datetime.utcnow().isoformat() + "Z"
    with open(watermark_file, "w") as f:
        f.write(new_watermark)
    print(f"\nWatermark updated: {new_watermark}")


# ============================================================================
# Silver Layer Transformation Examples
# ============================================================================

def transform_products_to_silver(spark, input_path: str = "s3://data-lake/bronze/products",
                                output_path: str = "s3://data-lake/silver/products"):
    """Transform products from Bronze to Silver layer."""
    
    # Read Bronze data
    df = spark.read.parquet(input_path)
    
    # Select relevant columns and apply business logic
    silver_df = df.select(
        "product_id",
        "tenant_id",
        "sku",
        "product_name",
        "category_name",
        "brand",
        "supplier_id",
        "unit_price",
        "cost_price",
        "tax_rate",
        "status",
        "created_at",
        "updated_at"
    ).filter("status = 'ACTIVE'")  # Only active products
    
    # Write to Silver layer
    silver_df.write.mode("overwrite").parquet(output_path)
    print(f"Transformed products to Silver layer: {output_path}")
    
    return silver_df


def transform_sales_to_silver(spark, input_path: str = "s3://data-lake/bronze/sales_orders",
                             output_path: str = "s3://data-lake/silver/sales_orders"):
    """Transform sales orders from Bronze to Silver layer."""
    
    df = spark.read.parquet(input_path)
    
    # Apply transformations
    silver_df = df.select(
        "order_id",
        "tenant_id",
        "customer_id",
        "store_id",
        "order_date",
        "order_status",
        "payment_method",
        "total_amount",
        "discount_amount",
        "tax_amount",
        "net_amount"
    ).filter("order_status != 'CANCELLED'")  # Exclude cancelled orders
    
    silver_df.write.mode("overwrite").parquet(output_path)
    print(f"Transformed sales to Silver layer: {output_path}")
    
    return silver_df


# ============================================================================
# Gold Layer Aggregation Examples
# ============================================================================

def create_product_summary_gold_layer(spark, 
                                     input_path: str = "s3://data-lake/silver/products",
                                     output_path: str = "s3://data-lake/gold/product_summary"):
    """Create product summary in Gold layer."""
    
    df = spark.read.parquet(input_path)
    
    # Aggregate by category
    summary = df.groupBy("category_name").agg({
        "product_id": "count",
        "unit_price": "avg",
        "cost_price": "sum"
    }).withColumnRenamed("count(product_id)", "product_count") \
     .withColumnRenamed("avg(unit_price)", "avg_price") \
     .withColumnRenamed("sum(cost_price)", "total_cost")
    
    summary.write.mode("overwrite").parquet(output_path)
    print(f"Created product summary in Gold layer: {output_path}")
    
    return summary


def create_sales_summary_gold_layer(spark,
                                   input_path: str = "s3://data-lake/silver/sales_orders",
                                   output_path: str = "s3://data-lake/gold/sales_summary"):
    """Create sales summary in Gold layer."""
    
    df = spark.read.parquet(input_path)
    
    # Aggregate by store and date
    summary = df.groupBy("store_id").agg({
        "order_id": "count",
        "total_amount": "sum",
        "net_amount": "sum"
    }).withColumnRenamed("count(order_id)", "total_orders") \
     .withColumnRenamed("sum(total_amount)", "total_revenue") \
     .withColumnRenamed("sum(net_amount)", "net_revenue")
    
    summary.write.mode("overwrite").parquet(output_path)
    print(f"Created sales summary in Gold layer: {output_path}")
    
    return summary


# ============================================================================
# Main Example Workflow
# ============================================================================

def main():
    """Main ETL workflow."""
    from pyspark.sql import SparkSession
    
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("RetailDataLakeETL") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    tenant_id = "tenant_001"
    
    print("="*70)
    print("RETAIL DATA LAKE ETL WORKFLOW")
    print("="*70)
    
    # Bronze Layer - Extract all raw data
    print("\n1. BRONZE LAYER - Ingesting raw data from APIs...")
    print("-"*70)
    ingest_all_entities(spark, tenant_id)
    
    # Silver Layer - Transform and clean
    print("\n2. SILVER LAYER - Transforming data...")
    print("-"*70)
    transform_products_to_silver(spark)
    transform_sales_to_silver(spark)
    
    # Gold Layer - Aggregate for analytics
    print("\n3. GOLD LAYER - Creating aggregations...")
    print("-"*70)
    create_product_summary_gold_layer(spark)
    create_sales_summary_gold_layer(spark)
    
    print("\n" + "="*70)
    print("ETL WORKFLOW COMPLETE!")
    print("="*70)
    
    spark.stop()


if __name__ == "__main__":
    # To run:
    # python data_lake_integration.py
    
    # Example usage:
    from pyspark.sql import SparkSession
    
    spark = SparkSession.builder.appName("RetailDataLake").getOrCreate()
    
    # Full workflow
    # main()
    
    # Or incremental ingestion
    # perform_incremental_ingestion(spark)
    
    print("Ready for data lake ingestion!")
