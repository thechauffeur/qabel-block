import pytest
import tempfile
import os
import random
import string
import blockserver.backends.cache as cache_backends
from blockserver.backends import s3, dummy

from glinda.testing import services
from tornado.options import options


@pytest.fixture
def auth_token():
    return 'Token MAGICFARYDUST'


@pytest.fixture
def headers(auth_token):
    return {'Authorization': auth_token}


@pytest.yield_fixture
def testfile():
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(b'Dummy\n')
        yield temp.name
    os.remove(temp.name)


@pytest.fixture
def service_layer():
    return services.ServiceLayer()


@pytest.yield_fixture
def auth_server(service_layer):
    options.dummy_auth = False
    options.dummy_log = False
    dummy_acc = options.accountingserver
    auth = service_layer['auth']  # type: services.Service
    options.accountingserver = 'http://' + auth.host
    yield auth
    options.dummy_auth = True
    options.dummy_log = True
    options.accountingserver = dummy_acc


@pytest.fixture
def file_path():
    return '/test/' + ''.join(random.choice(string.ascii_lowercase + string.digits)
                          for _ in range(12))


@pytest.fixture
def auth_path(file_path):
    return '/api/v0/auth' + file_path


@pytest.fixture
def path(base_url, file_path):
    return base_url + '/api/v0/files' + file_path


@pytest.yield_fixture
def backend(request):
    switch_to = (request.param == 'dummy')
    before = options.dummy
    options.dummy = switch_to
    if options.dummy:
        from blockserver.backends import dummy
        dummy.files = {}
    yield
    options.dummy = before


@pytest.fixture
def cache(request):
    cache_backend = request.param
    if cache_backend == 'dummy':
        return cache_backends.DummyCache()
    if cache_backend == 'redis':
        redis = cache_backends.RedisCache(host='localhost', port='6379')
        redis.flush()
        return redis

@pytest.yield_fixture()
def transfer(request, cache):
    transfer_backend = request.param
    if transfer_backend == 'dummy':
        dummy.files = {}
        yield dummy.DummyTransfer(cache)
        dummy.files = {}
    if transfer_backend == 's3':
        yield s3.S3Transfer(cache)


def pytest_addoption(parser):
    parser.addoption("--dummy", action="store_true",
        help="run only with the dummy backend")
    parser.addoption("--dummy-cache", action="store_true",
                     help="run only with the dummy cache")


def pytest_generate_tests(metafunc):
    if 'backend' in metafunc.fixturenames:
        backends = ['dummy']
        if not metafunc.config.option.dummy:
            backends.append('s3')
        metafunc.parametrize("backend", backends, indirect=True)
    if 'transfer' in metafunc.fixturenames:
        backends = ['dummy']
        if not metafunc.config.option.dummy:
            backends.append('s3')
        metafunc.parametrize("transfer", backends, indirect=True)
    if 'cache' in metafunc.fixturenames:
        backends = ['dummy']
        if not metafunc.config.option.dummy_cache:
            backends.append('redis')
        metafunc.parametrize("cache", backends, indirect=True)
