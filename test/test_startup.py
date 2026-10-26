import os
import unittest
from unittest.mock import patch
from run import configured_port, port_state


class StartupTests(unittest.TestCase):
    def test_port_validation(self):
        with patch.dict(os.environ, {'PORT': '3101'}):
            self.assertEqual(configured_port(), 3101)
        for value in ('invalid', '0', '65536'):
            with patch.dict(os.environ, {'PORT': value}), self.assertRaises(ValueError):
                configured_port()

    def test_free_port(self):
        import socket
        with socket.socket() as connection:
            connection.bind(('127.0.0.1', 0))
            port = connection.getsockname()[1]
        self.assertEqual(port_state(port), 'free')
