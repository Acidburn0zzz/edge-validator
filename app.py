# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

import rapidjson
from flask import Flask, request
from dockerflow.flask import Dockerflow


app = Flask(__name__)
dockerflow = Dockerflow(app)


def load_namespace(base, namespace):
    """Return a dictionary of all files with the `*.schema.json` suffix.

    Namespaces help differentiate ingestion systems. For example, `telemetry`
    refers to pings generated by various Firefox products. Other namespaced
    ingestion pipelines may exists due to generic ingestion.
    """
    schemas = dict()
    for root, _, files in os.walk(os.path.join(base, namespace)):
        for name in files:
            if not name.endswith(".schema.json"):
                continue
            with open(os.path.join(root, name), "r") as f:
                key = name.split(".schema.json")[0]
                schemas[key] = rapidjson.Validator(f.read())
                print("Registered {}.{} ".format(namespace, key))
    return schemas


def load_data():
    """Load schemas into memory while taking advantage of data preloading.
    
    See https://stackoverflow.com/a/42440784
    """

    # Schemas have a naming convention. See `sync.sh` for an example of the ingestion
    # submission format.
    schemas = {}

    # List the separate data ingestion namespaces
    base = "resources/schemas"
    for namespace in os.listdir("resources/schemas"):
        schemas[namespace] = load_namespace(base, namespace)

    versions = {}
    for namespace in schemas.keys():
        ns_version = {}
        for key in schemas[namespace].keys():
            doctype, docversion = key.split('.')
            # take the most recent version determined by string comparison
            ns_version[doctype] = max(ns_version.get(doctype, '0'), docversion)
        versions[namespace] = ns_version

    return schemas, versions


NAMESPACE_SCHEMAS, SCHEMA_VERSIONS = load_data()


def build_route(endpoint, params):
    return '/'.join([endpoint] + params)


telemetry_ingestion = [
    '<namespace>',          # generally `telemetry` in this context
    '<uuid:docid>',         # used for document de-duplication
    '<doctype>',
    '<appName>',
    '<appVersion>',
    '<appUpdateChannel>',
    '<appBuildId>',
]

generic_ingestion = [
    '<namespace>',
    '<doctype>',
    '<int:docversion>',
    '<uuid:docid>',
]


@app.route(build_route('/submit', telemetry_ingestion), methods=['POST'])
# the validation API is tolerant of missing docversion and docid
@app.route(build_route('/submit', generic_ingestion[:-2]),  methods=['POST'])
@app.route(build_route('/submit', generic_ingestion[:-1]),  methods=['POST'])
@app.route(build_route('/submit', generic_ingestion),  methods=['POST'])
# NOTE: See URL Route Registrations for more details on how multiple routing
# specifications are wrapped here.
# [docs] http://flask.pocoo.org/docs/1.0/api/#url-route-registrations
def submit(namespace, doctype, docversion=None, **kwargs):
    resp = ('OK', 200)

    try:
        docversion = docversion or SCHEMA_VERSIONS[namespace][doctype]
        key = "{}.{}".format(doctype, docversion)
        json_data = request.get_json(force=True)
        NAMESPACE_SCHEMAS[namespace][key](rapidjson.dumps(json_data))
    except ValueError as e:
        resp = ("Validation Error: {}".format(e), 400)
    except KeyError as e:
        resp = ("Missing Schema: {}".format(e), 400)
    return resp

