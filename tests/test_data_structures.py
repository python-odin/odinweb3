import pytest

from odinweb3.data_structures import (
    Status,
    DefaultResource,
    HttpResponse
)


def test_default_resource():
    # Creating a DefaultResource creates itself!
    assert DefaultResource is DefaultResource()


class TestHttpResponse(object):
    @pytest.mark.parametrize('args, body, status, headers', (
        ((Status.NOT_FOUND, None), Status.NOT_FOUND.description, Status.NOT_FOUND.value, {}),
        ((Status.PROCESSING, None), Status.PROCESSING.phrase, Status.PROCESSING.value, {}),
        ((Status.NOT_FOUND, {'foo': 1}), Status.NOT_FOUND.description, Status.NOT_FOUND.value, {'foo': 1}),
    ))
    def test_from_status(self, args, body, status, headers):
        target = HttpResponse.from_status(*args)

        assert target.body == body
        assert target.status == status
        assert target.headers == headers

    @pytest.mark.parametrize('args, body, status, headers', (
        (('foo',), 'foo', 200, {}),
        (('foo', Status.NOT_FOUND), 'foo', 404, {}),
        (('foo', 400), 'foo', 400, {}),
        (('foo', Status.NOT_FOUND, {'foo': 1}), 'foo', 404, {'foo': 1}),
    ))
    def test_init(self, args, body, status, headers):
        target = HttpResponse(*args)

        assert target.body == body
        assert target.status == status
        assert target.headers == headers

    def test_get(self):
        target = HttpResponse.from_status(Status.OK, {'foo': '1'})

        assert target['foo'] == '1'

    def test_set(self):
        target = HttpResponse.from_status(Status.OK, {'foo': '1'})
        target['foo'] = '2'

        assert target.headers == {'foo': '2'}

    def test_set_content_type(self):
        target = HttpResponse.from_status(Status.OK)
        target.content_type = 'text/html'

        assert target.headers == {'Content-Type': 'text/html'}
