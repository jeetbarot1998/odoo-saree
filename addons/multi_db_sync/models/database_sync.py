from odoo import models, api
import logging
import psycopg2
import json

_logger = logging.getLogger(__name__)


class DatabaseSync(models.TransientModel):
    _name = 'database.sync'
    _description = 'Database Synchronization'

    TABLES_TO_SYNC = [
        'res_partner',
        'product_template',
        'product_product',
        'stock_warehouse',
        'stock_location',
        'pos_session',
        'pos_order',
        'pos_payment',
        'purchase_order',
        'sale_order',
        'stock_picking',
        'stock_move'
    ]

    def adapt_value(self, value, data_type):
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

        elif data_type == 'numeric' or data_type == 'double precision':
            return float(value) if value is not None else None

        elif data_type in ['timestamp without time zone', 'timestamp with time zone', 'date']:
            return value if value else None

        elif data_type in ['character varying', 'text']:
            return str(value) if value is not None else None

        return value

    @api.model
    def sync_all_tables(self):
        """Synchronize all specified tables using DatabaseConnectionManager config"""
        _logger.info("Starting database synchronization...")

        connection_manager = self.env['database.connection.manager']

        # Get online database configuration
        online_config = connection_manager.search([
            ('db_type', '=', 'online'),
            ('is_active', '=', True)
        ], limit=1)

        if not online_config:
            _logger.error("No active online database configuration found")
            return False

        _logger.info(f"Found online database config: {online_config.name}")
        target_conn = None

        try:
            # Connect to online database
            target_params = online_config.get_connection_params()
            _logger.info(
                f"Attempting to connect to online database: {target_params['dbname']} at {target_params['host']}:{target_params['port']}")

            target_conn = psycopg2.connect(**target_params)
            target_conn.autocommit = False
            target_cr = target_conn.cursor()
            _logger.info("Successfully connected to online database")

            # Use current connection for source
            source_cr = self.env.cr

            for table in self.TABLES_TO_SYNC:
                _logger.info(f"Starting sync for table: {table}")
                try:
                    self.sync_table(table, source_cr, target_cr)
                    target_conn.commit()  # Commit after each table sync
                    _logger.info(f"Successfully synced table: {table}")
                except Exception as e:
                    _logger.error(f"Error syncing table {table}: {str(e)}")
                    target_conn.rollback()
                    continue

            return True

        except Exception as e:
            _logger.error(f"Sync process error: {str(e)}")
            if target_conn:
                target_conn.rollback()
            raise

        finally:
            if target_conn:
                target_conn.close()
                _logger.info("Closed connection to online database")

    def sync_table(self, table_name, source_cr, target_cr, batch_size=1000):
        """Synchronize a specific table between databases"""
        try:
            # Get column information
            source_cr.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                AND table_schema = 'public'
                ORDER BY ordinal_position;
            """, (table_name,))

            columns_info = source_cr.fetchall()
            columns = [col[0] for col in columns_info]
            column_types = {col[0]: col[1] for col in columns_info}

            columns_str = ', '.join(columns)

            # Get records to sync
            source_cr.execute(f"""
                SELECT {columns_str}
                FROM {table_name} 
                WHERE sync_status IN ('pending', 'error')
                ORDER BY id
            """)

            records = source_cr.fetchall()
            _logger.info(f"Found {len(records)} records to sync in {table_name}")

            if not records:
                return

            # Process records
            success_count = 0
            error_count = 0

            for record in records:
                try:
                    record_dict = dict(zip(columns, record))
                    _logger.info(f"Syncing {table_name} record ID {record_dict['id']}")

                    # Remove sync-related columns from update clause
                    update_columns = [c for c in columns if c not in ['sync_status', 'sync_last_date', 'sync_error']]
                    update_sets = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_columns])

                    # Prepare the upsert query
                    placeholders = ', '.join(['%s'] * len(columns))
                    upsert_query = f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES ({placeholders})
                        ON CONFLICT (id) DO UPDATE SET
                        {update_sets}
                    """

                    adapted_values = [
                        self.adapt_value(record_dict[col], column_types[col])
                        for col in columns
                    ]

                    target_cr.execute(upsert_query, adapted_values)

                    # Update source record status
                    source_cr.execute(f"""
                        UPDATE {table_name} 
                        SET sync_status = 'synced',
                            sync_last_date = NOW(),
                            sync_error = NULL
                        WHERE id = %s
                    """, (record_dict['id'],))

                    success_count += 1
                    _logger.info(f"Successfully synced {table_name} record ID {record_dict['id']}")

                except Exception as e:
                    error_message = str(e)
                    _logger.error(f"Error syncing {table_name} record ID {record_dict['id']}: {error_message}")

                    source_cr.execute(f"""
                        UPDATE {table_name} 
                        SET sync_status = 'error',
                            sync_last_date = NOW(),
                            sync_error = %s
                        WHERE id = %s
                    """, (error_message, record_dict['id']))

                    error_count += 1

            _logger.info(f"Sync summary for {table_name}:")
            _logger.info(f"  Success: {success_count}")
            _logger.info(f"  Errors: {error_count}")

        except Exception as e:
            _logger.error(f"Error syncing table {table_name}: {str(e)}")
            raise
