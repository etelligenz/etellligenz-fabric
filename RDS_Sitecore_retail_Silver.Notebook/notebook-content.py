# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "5f0850a1-37a9-44ac-9039-79f45f44acde",
# META       "default_lakehouse_name": "RDS_retail_LH_Sitecore_Silver",
# META       "default_lakehouse_workspace_id": "1e4482f3-5d7d-4467-a879-66ae1e48a0f1",
# META       "known_lakehouses": [
# META         {
# META           "id": "5f0850a1-37a9-44ac-9039-79f45f44acde"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Pre-create Silver Lakehouse Entity Delta Tables 
# 
# Use this notebook to create the tables for the Silver lake entities.


# CELL ********************

tables_to_delete = [  
    "Catalog",  
    "CustomerEmail",  
    "CustomerLocation",  
    "CustomerTelephoneNumber",  
    "CustomerGroup",
    "CustomerGroupCustomer",
    "IndividualCustomer",  
    "Item",  
    "Location",  
    "Order",  
    "OrderLine",  
    "OrderLineStatus",  
    "OrderStatus",  
    "ProductCategory",  
    "ProductCharacteristic",  
    "ProductCharacteristicType",  
    "RelatedProduct",  
    "RetailProduct",
    "Shipment",
]  
  
for table in tables_to_delete:  
    if spark.catalog.tableExists(table):  
        spark.sql(f"DELETE FROM {table}")  
    else:  
        print(f"Table {table} does not exist.")  

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Function Imports

# CELL ********************

from pyspark.sql.types import *
from pyspark.sql.functions import *
from delta.tables import DeltaTable

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Catalog Table

# CELL ********************

