"""Start the standalone documentation search; no external services required."""
import argparse
import json
import os
import socket
import threading
import webbrowser
from urllib.request import build_opener, ProxyHandler
from lib.documentation import ROOT
from lib.service import SupportService
from lib.server import LocalServer


def configured_port():
    settings = {}
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip()
    value = int(os.getenv('PORT', settings.get('PORT', '3101')))
    if not 1 <= value <= 65535:
        raise ValueError('PORT must be between 1 and 65535.')
    return value


def port_state(port):
    with socket.socket() as connection:
        connection.settimeout(1)
        if connection.connect_ex(('127.0.0.1', port)) != 0:
            return 'free'
    try:
        with build_opener(ProxyHandler({})).open(f'http://127.0.0.1:{port}/api/status', timeout=2) as response:
            if json.load(response).get('application') == 'agentguard-documentation-final':
                return 'running'
    except (OSError, ValueError, AttributeError):
        pass
    return 'occupied'


def open_page(url):
    try:
        webbrowser.open(url)
    except Exception:
        print('Open this address in your browser:', url)


def main():
    parser = argparse.ArgumentParser(description='AgentGuard local documentation search')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        port = configured_port()
        url = f'http://127.0.0.1:{port}'
        state = port_state(port)
        if state == 'occupied':
            raise ValueError(f'Port {port} belongs to another application. Choose another PORT in .env.')
        if state == 'running':
            print('This project is already running at', url)
            if not args.no_browser:
                open_page(url)
            return 0
        service = SupportService()
        with LocalServer(port, service) as server:
            print(f'AgentGuard documentation search: {url}', flush=True)
            print('Keep this terminal open. Press Ctrl+C to stop.', flush=True)
            if not args.no_browser:
                # Socket is listening before opening the browser; requests wait for serve_forever.
                threading.Thread(target=open_page, args=(url,), daemon=True).start()
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print('\nChatbot stopped.')
        return 0
    except (OSError, ValueError) as error:
        print('Startup failed:', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
