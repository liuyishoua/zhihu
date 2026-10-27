from pathlib import Path
import sys
from flask import request,jsonify
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'account-maintenance'))
from bridge import Bridge


def register(app,service,directory):
    bridge=Bridge(directory)
    @app.before_request
    def machine_auth():
        if request.path.startswith('/maintenance/') and not bridge.authorized(request.headers):return jsonify(error='Maintenance credential required'),401
    @app.get('/maintenance/accounts')
    def accounts():
        a=service.platform.identity()
        return {'items':[{'id':str(a['id']),'external_id':str(a['id']),'name':a['name'],'kind':'web','status':a['status'],
            'capability':'cookie','login_methods':['cookie'],'url':'https://d.58nft.net:9455/'}] if a else []}
    @app.get('/maintenance/events')
    def events():return {'items':bridge.events(max(0,int(request.args.get('after',0))))}
    @app.get('/maintenance/attempts/<id>')
    def attempt(id):return jsonify(error='Attempt absent'),404
