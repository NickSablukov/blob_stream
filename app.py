#! /usr/bin/env python3.6

import argparse
import logging
from asyncio import get_event_loop

import asyncio
import socketio

from aiohttp import web
from subprocess import Popen, PIPE, DEVNULL

sio = socketio.AsyncServer()
logger = logging.getLogger('transfer-logger')
server = None


class FFMPEGProcess:
    DEFAULT_LIFE = 6
    LIFE_STEP = 3

    ffmpeg = None
    rtmp_url = None
    options = None
    key = None

    def __init__(self, key: str, rtmp_url: str):
        self.life = self.DEFAULT_LIFE

        self.key = key
        self.rtmp_url = rtmp_url
        self.options = [
            'ffmpeg', '-vcodec', 'libvpx', '-i', '-',
            '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency',
            '-an', '-bufsize', '1000', '-f', 'flv', rtmp_url
        ]

    async def run(self):
        self.ffmpeg = await asyncio.create_subprocess_exec(
            *self.options,
            stdin=asyncio.subprocess.PIPE, loop=server.loop, stdout=DEVNULL, stderr=DEVNULL
        )

    async def stop(self):
        try:
            self.ffmpeg.kill()
            await self.ffmpeg.wait()
        except AttributeError:
            pass

    def set_default_life(self):
        self.life = self.DEFAULT_LIFE

    def is_life(self):
        return self.life > 0


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

        self.app = web.Application(loop=self.loop)
        self.app['websockets'] = []

        sio.attach(self.app)

        self.loop.create_task(self.watch_processes())
        web.run_app(self.app, host=self.host, port=self.port)

    async def watch_processes(self):
        while True:
            for process in self.ffmpeg_processes.values():
                try:
                    process.life -= process.LIFE_STEP
                    if not process.is_life():
                        self.stop_process(process.key)
                except TypeError:
                    pass

            await asyncio.sleep(FFMPEGProcess.LIFE_STEP, loop=self.loop)

    def add_process(self, process: FFMPEGProcess):
        self.ffmpeg_processes[process.key] = process

    async def stop_process(self, key: str):
        try:
            await self.ffmpeg_processes[key].stop()
            del self.ffmpeg_processes[key]
        except KeyError:
            pass

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
async def connect(key, url):
    process = FFMPEGProcess(key, url)
    server.add_process(process)

    await process.run()


@sio.on('stream')
async def message(key, data):
    try:
        process = server.ffmpeg_processes[key]
        process.ffmpeg.stdin.write(data)
        process.life = process.set_default_life()
    except (KeyError, AttributeError):
        pass


@sio.on('disconected')
async def disconected(key):
    server.stop_process(key)


if __name__ == '__main__':
    args = Server.parse_args()

    server = Server(*args)
    server.check_ffmpeg()
    server.run()
