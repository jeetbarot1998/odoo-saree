import psycopg2
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync.log'),
        logging.StreamHandler()
    ]
)

# Database connection parameters
SOURCE_DB = {
    'dbname': 'odoo',
    'user': 'odoo',
    'password': 'odoo',
    'host': 'localhost',
    'port': '5432'
}

TARGET_DB = {
    'dbname': 'odoo',
    'user': 'odoo',
    'password': 'odoo',
    'host': 'localhost',
    'port': '5433'
}


def connect_to_db(params):
    """Create a database connection"""
    try:
        conn = psycopg2.connect(**params)
        conn.autocommit = False
        return conn
    except psycopg2.Error as e:
        logging.error(f"Error connecting to database: {e}")
        raise


def adapt_value(value, data_type):
    """Adapt values based on their PostgreSQL data type"""
    if value is None:
        return None

    if data_type == 'jsonb':
        if isinstance(value, dict):
            return json.dumps(value)
        elif isinstance(value, str):
            try:
                json.loads(value)
                return value
            except json.JSONDecodeError:
                return json.dumps({})
        return json.dumps({})

    elif data_type == 'boolean':
        return bool(value)

    elif data_type == 'integer':
        return int(value) if value is not None else None

    elif data_type == 'numeric':
        return float(value) if value is not None else None

    elif data_type in ['timestamp without time zone', 'timestamp with time zone']:
        return value if value else None

    elif data_type in ['character varying', 'text']:
        return str(value) if value is not None else None

    return value


def sync_table(table_name, source_conn, target_conn):
    """Synchronize a specific table between databases"""
    try:
        source_cur = source_conn.cursor()
        target_cur = target_conn.cursor()

        # Get column information
        source_cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table_name,))

        columns_info = source_cur.fetchall()
        columns = [col[0] for col in columns_info]
        column_types = {col[0]: col[1] for col in columns_info}

        columns_str = ', '.join(columns)

        # Get records to sync
        source_cur.execute(f"""
            SELECT {columns_str}
            FROM {table_name} 
            WHERE sync_status IN ('pending', 'error')
        """)

        records = source_cur.fetchall()
        logging.info(f"Found {len(records)} records to sync in {table_name}")

        # Remove sync-related columns from update clause
        update_columns = [c for c in columns if c not in ['sync_status', 'sync_last_date', 'sync_error']]
        update_sets = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_columns])

        # Prepare the upsert query
        placeholders = ', '.join(['%s'] * len(columns))
        upsert_query = f"""
            INSERT INTO {table_name} ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET
            {update_sets},
            sync_status = 'synced',
            sync_last_date = NOW(),
            sync_error = NULL
        """

        success_count = 0
        error_count = 0

        # Process each record
        for record in records:
            try:
                record_dict = dict(zip(columns, record))
                adapted_values = [
                    adapt_value(record_dict[col], column_types[col])
                    for col in columns
                ]

                target_cur.execute(upsert_query, adapted_values)

                # Update source record status
                source_cur.execute(f"""
                    UPDATE {table_name} 
                    SET sync_status = 'synced',
                        sync_last_date = NOW(),
                        sync_error = NULL
                    WHERE id = %s
                """, (record_dict['id'],))

                source_conn.commit()
                target_conn.commit()

                success_count += 1
                logging.info(f"Successfully synced {table_name} record ID: {record_dict['id']}")

            except Exception as e:
                error_message = str(e)
                logging.error(f"Error syncing {table_name} record ID {record_dict['id']}: {error_message}")

                source_cur.execute(f"""
                    UPDATE {table_name} 
                    SET sync_status = 'error',
                        sync_last_date = NOW(),
                        sync_error = %s
                    WHERE id = %s
                """, (error_message, record_dict['id']))

                source_conn.commit()
                target_conn.rollback()
                error_count += 1

        logging.info(f"Sync summary for {table_name}:")
        logging.info(f"  Success: {success_count}")
        logging.info(f"  Errors: {error_count}")
        logging.info(f"  Total processed: {success_count + error_count}")

    except Exception as e:
        logging.error(f"Error syncing table {table_name}: {e}")
        raise


def sync_all_tables():
    """Synchronize all specified tables"""
    source_conn = None
    target_conn = None

    try:
        source_conn = connect_to_db(SOURCE_DB)
        target_conn = connect_to_db(TARGET_DB)

        # List of tables to sync
        tables = ['product_template', 'product_product']

        for table in tables:
            logging.info(f"Starting sync for table: {table}")
            sync_table(table, source_conn, target_conn)
            logging.info(f"Completed sync for table: {table}")

    except Exception as e:
        logging.error(f"Sync process error: {e}")
        if source_conn:
            source_conn.rollback()
        if target_conn:
            target_conn.rollback()
        raise

    finally:
        if source_conn:
            source_conn.close()
        if target_conn:
            target_conn.close()


if __name__ == "__main__":
    try:
        logging.info("Starting synchronization process")
        sync_all_tables()
        logging.info("Synchronization completed successfully")
    except Exception as e:
        logging.error(f"Synchronization failed: {e}")