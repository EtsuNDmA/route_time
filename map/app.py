import json
import logging
import os
from datetime import date, datetime, timedelta

from bson import ObjectId
from bson.errors import InvalidId as InvalidIdExeption
from flask import Flask, jsonify, make_response, render_template, request
from flask_pymongo import PyMongo
from flask_restful import Api, Resource, reqparse


class MongoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, date):
            return o.isoformat()
        elif isinstance(o, timedelta):
            return (datetime.min + o).time().isoformat()
        else:
            return super().default(self, o)


app = Flask(__name__)

app.logger.setLevel(logging.DEBUG)

app.config['DEBUG'] = True
app.config['MONGO_DBNAME'] = 'mainDB'
app.config['MONGO_URI'] = 'mongodb://mongo:27017/mainDB'

app.json_encoder = MongoJSONEncoder

api = Api(app)

mongo = PyMongo(app)
db = mongo.db


@app.route('/map', methods=['GET'])
def map_view():
    """Отображает карту и заданный маршрут"""
    try:
        route_id = ObjectId(request.args['route_id'])
    except KeyError:
        raise InvalidUsage('Empty route_id', status_code=400)
    except InvalidIdExeption:
        raise InvalidUsage('Invalid route_id format', status_code=400)

    route = db.routes.find_one_or_404({'_id': route_id})
    yamaps_apikey = os.environ.get('ROUTE_TIME_YAMAPS_API_KEY')

    is_reversed = bool(int(request.args.get('is_reversed', 0)))
    if is_reversed:
        route['from_address'], route['to_address'] = route.get('to_address'), route.get('from_address')
        route['from_alias'], route['to_alias'] = route.get('to_alias'), route.get('from_alias')

    return render_template('map.jinja', route=route, yamaps_apikey=yamaps_apikey)


@api.resource('/help', '/api', '/api/help')
class ApiHelp(Resource):
    def get(self):
        return jsonify({
            '/api/routes': 'List all routes',
            '/api/routes/<route_id>': 'GET POST DELETE route'
        })


@api.resource('/api/routes/<route_id>')
class Route(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('user_id', type=str, help='Unique ID of user')

    def get(self, route_id):
        try:
            route = db.routes.find_one({'_id': ObjectId(route_id)})
            return jsonify({'ok': True, 'result': route})
        except InvalidIdExeption:
            return jsonify({'ok': False, 'description': 'Invalid ID format', 'error_code': 404})

    def delete(self, route_id):
        try:
            route = {'_id': ObjectId(route_id)}
            result = db.routes.delete_one(route)
            if not result.acknowledged:
                return jsonify({'ok': False, 'description': 'Cannot delete', 'error_code': 404})
            return jsonify({'ok': True, 'result': {'deletedCount': result.deleted_count}})
        except InvalidIdExeption:
            return jsonify({'ok': False, 'description': 'Invalid ID format', 'error_code': 404})


@api.resource('/api/routes')
class RouteList(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('user_id', type=str, help='Unique ID of user')
    parser.add_argument('from_address', type=str, help='Source address')
    parser.add_argument('to_address', type=str, help='Destination address')
    parser.add_argument('from_alias', type=str, help='Alias for source address')
    parser.add_argument('to_alias', type=str, help='Alias for destination address')

    def get(self):
        args = self.parser.parse_args()
        user_id = args.get('user_id')
        if user_id is None:
            return jsonify({'ok': False, 'description': 'Need user_id', 'error_code': 400})
        routes = {'routes': list(db.routes.find({'user_id': user_id}).sort('time', 1))}
        return jsonify({'ok': True, 'result': routes})

    def post(self):
        args = self.parser.parse_args()
        print(args)
        if args.get('user_id') is None:
            return jsonify({'ok': False, 'description': 'Need user_id', 'error_code': 400})
        if args.get('from_address') is None:
            return jsonify({'ok': False, 'description': 'Need from_address', 'error_code': 400})
        if args.get('to_address') is None:
            return jsonify({'ok': False, 'description': 'Need to_address', 'error_code': 400})
        route = dict(
            user_id=args.get('user_id'),
            from_address=args.get('from_address'),
            from_alias=args.get('from_alias'),
            to_address=args.get('to_address'),
            to_alias=args.get('to_alias'),
            time=datetime.utcnow(),
        )
        result = db.routes.insert_one(route)

        if result.acknowledged:
            return jsonify({'ok': True, 'result': {'routeID': result.inserted_id}})
        else:
            return jsonify({'ok': False, 'description': 'Cannot create', 'error_code': 500})


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'ok': False, 'description': 'Not found'}), 404)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['description'] = self.message
        rv['ok'] = False
        rv['error_code'] = self.status_code
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


if __name__ == '__main__':
    app.run()
