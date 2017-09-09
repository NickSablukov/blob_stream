#! /usr/bin/env python3.6

import argparse
import logging
from asyncio import get_event_loop

import asyncio
import socketio

from aiohttp import web
from subprocess import Popen, PIPE

sio = socketio.AsyncServer()
logger = logging.getLogger('transfer-logger')


class Server:
    def __init__(self, host: str = None, port: int = None):
        assert isinstance(host, str)
        assert isinstance(port, int)

        self.host = host
        self.port = port
        self.ffmpeg_processes = {}
        self.loop = get_event_loop()

    def run(self):
        logger.info(f'Run server on {self.host}:{self.port}')
        self.check_ffmpeg()

        self.app = web.Application(loop=self.loop)
        self.app['websockets'] = []

        sio.attach(self.app)
        web.run_app(self.app, host=self.host, port=self.port)

    @staticmethod
    def check_ffmpeg():
        logger.info('Check ffmpeg  ... ')
        command = 'ffmpeg -h'
        proc = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        proc.wait()

        assert proc.returncode == 0, 'ffmpeg is not installed'

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser()
        parser.add_argument('host', type=str, help='running host')
        parser.add_argument('port', type=int, help='running port')

        args = parser.parse_args()

        return args.host, args.port


@sio.on('start')
async def connect(key, rtmp_url):
    print("connect ")
    options = [
        'ffmpeg', '-vcodec', 'libvpx', '-i', '-',
        '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency',
        '-an', '-bufsize', '1000', '-f', 'flv', rtmp_url
    ]

    server.ffmpeg_processes[key] = await asyncio.create_subprocess_exec(
        ' '.join(options), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
    )


@sio.on('binarystream')
async def message(key, data):
    print("message ")
    if key in server.ffmpeg_processes:
        await server.ffmpeg_processes[key].stdin.write(data)


@sio.on('disconnect')
async def disconnect(key):
    print('disconnect ')
    if key in server.ffmpeg_processes:
        server.ffmpeg_processes[key].terminate()
        await server.ffmpeg_processes[key].wait()
        del server.ffmpeg_processes[key]


if __name__ == '__main__':
    args = Server.parse_args()

    server = Server(*args)
    server.run()
