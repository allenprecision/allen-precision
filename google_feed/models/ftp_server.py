from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ftplib import FTP
import base64
import io
import os
from datetime import datetime
import tempfile

try:
    import paramiko
except ImportError:
    raise ImportError('This module needs paramiko to automatically write backups to the FTP through SFTP. '
                      'Please install paramiko on your system. (sudo pip3 install paramiko)')


class ServerConfig(models.Model):
    _name = 'server.config'
    _description = "This model is use for create a server configuration of feed file"

    config_type = fields.Selection([('using_pass', 'Using Password'), ('using_file', 'Using File')],
                                   default="using_pass", string='Configuration Type')
    name = fields.Char('Server Name')
    host = fields.Char('Host')
    protocol = fields.Selection([('ftp', 'FTP'), ('sftp', 'SFTP')], default="ftp", string='Protocol')
    user_name = fields.Char('User')
    password = fields.Char('Password')
    port = fields.Integer('Port')
    server_config = fields.Binary("Server Configuration File")
    file_path = fields.Char(string="Path Of File")
    file_name = fields.Char('File Name')

    @api.onchange('protocol')
    def onchange_protocol(self):
        if self.protocol == 'ftp':
            self.config_type = 'using_pass'

    def authorize_FTP(self):
        client = None
        try:
            client = FTP()
            client.connect(self.host, self.port)
            client.login(self.user_name, self.password)
        except Exception as e:
            raise UserError(_('The server error is : %s ' % (str(e))))
        return client

    def authorize_SFTP(self):
        sftp_client = None
        sftp_client = paramiko.SSHClient()
        sftp_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.config_type and self.config_type == 'using_file':
            tmp_file_path = self.get_path_of_tmp_file()
            file_data = self.write_tmp_file()
            key_pass = ""
            key_file = tmp_file_path
            try:
                key_pass = paramiko.RSAKey.from_private_key_file(key_file, key_pass)
                sftp_client.connect(hostname=self.host, port=self.port, username=self.user_name, pkey=key_pass,
                                    look_for_keys=False, allow_agent=False, timeout=10)
                self.delete_generated_tmp_file()
            except Exception as e:
                raise UserError(_('The server error is : %s ' % (str(e))))
        else:
            try:
                sftp_client.connect(self.host, self.port, self.user_name, self.password, timeout=10)
            except Exception as e:
                raise UserError(_('The server error is : %s ' % (str(e))))

        return sftp_client

    def get_path_of_tmp_file(self):
        # Generate a file in temp file inside the tmp folder and getting path of generated path
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file_path = tmp_file.name
            self.file_path = file_path
            return file_path

    def write_tmp_file(self):
        # writing this file
        binary_data = base64.b64decode(self.server_config)
        full_path = os.path.join(self.file_path)
        with open(full_path, 'wb') as file:
            file.write(binary_data)
        return binary_data

    def test_server_connection(self):
        self.ensure_one()
        has_failed = False
        if self.protocol == 'ftp':
            client = None
            try:
                client = self.authorize_FTP()
            except Exception as e:
                has_failed = True
                raise UserError(_('The server error is : %s ' % (str(e))))
            finally:
                if client:
                    client.close()
        else:
            sftp_client = None
            try:
                sftp_client = self.authorize_SFTP()
            except Exception as e:
                has_failed = True
                raise UserError(_('The server error is : %s ' % (str(e))))
            finally:
                if sftp_client:
                    sftp_client.close()

        if not has_failed:
            title = _("Connection Test Succeeded!")
            message = _("Everything seems properly set up!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }

    def delete_generated_tmp_file(self):
        file_path = self.file_path
        try:
            os.remove(file_path)
            return "True"
        except OSError as error:
            return "False"

    def upload_feed_on_server(self, feed_id):
        error_msg = ''
        if self.protocol == 'ftp':
            client = None
            try:
                client = self.authorize_FTP()
                if client:
                    client.cwd(feed_id.server_path)
                    data = base64.b64decode(feed_id.feed_file)
                    with io.BytesIO(data) as file:
                        client.storbinary('STOR %s' % feed_id.file_name, file)
            except Exception as e:
                error_msg = str(e)
            finally:
                if client:
                    client.close()
        else:
            sftp = None
            try:
                sftp = self.authorize_SFTP()
                if sftp:
                    data = base64.b64decode(feed_id.feed_file)
                    sftp_obj = sftp.open_sftp()
                    sftp_obj.chdir(feed_id.server_path)
                    with io.BytesIO(data) as file:
                        sftp_obj.putfo(file, feed_id.file_name)
                        sftp_obj.close()
            except Exception as e:
                error_msg = str(e)
            finally:
                if sftp:
                    sftp.close()
        if error_msg:
            self.env['feed.process.error.log'].create(
                {'feed_id': feed_id.id, 'error_datetime': datetime.now(), 'error_message': error_msg,
                 'file_name': feed_id.file_name})
