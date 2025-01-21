# core_models.py
import logging

from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'sync.tracking.mixin']
    _table = 'product_template'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'qty_available',
            'virtual_available',
            'taxes_id',
            'supplier_taxes_id',
            'image_1920',
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'sync.tracking.mixin']
    _table = 'product_product'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'qty_available',
            'virtual_available',
            'image_1920',
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'sync.tracking.mixin']
    _table = 'pos_order'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'session_id',
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self._handle_dual_db_creation()
        return res


class PosSession(models.Model):
    _name = 'pos.session'
    _inherit = ['pos.session', 'sync.tracking.mixin']
    _table = 'pos_session'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'sync.tracking.mixin']
    _table = 'res_partner'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'image_1920',
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
            'company_registry',
            'child_ids',
            'bank_ids',
            'user_ids',
        ]


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'sync.tracking.mixin']
    _table = 'purchase_order'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
            'access_token',
        ]


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'sync.tracking.mixin']
    _table = 'stock_picking'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'sync.tracking.mixin']
    _table = 'stock_move'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'sync.tracking.mixin']
    _table = 'sale_order'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
            'access_token',
            'signature',
            'signed_by',
        ]

    def action_confirm(self):
        res = super().action_confirm()
        self._handle_dual_db_creation()
        return res


class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'sync.tracking.mixin']
    _table = 'stock_warehouse'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = ['stock.location', 'sync.tracking.mixin']
    _table = 'stock_location'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]


class PosPayment(models.Model):
    _name = 'pos.payment'
    _inherit = ['pos.payment', 'sync.tracking.mixin']
    _table = 'pos_payment'

    def _get_sync_excluded_fields(self):
        excluded = super()._get_sync_excluded_fields()
        return excluded + [
            'activity_ids',
            'message_ids',
            'message_follower_ids',
            'message_main_attachment_id',
        ]