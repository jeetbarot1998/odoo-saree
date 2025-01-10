from contextlib import contextmanager
from odoo import api, fields, models
import logging
from odoo.exceptions import UserError
import psycopg2
import odoo.sql_db

_logger = logging.getLogger(__name__)


class DatabaseConnectionManager(models.Model):
    _name = 'database.connection.manager'
    _description = 'Database Connection Manager'

    name = fields.Char('Connection Name', required=True)
    db_type = fields.Selection([
        ('local', 'Local Database'),
        ('online', 'Online Database')
    ], string='Database Type', required=True)
    host = fields.Char('Host')
    port = fields.Integer('Port', default=5432)
    database = fields.Char('Database Name')
    user = fields.Char('Database User')
    password = fields.Char('Database Password')
    is_active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Connection Name must be unique!')
    ]

    def get_connection_params(self):
        """Generate connection parameters dictionary"""
        if not all([self.host, self.port, self.database, self.user, self.password]):
            raise UserError('All connection fields must be filled')

        return {
            'dbname': self.database,
            'user': self.user,
            'password': self.password,
            'host': self.host,
            'port': self.port
        }

    @api.model
    @contextmanager
    def get_connections(self):
        """Get connections to both local and online databases"""
        connections = {
            'local': self.env.cr,  # Current database connection
            'online': None,
            'online_dbname': None  # Added to store database name
        }

        try:
            # Get online database configuration
            online_config = self.search([
                ('db_type', '=', 'online'),
                ('is_active', '=', True)
            ], limit=1)

            if online_config:
                try:
                    # Test connection first
                    conn_params = online_config.get_connection_params()
                    test_conn = psycopg2.connect(**conn_params)
                    test_conn.close()

                    # If test successful, use Odoo's connection pooling
                    db = odoo.sql_db.db_connect(online_config.database)
                    cr = db.cursor()
                    connections.update({
                        'online': cr,
                        'online_dbname': online_config.database
                    })
                    _logger.info(f"Successfully connected to online database: {online_config.database}")
                except Exception as e:
                    _logger.error(f"Failed to connect to online database: {str(e)}")
                    connections.update({
                        'online': None,
                        'online_dbname': None
                    })

            yield connections

        finally:
            # Close online connection if it was opened
            if connections.get('online'):
                try:
                    connections['online'].close()
                except Exception as e:
                    _logger.error(f"Error closing online connection: {str(e)}")

    def test_connection(self):
        """Test the database connection"""
        try:
            # Get connection parameters
            conn_params = self.get_connection_params()

            # Construct connection URI for display (mask password)
            masked_uri = f"postgresql://{conn_params['user']}:****@{conn_params['host']}:{conn_params['port']}/{conn_params['dbname']}"

            # Test connection using psycopg2 directly
            try:
                conn = psycopg2.connect(**conn_params)
                with conn.cursor() as cur:
                    cur.execute("SELECT version();")
                    version = cur.fetchone()[0]
                conn.close()

                # Also test Odoo's connection pooling
                db = odoo.sql_db.db_connect(conn_params['dbname'])
                with db.cursor() as cr:
                    cr.execute("SELECT 1")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Success',
                        'message': f'Successfully connected to:\n{masked_uri}\n\nServer version: {version}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except psycopg2.OperationalError as e:
                # Handle connection errors specifically
                error_msg = str(e).strip()
                raise UserError(f'Connection failed to:\n{masked_uri}\n\nError: {error_msg}')
            except Exception as e:
                # Handle other database errors
                raise UserError(f'Database error with:\n{masked_uri}\n\nError: {str(e)}')

        except Exception as e:
            # Handle parameter validation errors
            raise UserError(f'Configuration error: {str(e)}')