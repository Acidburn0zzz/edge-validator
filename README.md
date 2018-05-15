# edge-validator

A service-endpoint for validating pings against `mozilla-pipeline-schemas`.

[![CircleCI](https://circleci.com/gh/acmiyaguchi/edge-validator.svg?style=svg)](https://circleci.com/gh/acmiyaguchi/edge-validator)

See [bug 1452166](https://bugzilla.mozilla.org/show_bug.cgi?id=1452166) for motivating background.

## Quickstart

**Warning: prebuilt docker images are not available yet. Please refer to the installation guide further below.**

Start the docker container to start the local service at `localhost:8000`. This will fetch the image from dockerhub.
```bash
docker run -it edge-validator:latest
```

Simply POST to the endpoint to check if a document is valid. The `testing` namespace has an example schema for
validation.

```bash
$ OK_DATA="$(echo '{"payload": {"foo": true, "bar": 1, "baz": "hello world"}}')"
$ curl -X POST -H "Content-Type: application/json" -d "${OK_DATA}" localhost:8000/submit/testing/test/1
> OK

$ BAD_DATA="$(echo '{"payload": {"foo": null, "bar": "3", "baz": 55}}')"
$ curl -X POST -H "Content-Type: application/json" -d "${BAD_DATA}" localhost:8000/submit/testing/test/1
> BAD: ('type', '#/properties/payload/properties/foo', '#/payload/foo')
```

The exposed port can be changed through the `PORT` environment variable. It is possible to mount a set of local
json-schemas by mounting a folder structure mirroring `mozilla-services/mozilla-pipeline-schemas` to the container's
`/app/resources/schemas` directory.

```bash
$ cd mozilla-pipeline-schemas
$ docker run -v "$(pwd)"/schemas:/app/resources/schemas -it edge-validator
```

## User Guide
## API

### Generic Ingestion

The generic ingestion specification provides enough context to map the ping to a schema.

The _namespace_ distinguishes
different data collection systems from each other. Telemetry is the largest consumer of the ingestion system to date.
The _document type_ differentiates messages in the ingestion pipeline. For example, the schemas of the main and crash
pings share little overlap. The _document version_ allows for versioning between documents. Finally, the _document id_
is used to check for duplicates. This is validated in the running pipeline, but not supported here.

```
POST /submit/<namespace>/<doctype>/<docversion/[<docid>]
```

The schemas are mounted under the application directory `/app/resources/schemas` with the following convention:

```
/schemas/<NAMESPACE>/<DOCTYPE>.<DOCVERSION>.schema.json
```

The following tree shows a subset of the resource directory.

```
/app/resources
└── schemas
    ├── telemetry
    │   ├── anonymous
    │   │   └── anonymous.4.schema.json
    │   ├── core
    │   │   ├── core.1.schema.json
    │   │   ├── core.2.schema.json
    │   │   ├── core.3.schema.json
    │   │   ├── core.4.schema.json
    │   │   ├── core.5.schema.json
    │   │   ├── core.6.schema.json
    │   │   ├── core.7.schema.json
    │   │   ├── core.8.schema.json
    │   │   └── core.9.schema.json
    │   ├── crash
    │   │   └── crash.4.schema.json
    │   ├── main
    │   │   └── main.4.schema.json
    │   └─── ...
    │   │   ├── ...
    │   │   ├── ...
    │   │   └── ...
    └── testing
        └── test
            └── test.1.schema.json
```

### Telemetry Ingestion

The edge-validator implements the Edge Server [POST request
specification](https://docs.telemetry.mozilla.org/concepts/pipeline/http_edge_spec.html#postput-request) for Firefox
Telemetry. The validator will reroute the request as a generic ingestion request.

```
POST /submit/<namespace>/<docid>/<appName>/<appVersion>/<appUpdateChannel>/<appBuildId>
```

### Installation

```bash
# clone and set the working directory
$ git clone https://github.com/acmiyaguchi/edge-validator.git
$ cd edge-validator

# make sure that the system pip is up to date
$ pip install --user --upgrade pip

# install pipenv for managing the application environment
$ pip install --user pipenv

# bootstrap for test/report/serve
$ make sync
```

### Serving
#### serving via docker host (recommended)

```bash
$ docker --version          # ensure that docker is installed
$ make build                # build the container
$ make serve                # start the service on localhost:8000
```

#### serving via local host
The docker host automates the following bootstrap process. `pipenv` should be installed on the host system. 

```bash
$ pipenv shell              # enter the application environment
$ pipenv sync               # update the environment
$ flask run --port 8000     # run the application
```

### Running tests

Unit tests do not require any dependencies and can be run out of the box. The sync command will
copy the test resources into the application resource folder.
```bash
$ make sync
$ make test
```

An integration report gives a performance report based on sampled data. Make sure that
aws is set up correctly.

```bash
# Run using the local app context
$ make report

# Run using the docker host
$ EXTERNAL=1 PORT=800 make report
```
