# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "2f8fd291-5f12-4dc2-9767-a65a5f4eaf3c",
# META       "default_lakehouse_name": "RDS_retail_LH_Sitecore_Bronze",
# META       "default_lakehouse_workspace_id": "1e4482f3-5d7d-4467-a879-66ae1e48a0f1",
# META       "known_lakehouses": [
# META         {
# META           "id": "2f8fd291-5f12-4dc2-9767-a65a5f4eaf3c"
# META         },
# META         {
# META           "id": "5f0850a1-37a9-44ac-9039-79f45f44acde"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Data Mapping
# 
# Use this notebook to process the data mapping for the bronze to the silver data lake

# MARKDOWN ********************

# ## Notebook Parameters

# CELL ********************

silver_lakehouse_name = "RDS_retail_LH_Sitecore_Silver"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Module Imports

# CELL ********************

from pyspark.sql.functions import *
from pyspark.sql import Window
from datetime import datetime, timezone
from itertools import product

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Reusable Functions & Variables

# CELL ********************

# Retrieve last processed versions from the CDF State table
currentVersionStateDF = spark.read.format("delta").table("ChangeDataFeedState")
display(currentVersionStateDF)

# Responsible for updating the CDF table for each table mapped below
def UpdateChangeDataFeedTable(latest_max_commit_version, table_name):
    print("Updating Change Data Feed Table")
    current_timestamp = datetime.now(timezone.utc)

    spark.createDataFrame([(latest_max_commit_version, current_timestamp, table_name)],\
        ["last_processed_commit_version", "last_processed_timestamp", "table_name"])\
        .write.mode("append").format("delta").save('Tables/ChangeDataFeedState')

# Responsible for getting the last processed and latest committed versions of data from the respective entity tables
# Here we get all of the current and latest processed commit versions per entity we're mapping.
# We also check if there has been a new version of data committed since the latest version we've processed. 
def GetLastProcessedDataVersion(entityName):
    fullHistoryDf = spark.sql("DESCRIBE HISTORY {0}".format(entityName))
    lastProcessedEntityVersion = currentVersionStateDF.where(currentVersionStateDF.table_name == entityName)\
        .select(max("last_processed_commit_version")).collect()[0][0]
    # maintain state table + 1 to get next version of data to process
    nextVersionToProcess = lastProcessedEntityVersion + 1
    # the latest commit version of data available in the table
    latestMaxCommitVersion = fullHistoryDf.select(max("version")).collect()[0][0]
    return (nextVersionToProcess, latestMaxCommitVersion)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## AddressAssignment Data Mapping
# 
# Here we are mapping the data from the Addresses table in the Bronze lake to the Location table in the silver lake. 

# CELL ********************

nextVersionStateAddressAssignments, latestMaxCommitVersionAddressAssignments = GetLastProcessedDataVersion("AddressAssignments")