print("Creating Catalog Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Catalog") \
    .addColumn("CatalogId", dataType=StringType(), nullable=True) \
    .addColumn("CatalogName", dataType=StringType(), nullable=True) \
    .addColumn("CatalogDescription", dataType=StringType(), nullable=True) \
    .addColumn("CatalogEffectivePeriodStartDate", dataType=TimestampType(), nullable=True) \
    .addColumn("CatalogEffectivePeriodEndDate", dataType=TimestampType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Country Table

# CELL ********************

print("Creating Country Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Country") \
    .addColumn("CountryId", dataType=LongType(), nullable=True) \
    .addColumn("IsoCountryName", dataType=StringType(), nullable=True) \
    .addColumn("Iso2LetterCountryName", dataType=StringType(), nullable=True) \
    .addColumn("Iso3LetterCountryName", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

bronze_lakehouse_id = "2f8fd291-5f12-4dc2-9767-a65a5f4eaf3c"
bronze_lakehouse_directory_name = "QA_Data_Files"

isoCountrysListDf = spark.read.format("csv").option("header","true")\
    .load("abfss://1e4482f3-5d7d-4467-a879-66ae1e48a0f1@onelake.dfs.fabric.microsoft.com/{0}/Files/{1}/IsoCountryList.csv"\
    .format(bronze_lakehouse_id, bronze_lakehouse_directory_name))

isoCountrysListDf = isoCountrysListDf.withColumnRenamed("CountryId", "CountryIdString")\
    .withColumn("CountryId", col("CountryIdString").cast(LongType())).drop("CountryIdString")

isoCountrysListDf.write.format("delta").mode("overwrite").save("Tables/Country")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create CustomerEmail Table

# CELL ********************

print("Creating CustomerEmail Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/CustomerEmail") \
    .addColumn("CustomerId", dataType=StringType(), nullable=True) \
    .addColumn("EmailAddress", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create CustomerLocation Table

# CELL ********************

print("Creating CustomerLocation Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/CustomerLocation") \
    .addColumn("CustomerId", dataType=StringType(), nullable=True) \
    .addColumn("LocationId", dataType=StringType(), nullable=True) \
    .addColumn("PeriodStartTimestamp", dataType=TimestampType(), nullable=True) \
    .addColumn("PeriodEndTimestamp", dataType=TimestampType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create CustomerTelephoneNumber Table

# CELL ********************

print("Creating CustomerTelephoneNumber Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/CustomerTelephoneNumber") \
    .addColumn("CustomerId", dataType=StringType(), nullable=True) \
    .addColumn("TelephoneNumber", dataType=DecimalType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create CustomerGroup Table

# CELL ********************

print("Creating CustomerGroup Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/CustomerGroup") \
    .addColumn("CustomerGroupId", dataType=StringType(), nullable=True) \
    .addColumn("CustomerGroupName", dataType=StringType(), nullable=True) \
    .addColumn("CustomerGroupDescription", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create CustomerGroupCustomer Table

# CELL ********************

print("Creating CustomerGroupCustomer Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/CustomerGroupCustomer") \
    .addColumn("CustomerGroupId", dataType=StringType(), nullable=True) \
    .addColumn("CustomerId", dataType=StringType(), nullable=True) \
    .addColumn("PeriodStartDate", dataType=TimestampType(), nullable=True) \
    .addColumn("PeriodEndDate", dataType=TimestampType(), nullable=True) \
    .addColumn("CustomerGroupNote", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create IndividualCustomer Table

# CELL ********************

print("Creating IndividualCustomer Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/IndividualCustomer") \
    .addColumn("CustomerId", dataType=StringType(), nullable=True) \
    .addColumn("IndividualCustomerName", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Item Table

# CELL ********************

print("Creating Item Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Item") \
    .addColumn("ProductId", dataType=StringType(), nullable=True) \
    .addColumn("ItemSku", dataType=StringType(), nullable=True) \
    .addColumn("ItemName", dataType=StringType(), nullable=True) \
    .addColumn("ItemDescription", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Location Table

# CELL ********************

print("Creating Location Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Location") \
    .addColumn("LocationId", dataType=StringType(), nullable=True) \
    .addColumn("LocationAddressLine1", dataType=StringType(), nullable=True) \
    .addColumn("LocationAddressLine2", dataType=StringType(), nullable=True) \
    .addColumn("LocationCity", dataType=StringType(), nullable=True) \
    .addColumn("LocationZipCode", dataType=StringType(), nullable=True) \
    .addColumn("CountryId", dataType=LongType(), nullable=True) \
    .addColumn("LocationName", dataType=StringType(), nullable=True) \
    .addColumn("LocationDescription", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Order Table

# CELL ********************

print("Creating Order Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Order") \
    .addColumn("OrderId", dataType=StringType(), nullable=True) \
    .addColumn("CustomerId", dataType=StringType(), nullable=True) \
    .addColumn("OrderTypeId", dataType=LongType(), nullable=True) \
    .addColumn("OrderBookedDate", dataType=TimestampType(), nullable=True) \
    .addColumn("OrderTotalAmount", dataType=DecimalType(), nullable=True) \
    .addColumn("NumberOfOrderLines", dataType=IntegerType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create OrderLine Table

# CELL ********************

print("Creating OrderLine Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/OrderLine") \
    .addColumn("OrderId", dataType=StringType(), nullable=True) \
    .addColumn("OrderLineId", dataType=StringType(), nullable=True) \
    .addColumn("ProductId", dataType=StringType(), nullable=True) \
    .addColumn("ProductSalesPriceAmount", dataType=DecimalType(), nullable=True) \
    .addColumn("Quantity", dataType=DecimalType(), nullable=True) \
    .addColumn("TotalOrderLineAmount", dataType=DecimalType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create OrderLineStatus Table

# CELL ********************

print("Creating OrderLineStatus Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/OrderLineStatus") \
    .addColumn("OrderId", dataType=StringType(), nullable=True) \
    .addColumn("OrderLineId", dataType=StringType(), nullable=True) \
    .addColumn("OrderLineStatusStartTimestamp", dataType=TimestampType(), nullable=True) \
    .addColumn("OrderLineStatusEndTimestamp", dataType=TimestampType(), nullable=True) \
    .addColumn("OrderLineStatusTypeId", dataType=IntegerType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create OrderStatus Table

# CELL ********************

print("Creating OrderStatus Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/OrderStatus") \
    .addColumn("OrderId", dataType=StringType(), nullable=True) \
    .addColumn("OrderStatusStartTimestamp", dataType=TimestampType(), nullable=True) \
    .addColumn("OrderStatusEndTimestamp", dataType=TimestampType(), nullable=True) \
    .addColumn("OrderStatusTypeId", dataType=IntegerType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create OrderStatusType Table

# CELL ********************

print("Creating OrderStatusType Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/OrderStatusType") \
    .addColumn("OrderStatusTypeId", dataType=LongType(), nullable=True) \
    .addColumn("OrderStatusTypeName", dataType=StringType(), nullable=True) \
    .addColumn("OrderStatusTypeDescription", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()


print("Populating OrderStatusType Table")
status_names = ["Unsubmitted", "AwaitingApproval", "Declined", "Open" ,"Completed", "Canceled"]
status_type_id = [0, 1, 2, 3, 4, 5]

spark.createDataFrame([(type_id, name, "") for type_id, name in zip(status_type_id, status_names)],\
    ["OrderStatusTypeId", "OrderStatusTypeName", "OrderStatusTypeDescription"])\
    .write.mode("overwrite").format("delta").save('Tables/OrderStatusType')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create OrderType Table

# CELL ********************

print("Creating OrderType Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/OrderType") \
    .addColumn("OrderTypeId", dataType=LongType(), nullable=True) \
    .addColumn("OrderTypeName", dataType=StringType(), nullable=True) \
    .addColumn("OrderTypeDescription", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

print("Populating OrderType Table")
status_names = ["Online Sale"]
status_type_id = [1]

spark.createDataFrame([(type_id, name, "") for type_id, name in zip(status_type_id, status_names)],\
    ["OrderTypeId", "OrderTypeName", "OrderTypeDescription"])\
    .write.mode("overwrite").format("delta").save('Tables/OrderType')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create ProductCategory Table

# CELL ********************

print("Creating ProductCategory Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/ProductCategory") \
    .addColumn("ProductCategoryId", dataType=StringType(), nullable=True) \
    .addColumn("ProductCategoryName", dataType=StringType(), nullable=True) \
    .addColumn("ProductCategoryDescription", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create ProductCharacteristic Table

# CELL ********************

print("Creating ProductCharacteristic Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/ProductCharacteristic") \
    .addColumn("ProductId", dataType=StringType(), nullable=True) \
    .addColumn("ProductCharacteristicTypeId", dataType=StringType(), nullable=True) \
    .addColumn("ProductCharacteristic", dataType=StringType(), nullable=True) \
    .addColumn("ProductCharacteristicPeriodStartDate", dataType=TimestampType(), nullable=True) \
    .addColumn("ProductCharacteristicPeriodEndDate", dataType=TimestampType(), nullable=True) \
    .addColumn("ProductCharacteristicNote", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create ProductCharacteristicType Table

# CELL ********************

print("Creating ProductCharacteristicType Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/ProductCharacteristicType") \
    .addColumn("ProductCharacteristicTypeId", dataType=StringType(), nullable=True) \
    .addColumn("ProductCharacteristicTypeName", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create ProductRelationshipType Table

# CELL ********************

print("Creating ProductRelationshipType Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/ProductRelationshipType") \
    .addColumn("ProductRelationshipTypeId", dataType=StringType(), nullable=True) \
    .addColumn("ProductRelationshipTypeName", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

print("Populating ProductRelationshipType Table")
rel_type_id = ["variant-relationship"]
rel_type_name = ["Variant"]

spark.createDataFrame([(type_id, type_name) for type_id, type_name in zip(rel_type_id, rel_type_name)],\
    ["ProductRelationshipTypeId", "ProductRelationshipTypeName"])\
    .write.mode("overwrite").format("delta").save('Tables/ProductRelationshipType')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create RelatedProduct Table

# CELL ********************

print("Creating RelatedProduct Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/RelatedProduct") \
    .addColumn("ProductId", dataType=StringType(), nullable=True) \
    .addColumn("RelatedProductId", dataType=StringType(), nullable=True) \
    .addColumn("ProductRelationshipTypeId", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create RetailProduct Table

# CELL ********************

print("Creating RetailProduct Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/RetailProduct") \
    .addColumn("ProductId", dataType=StringType(), nullable=True) \
    .addColumn("ProductName", dataType=StringType(), nullable=True) \
    .addColumn("ProductDescription", dataType=StringType(), nullable=True) \
    .addColumn("ReturnPolicyStatement", dataType=StringType(), nullable=True) \
    .addColumn("ReturnPolicyPeriodInDays", dataType=StringType(), nullable=True) \
    .addColumn("ItemSku", dataType=StringType(), nullable=True) \
    .addColumn("CatalogId", dataType=StringType(), nullable=True) \
    .addColumn("CategoryId", dataType=StringType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Shipment Table

# CELL ********************

print("Creating Shipment Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Shipment") \
    .addColumn("ShipmentId", dataType=StringType(), nullable=True) \
    .addColumn("ShipmentOrderId", dataType=StringType(), nullable=True) \
    .addColumn("ShipmentFromLocationId", dataType=IntegerType(), nullable=True) \
    .addColumn("OriginationWarehouseId", dataType=IntegerType(), nullable=True) \
    .addColumn("ShipmentFromName", dataType=StringType(), nullable=True) \
    .addColumn("ShipmentToName", dataType=StringType(), nullable=True) \
    .addColumn("ShipmentToLocationId", dataType=IntegerType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
