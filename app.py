#! /usr/bin/env python3.6
import argparse

from asyncio import subprocess
from aiohttp import web


class Server:
    def __init__(self, host: str=None, port:  int=None):
        assert isinstance(host, str)
        assert isinstance(port, int)

        self.host = host
        self.port = port

    def run(self):
        self.check_ffmpeg()

        app = web.Application()
        app['websockets'] = []

        app.router.add_route('GET', '/', self.transfer_socket)
        app.on_shutdown.append(self.on_shutdown)
        web.run_app(app, host=self.host, port=self.port)

    def transfer_socket(self):
        pass

    @classmethod
    async def on_shutdown(cls, app):
        for ws in app['websockets']:
            await ws.close(code=1001, message='Stop socket')

    @staticmethod
    async def check_ffmpeg():
        command = 'ffmpeg -h'
        status_code = await subprocess.create_subprocess_exec(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        assert status_code == 0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', type=str, help='running host')
    parser.add_argument('port', type=int, help='running port')

    args = parser.parse_args()

    return args.host, args.port

if __name__ == '__main__':
    server = Server(*parse_args())
    server.run()