# check if new data exists since last notebook processing
if (nextVersionStateAddressAssignments <= latestMaxCommitVersionAddressAssignments):
    print("New upload of 'AddressAssignments' event data is available for processing...")
    fullAddressAssignmentsDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateAddressAssignments) \
        .table("AddressAssignments")\
        .filter(col("Response.Body.Errors").isNull())\
        .withColumn("ExternalAddressID", when(col("Request.Body.AddressID").isNull(), \
            expr("'SC-' || RouteParams.addressID")).otherwise(expr("'SC-' || Request.Body.AddressID")))\
        .withColumn("ExternalUserID", when(col("Request.Body.UserID").isNull(), expr("'SC-' || QueryParams.userID"))\
        .otherwise(expr("'SC-' || Request.Body.UserID"))).select("ExternalAddressID", "ExternalUserID",\
        to_timestamp(col("Date")).alias("PeriodStartTimestamp"), "Verb",\
        "EventProcessedUtcTime", "_commit_version", "_change_type")\
        .withColumn("PeriodEndTimestamp", lit("2999-11-16T13:06:46.713+00:00"))

    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("ExternalUserID")
    latestSnapshotAddressAssignments = fullAddressAssignmentsDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["ExternalUserID"])
    
    insertedAddressAssignmentsDf = latestSnapshotAddressAssignments.filter(col("Verb") != "DELETE")
    insertedAddressAssignmentsDf.createOrReplaceTempView("latestSnapshotAddressAssignmentsView")
    
    # Select and sink Location Rows
    merge_address_assignment_sql = """
    MERGE INTO {0}.CustomerLocation
    USING latestSnapshotAddressAssignmentsView ON 
        {0}.CustomerLocation.CustomerId = latestSnapshotAddressAssignmentsView.ExternalUserID
    WHEN MATCHED THEN UPDATE SET
        LocationId = latestSnapshotAddressAssignmentsView.ExternalAddressID,
        PeriodStartTimestamp = latestSnapshotAddressAssignmentsView.PeriodStartTimestamp,
        PeriodEndTimestamp = latestSnapshotAddressAssignmentsView.PeriodEndTimestamp
    WHEN NOT MATCHED THEN INSERT (CustomerId, LocationId, PeriodStartTimestamp, PeriodEndTimestamp)
    VALUES (
        latestSnapshotAddressAssignmentsView.ExternalUserID,
        latestSnapshotAddressAssignmentsView.ExternalAddressID,
        latestSnapshotAddressAssignmentsView.PeriodStartTimestamp,
        latestSnapshotAddressAssignmentsView.PeriodEndTimestamp
        )
    """.format(silver_lakehouse_name)    
    spark.sql(merge_address_assignment_sql)

    # Delete Rows  
    deletedAddressAssignmentsDf = latestSnapshotAddressAssignments.where(col("Verb") == "DELETE")
    deletedAddressAssignmentsDf.createOrReplaceTempView("deletedAddressAssignmentsView")

    delete_address_assignment_sql = """
    MERGE INTO {0}.CustomerLocation
    USING deletedAddressAssignmentsView ON 
        {0}.CustomerLocation.CustomerId = deletedAddressAssignmentsView.ExternalUserID
    WHEN MATCHED THEN DELETE
    """.format(silver_lakehouse_name)
    spark.sql(delete_address_assignment_sql)
    
    UpdateChangeDataFeedTable(latestMaxCommitVersionAddressAssignments, "AddressAssignments")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotAddressAssignmentsView")
    spark.catalog.dropTempView("deletedAddressAssignmentsView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Addresses Data Mapping
# 
# Here we are mapping the data from the Addresses table in the Bronze lake to the Location table in the silver lake. 

# CELL ********************

nextVersionStateAddresses, latestMaxCommitVersionAddresses = GetLastProcessedDataVersion("Addresses")

# check if new data exists since last notebook processing
if (nextVersionStateAddresses <= latestMaxCommitVersionAddresses):
    print("New upload of 'Addresses' event data is available for processing...")
    fullAddressesDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateAddresses) \
        .table("Addresses") \
        .withColumn("ExternalLocationID", when(col("Response.Body.ID").isNull(), expr("'SC-' || RouteParams.addressID"))\
        .otherwise(expr("'SC-' || Response.Body.ID"))).select("ExternalLocationID", col("Response.Body.Street1"), \
        col("Response.Body.Street2"), col("Response.Body.City"), col("Response.Body.Zip"), col("Response.Body.Country"), \
        col("Response.Body.FirstName"), col("Response.Body.LastName"), "Verb", "EventProcessedUtcTime", "_commit_version", "_change_type")

    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("ExternalLocationID")
    latestSnapshotAddresses = fullAddressesDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["ExternalLocationID"])
    
    insertedAddressesDf = latestSnapshotAddresses.filter(col("Verb") != "DELETE")

    # Get the country IDs for the 2-char country string from OrderCloud
    fullCountryDf = spark.read.format("delta").table("{0}.Country".format(silver_lakehouse_name))
    insertedAddressesDf = insertedAddressesDf.join(fullCountryDf, \
        (upper(insertedAddressesDf.Country) == fullCountryDf.Iso2LetterCountryName) | (upper(insertedAddressesDf.Country) == fullCountryDf.Iso3LetterCountryName), "left")

    insertedAddressesDf.createOrReplaceTempView("latestSnapshotAddresses")

    # Select and sink Location Rows
    merge_address_sql = """
    MERGE INTO {0}.Location
    USING latestSnapshotAddresses ON {0}.Location.LocationId = latestSnapshotAddresses.ExternalLocationID
    WHEN MATCHED THEN UPDATE SET
        LocationAddressLine1 = latestSnapshotAddresses.Street1,
        LocationAddressLine2 = latestSnapshotAddresses.Street2,
        LocationCity = latestSnapshotAddresses.City,
        LocationZipCode = latestSnapshotAddresses.Zip,
        CountryId = latestSnapshotAddresses.CountryId,
        LocationName = latestSnapshotAddresses.FirstName,
        LocationDescription = latestSnapshotAddresses.LastName
    WHEN NOT MATCHED THEN INSERT (LocationId, LocationAddressLine1, LocationAddressLine2, LocationCity, LocationZipCode, CountryId, LocationName, LocationDescription)
    VALUES (
        latestSnapshotAddresses.ExternalLocationId,
        latestSnapshotAddresses.Street1,
        latestSnapshotAddresses.Street2,
        latestSnapshotAddresses.City,
        latestSnapshotAddresses.Zip,
        latestSnapshotAddresses.CountryId, 
        latestSnapshotAddresses.FirstName,
        latestSnapshotAddresses.LastName
    )
    """.format(silver_lakehouse_name)
    spark.sql(merge_address_sql)

    # Delete Rows  
    deletedAddressesDf = latestSnapshotAddresses.where(col("Verb") == "DELETE")
    deletedAddressesDf.createOrReplaceTempView("deletedAddressesView")
    
    delete_address_sql = """
    MERGE INTO {0}.Location
    USING deletedAddressesView ON {0}.Location.LocationId = deletedAddressesView.ExternalLocationID
    WHEN MATCHED THEN DELETE
    """.format(silver_lakehouse_name)
    
    spark.sql(delete_address_sql)

    UpdateChangeDataFeedTable(latestMaxCommitVersionAddresses, "Addresses")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotAddresses")
    spark.catalog.dropTempView("deletedAddressesView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Catalogs Data Mapping
# 
# Here we are mapping the data from the Catalogs table in the Bronze lake to the Catalog table in the silver lake. 

# CELL ********************

nextVersionStateCatalogs, latestMaxCommitVersionCatalogs = GetLastProcessedDataVersion("Catalogs")

# check if new data exists since last notebook processing
if (nextVersionStateCatalogs <= latestMaxCommitVersionCatalogs):
    print("New upload of 'Catalogs' event data is available for processing...")
    fullCatalogsDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateCatalogs) \
        .table("Catalogs") \
        .withColumn("CatalogID", when(col("Response.Body.ID").isNull(), expr("'SC-' || RouteParams.catalogID")).otherwise(expr("'SC-' || Response.Body.ID")))\
        .select("CatalogID", col("Response.Body.Name").alias("CatalogName"), col("Response.Body.Description").alias("CatalogDescription"), \
        "EventProcessedUtcTime", "_commit_version", "_change_type", "Verb", col("Date").alias("CatalogEffectivePeriodStartDate")) \
        .withColumn("CatalogEffectivePeriodEndDate", lit("2999-11-16T13:06:46.713+00:00"))

    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("CatalogID")
    latestSnapshotCatalogs = fullCatalogsDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["CatalogID"])
    
    insertedCatalogsDf = latestSnapshotCatalogs.filter(col("Verb") != "DELETE")
    insertedCatalogsDf.createOrReplaceTempView("latestSnapshotCatalogs")

    merge_catalogs_sql = """
    MERGE INTO {0}.Catalog
    USING latestSnapshotCatalogs ON {0}.Catalog.CatalogId = latestSnapshotCatalogs.CatalogID
    WHEN MATCHED THEN UPDATE SET
        CatalogName = latestSnapshotCatalogs.CatalogName, 
        CatalogDescription = latestSnapshotCatalogs.CatalogDescription,
        CatalogEffectivePeriodStartDate = latestSnapshotCatalogs.CatalogEffectivePeriodStartDate,
        CatalogEffectivePeriodEndDate = latestSnapshotCatalogs.CatalogEffectivePeriodEndDate
    WHEN NOT MATCHED THEN INSERT (CatalogId, CatalogName, CatalogDescription, CatalogEffectivePeriodStartDate, CatalogEffectivePeriodEndDate)
    VALUES (
        latestSnapshotCatalogs.CatalogID, 
        latestSnapshotCatalogs.CatalogName, 
        latestSnapshotCatalogs.CatalogDescription,
        latestSnapshotCatalogs.CatalogEffectivePeriodStartDate,
        latestSnapshotCatalogs.CatalogEffectivePeriodEndDate
        )""".format(silver_lakehouse_name)
    
    spark.sql(merge_catalogs_sql)

    # Delete Rows
    deletedCatalogDf = latestSnapshotCatalogs.filter(col("Verb") == "DELETE")
    deletedCatalogDf.createOrReplaceTempView("deletedCatalogView")

    delete_catalogs_sql = """
    MERGE INTO {0}.Catalog
    USING deletedCatalogView ON {0}.Catalog.CatalogId = deletedCatalogView.CatalogID
    WHEN MATCHED THEN DELETE
    """.format(silver_lakehouse_name)
    
    spark.sql(delete_catalogs_sql)

    UpdateChangeDataFeedTable(latestMaxCommitVersionCatalogs, "Catalogs")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotCatalogs")
    spark.catalog.dropTempView("deletedCatalogView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Categories Data Mapping
# 
# Here we are mapping the data from the Catalogs table in the Bronze lake to the ProductCategory table in the silver lake. 

# CELL ********************

nextVersionStateCategories, latestMaxCommitVersionCategories = GetLastProcessedDataVersion("Categories")

# check if new data exists since last notebook processing
if (nextVersionStateCategories <= latestMaxCommitVersionCategories):
    print("New upload of 'Categories' event data is available for processing...")
    fullCategoriesDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateCategories) \
        .table("Categories") \
        .withColumn("CategoryID", when(col("Response.Body.ID").isNull(), expr("'SC-' || RouteParams.categoryID")).otherwise(expr("'SC-' || Response.Body.ID")))\
        .select(col("CategoryID"), col("Response.Body.Name").alias("CategoryName"), col("Response.Body.Description").alias("CategoryDescription"), \
        "EventProcessedUtcTime", "_commit_version", "_change_type", "Verb")

    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("CategoryID")
    latestSnapshotCategories = fullCategoriesDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["CategoryID"])
    
    insertedCategoryDf = latestSnapshotCategories.filter(col("Verb") != "DELETE")
    insertedCategoryDf.createOrReplaceTempView("latestSnapshotCategories")

    merge_categories_sql = """
    MERGE INTO {0}.ProductCategory
    USING latestSnapshotCategories ON {0}.ProductCategory.ProductCategoryId = latestSnapshotCategories.CategoryID
    WHEN MATCHED THEN UPDATE SET
        ProductCategoryName = latestSnapshotCategories.CategoryName, 
        ProductCategoryDescription = latestSnapshotCategories.CategoryDescription
    WHEN NOT MATCHED THEN INSERT (ProductCategoryId, ProductCategoryName, ProductCategoryDescription)
    VALUES (
        latestSnapshotCategories.CategoryID, 
        latestSnapshotCategories.CategoryName, 
        latestSnapshotCategories.CategoryDescription
        )""".format(silver_lakehouse_name)
    
    spark.sql(merge_categories_sql)

    # Delete Rows
    deletedCategoryDf = latestSnapshotCategories.filter(col("Verb") == "DELETE")
    deletedCategoryDf.createOrReplaceTempView("deletedCategoryView")
    
    delete_categories_sql = """
    MERGE INTO {0}.ProductCategory
    USING deletedCategoryView ON {0}.ProductCategory.ProductCategoryId = deletedCategoryView.CategoryID
    WHEN MATCHED THEN DELETE
    """.format(silver_lakehouse_name)
    
    spark.sql(delete_categories_sql)

    UpdateChangeDataFeedTable(latestMaxCommitVersionCategories, "Categories")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotCategories")
    spark.catalog.dropTempView("deletedCategoryView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Orders Data Mapping
# 
# Here we are mapping the data from the Orders table in the Bronze lake to the Order and related tables in the silver lake. 

# CELL ********************

nextVersionStateOrders, latestMaxCommitVersionOrders = GetLastProcessedDataVersion("Orders")

# check if new data exists since last notebook processing
if (nextVersionStateOrders <= latestMaxCommitVersionOrders):
    print("New upload of 'Orders' event data is available for processing...")
    fullOrdersDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateOrders) \
        .table("Orders")\
        .select(expr("'SC-' || ID").alias("OrderId"), \
        col("DateCreated").alias("OrderBookedDate"), \
        col("DateSubmitted"), expr("'SC-' || FromUserID").alias("FromUserID"), \
        col("Total").alias("OrderTotalAmount"), \
        col("LineItemCount").alias("NumberOfOrderLines"), \
        col("Status").alias("OrderStatusTypeId"), \
        col("LineItems").alias("LineItems"), \
        "EventProcessedUtcTime", "_commit_version", "_change_type")\
        .withColumn("OrderTypeID", lit(1)) \
        .withColumn("OrderStatusStartTimestamp", lit("2000-11-16T13:06:46.713+00:00")) \
        .withColumn("OrderStatusEndTimestamp", lit("2999-11-16T13:06:46.713+00:00"))

    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("OrderId")
    latestSnapshotOrders = fullOrdersDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["OrderId"])

    latestSnapshotOrders.createOrReplaceTempView("latestSnapshotOrders")
    
    latestSnapshotOrdersExploded = latestSnapshotOrders.select("OrderId", explode("LineItems").alias("LineItems"), col("OrderStatusStartTimestamp")\
        .alias("OrderLineStatusStartTimestamp"), col("OrderStatusEndTimestamp")\
        .alias("OrderLineStatusEndTimestamp"), "OrderStatusTypeId")\
        .withColumn("OrderLineId", expr("'SC-' || LineItems.ID"))\
        .withColumn("ProductId", expr("'SC-' || LineItems.Product.ID"))\
        .withColumn("Quantity", col("LineItems.Quantity"))\
        .withColumn("TotalOrderLineAmount", col("LineItems.LineTotal"))\
        .withColumn("ProductSalesPriceAmount", col("LineItems.UnitPrice"))
    
    latestSnapshotOrdersExploded.createOrReplaceTempView("latestSnapshotOrdersExploded")
    
    #
    # Order
    #
    merge_order_sql = """MERGE INTO {0}.Order
        USING latestSnapshotOrders ON {0}.Order.OrderId = latestSnapshotOrders.OrderId
        WHEN MATCHED THEN UPDATE SET
            OrderTypeId = latestSnapshotOrders.OrderTypeID,
            CustomerId = latestSnapshotOrders.FromUserID,
            OrderBookedDate = latestSnapshotOrders.OrderBookedDate,
            OrderTotalAmount = latestSnapshotOrders.OrderTotalAmount,
            NumberOfOrderLines = latestSnapshotOrders.NumberOfOrderLines
        WHEN NOT MATCHED THEN INSERT (OrderId, CustomerId, OrderTypeId, OrderBookedDate, OrderTotalAmount, NumberOfOrderLines)
        VALUES (
            latestSnapshotOrders.OrderId,
            latestSnapshotOrders.FromUserID,
            latestSnapshotOrders.OrderTypeID,
            latestSnapshotOrders.OrderBookedDate, 
            latestSnapshotOrders.OrderTotalAmount, 
            latestSnapshotOrders.NumberOfOrderLines
    )""".format(silver_lakehouse_name)
    
    #
    # Shipment
    #
    merge_shipment_sql = """MERGE INTO {0}.Shipment
        USING latestSnapshotOrders ON {0}.Shipment.ShipmentOrderId = latestSnapshotOrders.OrderId
        WHEN MATCHED THEN UPDATE SET
            ShipmentOrderId = latestSnapshotOrders.OrderId
        WHEN NOT MATCHED THEN INSERT (ShipmentOrderId)
        VALUES (
            latestSnapshotOrders.OrderId
    )""".format(silver_lakehouse_name)

    #
    # OrderStatus
    #
    merge_order_status_sql = """MERGE INTO {0}.OrderStatus
        USING latestSnapshotOrders ON {0}.OrderStatus.OrderId = latestSnapshotOrders.OrderId
        WHEN MATCHED THEN UPDATE SET
            OrderStatusStartTimestamp = latestSnapshotOrders.OrderStatusStartTimestamp,
            OrderStatusEndTimestamp = latestSnapshotOrders.OrderStatusEndTimestamp,
            OrderStatusTypeId = latestSnapshotOrders.OrderStatusTypeId
        WHEN NOT MATCHED THEN INSERT (OrderId, OrderStatusStartTimestamp, OrderStatusEndTimestamp, OrderStatusTypeId)
        VALUES (
            latestSnapshotOrders.OrderId,
            latestSnapshotOrders.OrderStatusStartTimestamp, 
            latestSnapshotOrders.OrderStatusEndTimestamp, 
            latestSnapshotOrders.OrderStatusTypeId
    )""".format(silver_lakehouse_name)

    #
    # OrderLine
    #
    merge_order_line_sql = """MERGE INTO {0}.OrderLine
        USING latestSnapshotOrdersExploded ON {0}.OrderLine.OrderLineId = latestSnapshotOrdersExploded.OrderLineId
        WHEN MATCHED THEN UPDATE SET
            OrderId = latestSnapshotOrdersExploded.OrderId,
            ProductId = latestSnapshotOrdersExploded.ProductId,
            ProductSalesPriceAmount = latestSnapshotOrdersExploded.ProductSalesPriceAmount,
            Quantity = latestSnapshotOrdersExploded.Quantity,
            TotalOrderLineAmount = latestSnapshotOrdersExploded.TotalOrderLineAmount
        WHEN NOT MATCHED THEN INSERT (OrderId, OrderLineId, ProductId, ProductSalesPriceAmount, Quantity, TotalOrderLineAmount)
        VALUES (
            latestSnapshotOrdersExploded.OrderId,
            latestSnapshotOrdersExploded.OrderLineId,
            latestSnapshotOrdersExploded.ProductId,
            latestSnapshotOrdersExploded.ProductSalesPriceAmount,
            latestSnapshotOrdersExploded.Quantity,
            latestSnapshotOrdersExploded.TotalOrderLineAmount
    )""".format(silver_lakehouse_name)

    #
    # OrderLineStatus
    #
    merge_order_line_status_sql = """MERGE INTO {0}.OrderLineStatus
        USING latestSnapshotOrdersExploded ON {0}.OrderLineStatus.OrderLineId = latestSnapshotOrdersExploded.OrderLineId
        WHEN MATCHED THEN UPDATE SET
            OrderId = latestSnapshotOrdersExploded.OrderId,
            OrderLineStatusStartTimestamp = latestSnapshotOrdersExploded.OrderLineStatusStartTimestamp,
            OrderLineStatusEndTimestamp = latestSnapshotOrdersExploded.OrderLineStatusEndTimestamp,
            OrderLineStatusTypeId = latestSnapshotOrdersExploded.OrderStatusTypeId
        WHEN NOT MATCHED THEN INSERT (OrderId, OrderLineId, OrderLineStatusStartTimestamp, OrderLineStatusEndTimestamp, OrderLineStatusTypeId)
        VALUES (
            latestSnapshotOrdersExploded.OrderId,
            latestSnapshotOrdersExploded.OrderLineId,
            latestSnapshotOrdersExploded.OrderLineStatusStartTimestamp,
            latestSnapshotOrdersExploded.OrderLineStatusEndTimestamp,
            latestSnapshotOrdersExploded.OrderStatusTypeId
    )""".format(silver_lakehouse_name)
    
    spark.sql(merge_order_sql)
    spark.sql(merge_shipment_sql)
    spark.sql(merge_order_status_sql)
    spark.sql(merge_order_line_sql)
    spark.sql(merge_order_line_status_sql)

    UpdateChangeDataFeedTable(latestMaxCommitVersionOrders, "Orders")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotOrders")
    spark.catalog.dropTempView("latestSnapshotOrdersExploded")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Products Data Mapping
