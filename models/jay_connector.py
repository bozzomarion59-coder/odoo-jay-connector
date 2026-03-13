import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None
    _logger.warning("requests library not found. Install it with: pip install requests")


class JayConnectorSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    jay_api_url = fields.Char(
        string="Jay Instance URL",
        config_parameter='jay_connector.api_url',
        help="The URL of your Jay instance (e.g. https://www.jay-assistant.fr)",
    )
    jay_api_key = fields.Char(
        string="Jay API Key",
        config_parameter='jay_connector.api_key',
        help="Your Jay API key. You can find it in your Jay dashboard under Settings.",
    )
    jay_user_email = fields.Char(
        string="Jay Account Email",
        config_parameter='jay_connector.user_email',
        help="The email address associated with your Jay account.",
    )
    jay_connected = fields.Boolean(
        string="Connected",
        config_parameter='jay_connector.connected',
        readonly=True,
    )

    def action_test_jay_connection(self):
        """Test the connection to Jay API."""
        self.ensure_one()

        api_url = self.jay_api_url or self.env['ir.config_parameter'].sudo().get_param('jay_connector.api_url')
        api_key = self.jay_api_key or self.env['ir.config_parameter'].sudo().get_param('jay_connector.api_key')

        if not api_url or not api_key:
            raise UserError("Please fill in both the Jay Instance URL and API Key before testing.")

        if requests is None:
            raise UserError("The 'requests' Python library is required. Please install it.")

        api_url = api_url.rstrip('/')

        try:
            response = requests.get(
                f"{api_url}/api/health",
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                timeout=10,
            )

            if response.status_code == 200:
                self.env['ir.config_parameter'].sudo().set_param('jay_connector.connected', 'True')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection successful',
                        'message': 'Jay is connected and ready to sync your CRM data.',
                        'type': 'success',
                        'sticky': False,
                    },
                }
            else:
                self.env['ir.config_parameter'].sudo().set_param('jay_connector.connected', 'False')
                raise UserError(
                    f"Connection failed (HTTP {response.status_code}). "
                    "Please check your URL and API key."
                )

        except requests.exceptions.Timeout:
            self.env['ir.config_parameter'].sudo().set_param('jay_connector.connected', 'False')
            raise UserError("Connection timed out. Please check the URL and try again.")
        except requests.exceptions.ConnectionError:
            self.env['ir.config_parameter'].sudo().set_param('jay_connector.connected', 'False')
            raise UserError("Could not connect to Jay. Please check the URL.")

    def action_disconnect_jay(self):
        """Disconnect from Jay."""
        self.ensure_one()
        sudo_param = self.env['ir.config_parameter'].sudo()
        sudo_param.set_param('jay_connector.connected', 'False')
        sudo_param.set_param('jay_connector.api_key', '')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Disconnected',
                'message': 'Jay has been disconnected from Odoo.',
                'type': 'warning',
                'sticky': False,
            },
        }
