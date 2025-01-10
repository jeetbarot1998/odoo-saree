from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class SyncTrackingMixin(models.AbstractModel):
    _name = 'sync.tracking.mixin'
    _description = 'Synchronization Tracking Mixin'

    sync_online_record_id = fields.Integer(string='Online Record ID', copy=False)
    sync_is_synced = fields.Boolean(string='Is Synced', default=False, copy=False)
    sync_error = fields.Text(string='Sync Error', copy=False)
    sync_last_date = fields.Datetime('Last Sync Date', copy=False)
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
        ('conflict', 'Conflict'),
    ], default='pending', copy=False, string='Sync Status')

    def _get_sync_fields(self):
        """Get fields to synchronize for this model"""
        return [f.name for f in self._fields.values()
                if not f.compute and f.store
                and f.name not in self._get_sync_excluded_fields()
                and not f.name.startswith('sync_')]

    def _get_sync_excluded_fields(self):
        """Fields to exclude from synchronization"""
        return [
            'id', 'create_date', 'write_date',
            'sync_online_record_id', 'sync_is_synced',
            'sync_error', 'sync_last_date', 'sync_status'
        ]

    def _prepare_sync_values(self):
        """Prepare values for synchronization"""
        sync_fields = self._get_sync_fields()
        vals = {}
        for field in sync_fields:
            if field in self._fields:
                field_value = self[field]
                if self._fields[field].type == 'many2one':
                    if field_value:
                        vals[field] = field_value.id
                elif self._fields[field].type in ['many2many', 'one2many']:
                    if field_value:
                        vals[field] = [(6, 0, field_value.ids)]
                else:
                    vals[field] = field_value
        return vals

    def _handle_dual_db_creation(self):
        """Handle record creation in both databases"""
        try:
            sync_manager = self.env['multi.db.sync.manager']
            sync_values = self._prepare_sync_values()
            sync_manager.create_record(self._name, sync_values)
        except Exception as e:
            _logger.error(f"Failed to sync record: {str(e)}")
            self.write({
                'sync_status': 'error',
                'sync_error': str(e)
            })

    def retry_sync(self):
        """Manually retry synchronization for this record"""
        self.ensure_one()
        _logger.info(f"Attempting to retry sync for {self._name} record {self.id}")

        try:
            # Reset error state
            self.write({
                'sync_status': 'pending',
                'sync_error': False
            })

            # Attempt resync using the sync manager
            sync_manager = self.env['multi.db.sync.manager']
            sync_manager._sync_single_record(self)

            # Commit after successful sync
            self.env.cr.commit()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Record synchronized successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            self.env.cr.rollback()
            error_message = str(e)
            _logger.error(f"Manual sync retry failed for {self._name} record {self.id}: {error_message}")

            self.write({
                'sync_status': 'error',
                'sync_error': error_message
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync Failed',
                    'message': f'Sync failed: {error_message}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def retry_sync_batch(self):
        """Retry synchronization for multiple records"""
        success_count = 0
        error_count = 0

        for record in self:
            try:
                record.write({
                    'sync_status': 'pending',
                    'sync_error': False
                })

                sync_manager = self.env['multi.db.sync.manager']
                sync_manager._sync_single_record(record)
                success_count += 1
                self.env.cr.commit()

            except Exception as e:
                self.env.cr.rollback()
                error_message = str(e)
                _logger.error(f"Batch sync retry failed for {record._name} record {record.id}: {error_message}")

                record.write({
                    'sync_status': 'error',
                    'sync_error': error_message
                })
                error_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': f'Successfully synced {success_count} records, {error_count} failed',
                'type': 'info',
                'sticky': True,
            }
        }

    @api.model
    def get_sync_stats(self):
        """Get synchronization statistics for this model"""
        return {
            'total': self.search_count([]),
            'pending': self.search_count([('sync_status', '=', 'pending')]),
            'synced': self.search_count([('sync_status', '=', 'synced')]),
            'error': self.search_count([('sync_status', '=', 'error')]),
            'conflict': self.search_count([('sync_status', '=', 'conflict')])
        }