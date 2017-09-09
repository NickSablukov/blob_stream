from time import time

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session
from bson.objectid import ObjectId

from datatools import redirect
from models import Message, User


class Login(web.View):

    @aiohttp_jinja2.template('login.html')
    async def get(self):
        session = await get_session(self.request)
        if session.get('user'):
            redirect(self.request, 'chat_list')
        return {}

    async def post(self):
        data = await self.request.post()
        user = User(self.request.db, data)
        result = await user.check_user()
        if isinstance(result, dict):
            session = await get_session(self.request)
            session['user'] = str(result['_id'])
            session['last_visit'] = time()
            redirect(self.request, 'login')
        else:
            return aiohttp_jinja2.render_template('login.html', self.request, {
                'error': result
            })


class Registration(web.View):
    @aiohttp_jinja2.template('registration.html')
    async def get(self, **kwargs):
        session = await get_session(self.request)
        if session.get('user'):
            redirect(self.request, 'chat_list')
        return {}

    async def post(self, **kwargs):
        data = await self.request.post()
        user = User(self.request.db, data)
        result = await user.create_user()

        if isinstance(result, ObjectId):
            session = await get_session(self.request)
            session['user'] = str(result)
            session['last_visit'] = time()
            redirect(self.request, 'login')
        else:
            return aiohttp_jinja2.render_template('registration.html', self.request, {
                'error': result
            })


class Logout(web.View):
    async def get(self, **kwargs):
        session = await get_session(self.request)
        if session.get('user'):
            del session['user']
            redirect(self.request, 'login')
        else:
            raise web.HTTPForbidden(body=b'Forbidden')


class ChatList(web.View):
    @aiohttp_jinja2.template('index.html')
    async def get(self):
        messages = await Message(self.request.db).get_messages()
        session = await get_session(self.request)
        user = User(self.request.db, {'id': session.get('user')})
        login = await user.get_login()
        return {'messages': list(reversed(messages))[:5], 'login': login}


class Chat(web.View):
    async def get(self):
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)

        session = await get_session(self.request)
        user = User(self.request.db, {'id': session.get('user')})
        login = await user.get_login()

        for _ws in self.request.app['websockets']:
            _ws.send_str('<small style="color: red">Пользовтель %s зашел в чат</small>' % login)
        self.request.app['websockets'].append(ws)

        async for msg in ws:
            if msg.data == 'close':
                await ws.close()
            else:
                message = Message(self.request.db)
                await message.save(user=login, msg=msg.data)

                for _ws in self.request.app['websockets']:
                    _ws.send_str('<b>(%s)</b> %s' % (login, msg.data))

        self.request.app['websockets'].remove(ws)
        for _ws in self.request.app['websockets']:
            _ws.send_str('<small style="color: red">Пользователь %s вышел из чата</small>' % login)

        return ws
