from datetime import timedelta
from odoo import api, fields, models
import logging
import odoo.sql_db

_logger = logging.getLogger(__name__)


class MultiDBSyncManager(models.AbstractModel):
    _name = 'multi.db.sync.manager'
    _description = 'Multi Database Sync Manager'

    @api.model
    def create_record(self, model_name, values):
        """Create record with dual-database support"""
        connection_manager = self.env['database.connection.manager']

        # Create in local database first
        local_record = self.env[model_name].create(values)

        with connection_manager.get_connections() as connections:
            if connections.get('online') and connections.get('online_dbname'):
                try:
                    sync_values = local_record._prepare_sync_values()
                    registry = odoo.registry(connections['online_dbname'])

                    with registry.cursor() as new_cr:
                        online_env = api.Environment(new_cr, self.env.uid, self.env.context)
                        online_record = online_env[model_name].create(sync_values)
                        new_cr.commit()

                        local_record.write({
                            'sync_online_record_id': online_record.id,
                            'sync_is_synced': True,
                            'sync_status': 'synced',
                            'sync_last_date': fields.Datetime.now(),
                        })
                except Exception as e:
                    _logger.error(f"Failed to create online record: {str(e)}")
                    local_record.write({
                        'sync_status': 'error',
                        'sync_error': str(e)
                    })

        return local_record.id

    def sync_offline_records(self):
        """Sync records created during offline mode"""
        models_to_sync = [
            'product.template', 'product.product',
            'pos.order', 'pos.session',
            'res.partner', 'purchase.order',
            'stock.picking', 'stock.move',
            'sale.order', 'stock.warehouse',
            'stock.location', 'pos.payment'
        ]

        for model in models_to_sync:
            self._sync_model_records(model)

    def _sync_model_records(self, model_name):
        """Sync records for specific model"""
        records = self.env[model_name].search([
            ('sync_status', 'in', ['pending', 'error']),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=7))
        ])

        if not records:
            return

        connection_manager = self.env['database.connection.manager']
        with connection_manager.get_connections() as connections:
            if not connections.get('online') or not connections.get('online_dbname'):
                _logger.warning("Online environment not available for sync")
                return

            registry = odoo.registry(connections['online_dbname'])
            with registry.cursor() as new_cr:
                try:
                    online_env = api.Environment(new_cr, self.env.uid, self.env.context)

                    for record in records:
                        try:
                            self._sync_single_record(record, online_env)
                            new_cr.commit()
                        except Exception as e:
                            new_cr.rollback()
                            _logger.error(f"Sync failed for {model_name} record {record.id}: {str(e)}")
                            record.write({
                                'sync_status': 'error',
                                'sync_error': str(e)
                            })
                except Exception as e:
                    _logger.error(f"Failed to sync {model_name} records: {str(e)}")
                    raise

    def _sync_single_record(self, record, online_env):
        """Sync single record to online database"""
        sync_values = record._prepare_sync_values()

        if record.sync_online_record_id:
            online_record = online_env[record._name].browse(record.sync_online_record_id)
            if online_record.exists():
                online_record.write(sync_values)
            else:
                online_record = online_env[record._name].create(sync_values)
                record.sync_online_record_id = online_record.id
        else:
            online_record = online_env[record._name].create(sync_values)
            record.sync_online_record_id = online_record.id

        record.write({
            'sync_is_synced': True,
            'sync_status': 'synced',
            'sync_last_date': fields.Datetime.now(),
            'sync_error': False
        })