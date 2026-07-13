from channels.generic.websocket import AsyncWebsocketConsumer
import json


class DashConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.groupname = 'dashboard'
        await self.channel_layer.group_add(
            self.groupname,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.groupname,
            self.channel_name
        )

    async def receive(self, text_data):
        datapoint = json.loads(text_data)
        _seat = datapoint['seat']
        _status = datapoint['status']

        await self.channel_layer.group_send(
            self.groupname,
            {
                'type': 'deprocessing',
                'seat': _seat,
                'status': _status
            }
        )

        print('>>>>', text_data)

        # pass

    async def deprocessing(self, event):
        val_seat = event['seat']
        val_status = event['status']
        await self.send(text_data=json.dumps({'seat': val_seat, 'status': val_status}))