# 
# Here we are mapping the data from the Products table in the Bronze lake to the RetailProduct table in the silver lake. 

# CELL ********************

nextVersionStateProducts, latestMaxCommitVersionProducts = GetLastProcessedDataVersion("Products")

# check if new data exists since last notebook processing
if (nextVersionStateProducts <= latestMaxCommitVersionProducts):
    print("New upload of 'Products' event data is available for processing...")
    fullProductsDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateProducts) \
        .table("Products") \
        .select(expr("'SC-' || ProductID").alias("ExternalProductID"), col("Name"), \
        col("Description"), when((col("Returnable") == True), "Yes").otherwise("No").alias("ReturnPolicyStatement"), \
        col("EventProcessedUtcTime"), col("_commit_version"), col("_change_type"), col("Catalogs"), \
        col("Categories"), col("Specs")).withColumn("ReturnPolicyPeriodInDays", lit(None))\
        .withColumn("ProductCharacteristicPeriodStartTimestamp", lit("2000-11-16T13:06:46.713+00:00")) \
        .withColumn("ProductCharacteristicPeriodEndTimestamp", lit("2999-11-16T13:06:46.713+00:00"))

    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("ExternalProductID")
    latestSnapshotProducts = fullProductsDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["ExternalProductID"])

    ###
    # Logic to handle the spec changes in the base product
    ###

    # This is looking for rows in RelatedProduct that have a new set of specs in the current data upload
    # Because the data comes in from OrderCloud separately and we have to make the spec combinations ourselves (done below)
    # Whenever there are changes to a products spec, we lose the ability to look up existing specs to update
    # This solution is helping us manage updates to the specs on a base product by marking the old spec assignments
    # For deletion and then writing the new specs to replace it, we do the deletion after processing in case there
    # Are any errors during so we don't lose data

    # Existing spec options
    fullRelatedProductDf = spark.read.format("delta").table("{0}.RelatedProduct".format(silver_lakehouse_name))
    # Updated specs options in the current data upload
    updatedProductIds = latestSnapshotProducts.filter(size("Specs") > 0)
    # Keep the ones that match
    joinedUpdateRelatedProductDf = fullRelatedProductDf.join(updatedProductIds, (fullRelatedProductDf.ProductId == updatedProductIds.ExternalProductID), \
                        how = "left_semi").drop("ExternalProductID").withColumn("ProductRelationshipTypeIdMarkedForDelete", lit("delete-variant-relationship"))
    joinedUpdateRelatedProductDf.createOrReplaceTempView("MarkedForDeleteRelatedProductView")

    # We want to mark the old spec rows for deletion, we update the rows in RelatedProduct with this marking for deletion later
    mark_for_delete_related_product_sql = """MERGE INTO {0}.RelatedProduct
        USING MarkedForDeleteRelatedProductView ON 
            {0}.RelatedProduct.ProductId = MarkedForDeleteRelatedProductView.ProductID
            AND {0}.RelatedProduct.RelatedProductId = MarkedForDeleteRelatedProductView.RelatedProductId
        WHEN MATCHED THEN UPDATE SET 
            ProductRelationshipTypeId = MarkedForDeleteRelatedProductView.ProductRelationshipTypeIdMarkedForDelete
        """.format(silver_lakehouse_name)
    spark.sql(mark_for_delete_related_product_sql)

    #
    # Exploded top-level specs only
    #
    #
    # ProductCharacteristic
    explodedProducts = latestSnapshotProducts.select("ExternalProductID", "Name", "Specs.ID", explode_outer("Specs").alias("Specs"))

    #
    productCharacteristicDf = explodedProducts.select("ExternalProductID", "Specs.ID", explode("Specs.Options").alias("SpecOptions"))

    # Function to generate permutations
    def generate_permutations(row):
        external_product_id = row.ExternalProductID
        option_ids = row.OptionIDs
        # Generate permutations
        permutations = list(product(*option_ids))
        # Concatenate elements in each tuple
        result = [f"{external_product_id}-{ '-'.join(permutation)}" for permutation in permutations]
        return external_product_id, result
    
    # Collect IDs we want to permutate 
    explodedPWVariantIDsDf = explodedProducts.groupBy("ExternalProductID").agg(sort_array(collect_set("Specs.Options.ID")) \
      .alias("OptionIDs")).filter(size("OptionIDs") > 0)

    if not (explodedPWVariantIDsDf.isEmpty()):
      print("Product Specs are NOT empty...")
      # Apply the function to each row in the DataFrame
      variant_id_result_df = explodedPWVariantIDsDf.rdd.map(generate_permutations).toDF(["ExternalProductID", "Permutations"])
      explodedAndJoinedFullPWVIDsDf = variant_id_result_df.select("ExternalProductID", explode("Permutations").alias("ProductID"))\
          .join(latestSnapshotProducts, "ExternalProductID", "outer").drop(*("_commit_version", "_change_type", "EventProcessedUtcTime"))
    else: 
      print("Product Specs are empty...")
      explodedAndJoinedFullPWVIDsDf = latestSnapshotProducts.withColumn("ProductID", col("ExternalProductID"))

    new_df = explodedAndJoinedFullPWVIDsDf.select(explodedAndJoinedFullPWVIDsDf['*'], explode("Specs").alias("SpecsExploded"))
    new_df = new_df.select('*', explode("SpecsExploded.Options").alias("OptionsExploded"))

    filtered_prod_char_df = new_df.filter(col("ProductID").contains(col("OptionsExploded.ID")))\
        .select("ProductID", "Name", col("OptionsExploded.ID").alias("OptionID"), col("SpecsExploded.ID").alias("ProductCharacteristicTypeId"), \
        col("OptionsExploded.Value").alias("ProductCharacteristic"), "ProductCharacteristicPeriodStartTimestamp", \
        "ProductCharacteristicPeriodEndTimestamp").distinct()

    filtered_prod_char_df.createOrReplaceTempView("ProductCharacteristicDf")

    # Select and sink ProductCharacteristic Rows
    merge_prod_char_sql = """MERGE INTO {0}.ProductCharacteristic
        USING ProductCharacteristicDf ON 
            {0}.ProductCharacteristic.ProductId = ProductCharacteristicDf.ProductID
            AND {0}.ProductCharacteristic.ProductCharacteristicTypeId = ProductCharacteristicDf.ProductCharacteristicTypeId
            AND {0}.ProductCharacteristic.ProductCharacteristic = ProductCharacteristicDf.ProductCharacteristic
        WHEN MATCHED THEN UPDATE SET
            ProductCharacteristicPeriodStartDate = ProductCharacteristicDf.ProductCharacteristicPeriodStartTimestamp,
            ProductCharacteristicPeriodEndDate = ProductCharacteristicDf.ProductCharacteristicPeriodEndTimestamp
        WHEN NOT MATCHED THEN INSERT (
            ProductId, 
            ProductCharacteristicTypeId, 
            ProductCharacteristic, 
            ProductCharacteristicPeriodStartDate,
            ProductCharacteristicPeriodEndDate)
        VALUES (
            ProductCharacteristicDf.ProductID,
            ProductCharacteristicDf.ProductCharacteristicTypeId,
            ProductCharacteristicDf.ProductCharacteristic,
            ProductCharacteristicDf.ProductCharacteristicPeriodStartTimestamp,
            ProductCharacteristicDf.ProductCharacteristicPeriodEndTimestamp
    )""".format(silver_lakehouse_name)

    #
    # RelatedProduct
    #
    relatedProductDf = explodedAndJoinedFullPWVIDsDf.select(["ExternalProductID", "ProductID"]).where(size("Specs") > 0)\
        .withColumnRenamed("ProductID", "RelatedProductID").withColumnRenamed("ExternalProductID", "ProductID")\
        .withColumn("ProductRelationshipTypeId", lit("variant-relationship"))
    relatedProductDf.createOrReplaceTempView("relatedProductDf")

    # Select and sink RelatedProduct Rows
    merge_related_prod_sql = """MERGE INTO {0}.RelatedProduct
        USING relatedProductDf ON {0}.RelatedProduct.RelatedProductId = relatedProductDf.RelatedProductID
        WHEN MATCHED THEN UPDATE SET
            ProductId = relatedProductDf.ProductID,
            ProductRelationshipTypeId = relatedProductDf.ProductRelationshipTypeId
        WHEN NOT MATCHED THEN INSERT (ProductId, RelatedProductId, ProductRelationshipTypeId)
        VALUES (
            relatedProductDf.ProductId, 
            relatedProductDf.RelatedProductId, 
            relatedProductDf.ProductRelationshipTypeId
    )""".format(silver_lakehouse_name)

    #
    # Item and RetailProduct
    #    
    grouped_prod_char_df = filtered_prod_char_df.sort(["ProductID", "OptionID"], ascending = True)\
        .withColumn("id", monotonically_increasing_id()).groupby("ProductID", "Name")\
        .agg(array_distinct(collect_list("ProductCharacteristic")).alias("ProductCharacteristic"), \
        array_distinct(collect_list("OptionID")).alias("OptionID"))\
        .select("ProductID", "Name", array_join("ProductCharacteristic", ".").alias("ProductCharacteristic"), \
        array_join("OptionID", ",").alias("OptionID")).withColumn("ItemNameConcat", concat_ws("-", "Name", "ProductCharacteristic"))\
        .drop("Name", "ProductCharacteristic", "OptionID")

    full_retail_prod_item_df = explodedAndJoinedFullPWVIDsDf.join(grouped_prod_char_df, "ProductID", "outer")\
        .withColumn("ProductId", when(col("ProductID").isNull(), col("ExternalProductID")).otherwise(col("ProductID")))\
        .withColumn("ItemSku", when((col("Specs").isNull()) | (size("Specs") == 0), lit(None)).otherwise(expr("ProductId || '-sku'")))\
        .withColumn("ItemName", when((col("Specs").isNull()) | (size("Specs") == 0), col("Name")).otherwise(col("ItemNameConcat")))\
        .select("ProductId", col("Name").alias("ProductName"), "Description", "ItemSku", "ItemName", "Description", \
        "ReturnPolicyStatement", "ReturnPolicyPeriodInDays", expr("'SC-' || Catalogs[0]").alias("CatalogID"), \
        expr("'SC-' || Categories[0]['ID']").alias("CategoryID"))

    full_retail_prod_item_df.createOrReplaceTempView("RetailProductAndItemEntityTempView")

    # Select and sink RetailProduct Rows
    merge_products_sql = """MERGE INTO {0}.RetailProduct
        USING RetailProductAndItemEntityTempView ON {0}.RetailProduct.ProductId = RetailProductAndItemEntityTempView.ProductId
        WHEN MATCHED THEN UPDATE SET
            ProductName = RetailProductAndItemEntityTempView.ProductName, 
            ProductDescription = RetailProductAndItemEntityTempView.Description, 
            ReturnPolicyStatement = RetailProductAndItemEntityTempView.ReturnPolicyStatement, 
            ReturnPolicyPeriodInDays = RetailProductAndItemEntityTempView.ReturnPolicyPeriodInDays, 
            ItemSku = RetailProductAndItemEntityTempView.ItemSku,
            CatalogId = RetailProductAndItemEntityTempView.CatalogID, 
            CategoryId = RetailProductAndItemEntityTempView.CategoryID
        WHEN NOT MATCHED THEN INSERT (ProductId, ProductName, ProductDescription, ReturnPolicyStatement, ReturnPolicyPeriodInDays, ItemSku, CatalogId, CategoryId)
        VALUES (
            RetailProductAndItemEntityTempView.ProductId,
            RetailProductAndItemEntityTempView.ProductName, 
            RetailProductAndItemEntityTempView.Description, 
            RetailProductAndItemEntityTempView.ReturnPolicyStatement, 
            RetailProductAndItemEntityTempView.ReturnPolicyPeriodInDays, 
            RetailProductAndItemEntityTempView.ItemSku,
            RetailProductAndItemEntityTempView.CatalogID, 
            RetailProductAndItemEntityTempView.CategoryID
    )""".format(silver_lakehouse_name)

    # Select and sink Item Rows
    merge_item_sql = """MERGE INTO {0}.Item
        USING RetailProductAndItemEntityTempView ON {0}.Item.ProductId = RetailProductAndItemEntityTempView.ProductId
        WHEN MATCHED THEN UPDATE SET
            ItemSku = RetailProductAndItemEntityTempView.ItemSku,
            ItemName = RetailProductAndItemEntityTempView.ItemName,
            ItemDescription = RetailProductAndItemEntityTempView.Description
        WHEN NOT MATCHED THEN INSERT (ProductId, ItemSku, ItemName, ItemDescription)
        VALUES (
            RetailProductAndItemEntityTempView.ProductId, 
            RetailProductAndItemEntityTempView.ItemSku, 
            RetailProductAndItemEntityTempView.ItemName, 
            RetailProductAndItemEntityTempView.Description
    )""".format(silver_lakehouse_name)

    #
    # ProductCharacteristicType
    #
    productCharacteristicTypeDf = explodedProducts.select(expr("'SC-' || Specs.ID").alias("ProductCharacteristicTypeId"), \
        col("Specs.Name").alias("ProductCharacteristicTypeName")).distinct().na.drop(subset=["ProductCharacteristicTypeId"])
    productCharacteristicTypeDf.createOrReplaceTempView("productCharacteristicTypeDf")
    
    # Select and sink ProductCharacteristicType Rows
    merge_prod_char_type_sql = """MERGE INTO {0}.ProductCharacteristicType
        USING productCharacteristicTypeDf ON {0}.ProductCharacteristicType.ProductCharacteristicTypeId = productCharacteristicTypeDf.ProductCharacteristicTypeId
        WHEN MATCHED THEN UPDATE SET
            ProductCharacteristicTypeName = productCharacteristicTypeDf.ProductCharacteristicTypeName
        WHEN NOT MATCHED THEN INSERT (ProductCharacteristicTypeId, ProductCharacteristicTypeName)
        VALUES (
            ProductCharacteristicTypeDf.ProductCharacteristicTypeId, 
            ProductCharacteristicTypeDf.ProductCharacteristicTypeName
    )""".format(silver_lakehouse_name)

    #
    # SQL Statement Execution
    #
    spark.sql(merge_related_prod_sql)
    spark.sql(merge_products_sql)
    spark.sql(merge_item_sql)
    spark.sql(merge_prod_char_sql)
    spark.sql(merge_prod_char_type_sql)

    ###
    # Expired variant IDs we want to remove from the data are gathered here, then we delete from the respective tables
    ###
    productIdsToDeleteDf = spark.read.format("delta").table("{0}.RelatedProduct".format(silver_lakehouse_name))\
        .filter(col("ProductRelationshipTypeId") == "delete-variant-relationship")\
        .select(col("RelatedProductId").alias("ProductIdToDelete")).distinct()
    productIdsToDeleteDf.createOrReplaceTempView("productIdsToDeleteView")
    
    delete_retail_product_sql = '''MERGE INTO {0}.RetailProduct
        USING productIdsToDeleteView ON {0}.RetailProduct.ProductId = productIdsToDeleteView.ProductIdToDelete
        WHEN MATCHED THEN DELETE
    '''.format(silver_lakehouse_name)

    delete_item_sql = '''MERGE INTO {0}.Item
        USING productIdsToDeleteView ON {0}.Item.ProductId = productIdsToDeleteView.ProductIdToDelete
        WHEN MATCHED THEN DELETE
    '''.format(silver_lakehouse_name)

    delete_product_characteristic_sql = '''MERGE INTO {0}.ProductCharacteristic
        USING productIdsToDeleteView ON {0}.ProductCharacteristic.ProductId = productIdsToDeleteView.ProductIdToDelete
        WHEN MATCHED THEN DELETE
    '''.format(silver_lakehouse_name)

    delete_related_product_sql = '''MERGE INTO {0}.RelatedProduct
        USING productIdsToDeleteView ON {0}.RelatedProduct.RelatedProductId = productIdsToDeleteView.ProductIdToDelete
        WHEN MATCHED THEN DELETE
    '''.format(silver_lakehouse_name)
    
    #
    # SQL Statement Execution (DELETE)
    #
    spark.sql(delete_retail_product_sql)
    spark.sql(delete_item_sql)
    spark.sql(delete_product_characteristic_sql)
    spark.sql(delete_related_product_sql)

    UpdateChangeDataFeedTable(latestMaxCommitVersionProducts, "Products")

    # Memory Clean-up
    spark.catalog.dropTempView("MarkedForDeleteRelatedProductView")
    spark.catalog.dropTempView("ProductCharacteristicDf")
    spark.catalog.dropTempView("relatedProductDf")
    spark.catalog.dropTempView("RetailProductAndItemEntityTempView")
    spark.catalog.dropTempView("productCharacteristicTypeDf")
    spark.catalog.dropTempView("productIdsToDeleteView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## UserGroupAssignments Data Mapping

# CELL ********************

nextVersionStateUserGroupAssignments, latestMaxCommitVersionUserGroupAssignments = GetLastProcessedDataVersion("UserGroupAssignments")

# check if new data exists since last notebook processing
if (nextVersionStateUserGroupAssignments <= latestMaxCommitVersionUserGroupAssignments):
    print("New upload of 'UserGroupAssignments' event data is available for processing...")
    fullUserGroupAssignmentsDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateUserGroupAssignments) \
        .table("UserGroupAssignments") \
        .filter(col("Response.Body.Errors").isNull())\
        .withColumn("ExternalUserGroupID", when(col("Request.Body.userGroupID").isNull(), \
        expr("'SC-' || RouteParams.userGroupID")).otherwise(expr("'SC-' || Request.Body.userGroupID")))\
        .withColumn("ExternalUserID", when(col("Request.Body.userID").isNull(), \
        expr("'SC-' || RouteParams.userID")).otherwise(expr("'SC-' || Request.Body.userID")))\
        .select("ExternalUserGroupID", "ExternalUserID", "Verb",\
        "EventProcessedUtcTime", "_commit_version", "_change_type")
        
    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("ExternalUserID")
    latestSnapshotUserGroupAssignments = fullUserGroupAssignmentsDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["ExternalUserID"])
    
    insertedUserGroupAssignmentsDf = latestSnapshotUserGroupAssignments.filter(col("Verb") != "DELETE")
    insertedUserGroupAssignmentsDf.createOrReplaceTempView("latestSnapshotUserGroupAssignments")
    
    # Select and sink CustomerGroupCustomer Rows  
    merge_user_group_assign_sql = """  
    MERGE INTO {0}.CustomerGroupCustomer  
    USING latestSnapshotUserGroupAssignments ON {0}.CustomerGroupCustomer.CustomerId = latestSnapshotUserGroupAssignments.ExternalUserID  
    AND {0}.CustomerGroupCustomer.CustomerGroupId = latestSnapshotUserGroupAssignments.ExternalUserGroupID  
    WHEN MATCHED THEN UPDATE SET  
        CustomerGroupId = latestSnapshotUserGroupAssignments.ExternalUserGroupID  
    WHEN NOT MATCHED THEN INSERT (CustomerGroupId, CustomerId)  
    VALUES (  
        latestSnapshotUserGroupAssignments.ExternalUserGroupID,  
        latestSnapshotUserGroupAssignments.ExternalUserID  
    )  
    """.format(silver_lakehouse_name)
    
    spark.sql(merge_user_group_assign_sql)

    # Delete Rows
    deletedUserGroupAssignmentsDf = latestSnapshotUserGroupAssignments.filter(col("Verb") == "DELETE")
    deletedUserGroupAssignmentsDf.createOrReplaceTempView("deletedUserGroupAssignmentsView")

    delete_user_group_assign_groups_sql = """  
    MERGE INTO {0}.CustomerGroupCustomer  
    USING deletedUserGroupAssignmentsView ON {0}.CustomerGroupCustomer.CustomerId = deletedUserGroupAssignmentsView.ExternalUserID
    AND {0}.CustomerGroupCustomer.CustomerGroupId = deletedUserGroupAssignmentsView.ExternalUserGroupID
    WHEN MATCHED THEN UPDATE SET CustomerGroupId = NULL;
    """.format(silver_lakehouse_name)
    
    spark.sql(delete_user_group_assign_groups_sql)
    
    UpdateChangeDataFeedTable(latestMaxCommitVersionUserGroupAssignments, "UserGroupAssignments")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotUserGroupAssignments")
    spark.catalog.dropTempView("deletedUserGroupAssignmentsView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## UserGroups Data Mapping

# CELL ********************

nextVersionStateUserGroups, latestMaxCommitVersionUserGroups = GetLastProcessedDataVersion("UserGroups")

# check if new data exists since last notebook processing
if (nextVersionStateUserGroups <= latestMaxCommitVersionUserGroups):
    print("New upload of 'UserGroups' event data is available for processing...")
    fullUserGroupsDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateUserGroups) \
        .table("UserGroups") \
        .withColumn("ExternalUserGroupID", when(col("Response.Body.ID").isNull(), expr("'SC-' || RouteParams.userGroupID")).otherwise(expr("'SC-' || Response.Body.ID")))\
        .select("ExternalUserGroupID", col("Response.Body.Name").alias("UserGroupName"), \
        col("Response.Body.Description").alias("UserGroupDescription"), "Verb",\
        "EventProcessedUtcTime", "_commit_version", "_change_type")
    
    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("ExternalUserGroupID")
    latestSnapshotUserGroups = fullUserGroupsDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["ExternalUserGroupID"])
    
    insertedUserGroupsDf = latestSnapshotUserGroups.filter(col("Verb") != "DELETE")
    insertedUserGroupsDf.createOrReplaceTempView("latestSnapshotUserGroups")
    
    # Select and sink CustomerGroup Rows  
    merge_user_groups_sql = """  
    MERGE INTO {0}.CustomerGroup  
    USING latestSnapshotUserGroups ON {0}.CustomerGroup.CustomerGroupId = latestSnapshotUserGroups.ExternalUserGroupID  
    WHEN MATCHED THEN UPDATE SET  
        CustomerGroupName = latestSnapshotUserGroups.UserGroupName,  
        CustomerGroupDescription = latestSnapshotUserGroups.UserGroupDescription  
    WHEN NOT MATCHED THEN INSERT (CustomerGroupId, CustomerGroupName, CustomerGroupDescription)  
    VALUES (  
        latestSnapshotUserGroups.ExternalUserGroupID,  
        latestSnapshotUserGroups.UserGroupName,  
        latestSnapshotUserGroups.UserGroupDescription  
    )  
    """.format(silver_lakehouse_name)
    
    spark.sql(merge_user_groups_sql)

    # Delete Rows
    deletedUserGroupsDf = latestSnapshotUserGroups.filter(col("Verb") == "DELETE")
    deletedUserGroupsDf.createOrReplaceTempView("deletedUserGroupsView")

    delete_user_groups_sql = """  
    MERGE INTO {0}.CustomerGroup  
    USING deletedUserGroupsView ON {0}.CustomerGroup.CustomerGroupId = deletedUserGroupsView.ExternalUserGroupID
    WHEN MATCHED THEN DELETE  
    """.format(silver_lakehouse_name)
    
    spark.sql(delete_user_groups_sql)

    UpdateChangeDataFeedTable(latestMaxCommitVersionUserGroups, "UserGroups")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotUserGroups")
    spark.catalog.dropTempView("deletedUserGroupsView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Users Data Mapping
# 
# Here we are mapping the data from the Users table in the Bronze lake to IndividualCustomer, CustomerTelephoneNumber and CustomerEmail tables in the silver lake. 

# CELL ********************

nextVersionStateUsers, latestMaxCommitVersionUsers = GetLastProcessedDataVersion("Users")

# check if new data exists since last notebook processing
if (nextVersionStateUsers <= latestMaxCommitVersionUsers):
    print("New upload of 'Users' event data is available for processing...")
    fullUsersDf = spark.read.format("delta") \
        .option("readChangeFeed", "true") \
        .option("startingVersion", nextVersionStateUsers) \
        .table("Users") \
        .withColumn("ExternalCustomerID", when(col("Response.Body.ID").isNull(), expr("'SC-' || RouteParams.userID"))\
        .otherwise(expr("'SC-' || Response.Body.ID"))).select("ExternalCustomerID", \
        expr("Response.Body.FirstName || ' ' || Response.Body.LastName").alias("ConcatCustomerName"), "Response.Body.Email", \
        regexp_replace(regexp_replace(col("Response.Body.Phone"), '\\s+', ''), '\\+', '00').cast('decimal(10,0)')\
        .alias("Phone"), "Verb", "EventProcessedUtcTime", "_commit_version", "_change_type")

    # Select and show us the latest version of each duplicated row
    w = Window.partitionBy("ExternalCustomerID")
    latestSnapshotUsers = fullUsersDf.where(col("_change_type") != "delete")\
        .withColumn("latestProcessedTimestamp", max("EventProcessedUtcTime").over(w)) \
        .where(col("EventProcessedUtcTime") == col("latestProcessedTimestamp")) \
        .drop("latestProcessedTimestamp")\
        .withColumn("latestCommitVersion", max("_commit_version").over(w)) \
        .where(col("_commit_version") == col("latestCommitVersion")) \
        .drop("latestCommitVersion").na.drop(subset=["ExternalCustomerID"])
    
    insertedUsersDf = latestSnapshotUsers.filter(col("Verb") != "DELETE")
    insertedUsersDf.createOrReplaceTempView("latestSnapshotUsers")
    
    # Select and sink IndividualCustomer Rows
    merge_user_sql = """
    MERGE INTO {0}.IndividualCustomer
    USING latestSnapshotUsers ON {0}.IndividualCustomer.CustomerId = latestSnapshotUsers.ExternalCustomerID
    WHEN MATCHED THEN UPDATE SET IndividualCustomerName = latestSnapshotUsers.ConcatCustomerName
    WHEN NOT MATCHED THEN INSERT (CustomerId, IndividualCustomerName)
    VALUES (latestSnapshotUsers.ExternalCustomerID, latestSnapshotUsers.ConcatCustomerName)
    """.format(silver_lakehouse_name)
    spark.sql(merge_user_sql)

    # Select and sink CustomerEmail Rows
    merge_email_sql = """
    MERGE INTO {0}.CustomerEmail
    USING latestSnapshotUsers ON {0}.CustomerEmail.CustomerId = latestSnapshotUsers.ExternalCustomerID
    WHEN MATCHED THEN UPDATE SET EmailAddress = latestSnapshotUsers.Email
    WHEN NOT MATCHED THEN INSERT (CustomerId, EmailAddress)
    VALUES (latestSnapshotUsers.ExternalCustomerID, latestSnapshotUsers.Email)
    """.format(silver_lakehouse_name)
    spark.sql(merge_email_sql)

    # Select and sink CustomerTelephoneNumber Rows
    merge_telephone_sql = """
    MERGE INTO {0}.CustomerTelephoneNumber
    USING latestSnapshotUsers ON {0}.CustomerTelephoneNumber.CustomerId = latestSnapshotUsers.ExternalCustomerID
    WHEN MATCHED THEN UPDATE SET TelephoneNumber = latestSnapshotUsers.Phone
    WHEN NOT MATCHED THEN INSERT (CustomerId, TelephoneNumber)
    VALUES (latestSnapshotUsers.ExternalCustomerID, latestSnapshotUsers.Phone)
    """.format(silver_lakehouse_name)
    spark.sql(merge_telephone_sql)

    # Delete Rows
    deletedUsersDf = latestSnapshotUsers.filter(col("Verb") == "DELETE")
    deletedUsersDf.createOrReplaceTempView("deletedUsersView")

    delete_user_sql = """
    MERGE INTO {0}.IndividualCustomer
    USING deletedUsersView ON {0}.IndividualCustomer.CustomerId = deletedUsersView.ExternalCustomerID
    WHEN MATCHED THEN DELETE
    """.format(silver_lakehouse_name)
    spark.sql(delete_user_sql)

    delete_email_sql = """
    MERGE INTO {0}.CustomerEmail
    USING deletedUsersView ON {0}.CustomerEmail.CustomerId = deletedUsersView.ExternalCustomerID
    WHEN MATCHED THEN DELETE
    """.format(silver_lakehouse_name)
    spark.sql(delete_email_sql)

    delete_telephone_sql = """
    MERGE INTO {0}.CustomerTelephoneNumber
    USING deletedUsersView ON {0}.CustomerTelephoneNumber.CustomerId = deletedUsersView.ExternalCustomerID
    WHEN MATCHED THEN DELETE
    """.format(silver_lakehouse_name)
    spark.sql(delete_telephone_sql)

    UpdateChangeDataFeedTable(latestMaxCommitVersionUsers, "Users")

    # Memory Clean-up
    spark.catalog.dropTempView("latestSnapshotUsers")
    spark.catalog.dropTempView("deletedUsersView")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
