from unittest.mock import patch
from middleware.project_context import project_context_middleware
from pydantic import ValidationError, BaseModel

class DummyReq:
    def __init__(self, params=None, headers=None):
        self.params = params or {}
        self.headers = headers or {}
        self.context = None
    def HttpResponse(self, body, status_code=200, mimetype=None):
        return {'body': body, 'status_code': status_code, 'mimetype': mimetype}

@patch('middleware.project_context.get_project_arn', return_value='arn:dummy')
@patch('middleware.project_context.logger')
def test_middleware_success(mock_logger, mock_get_arn):
    req = DummyReq(params={'project': 'test'}, headers={'correlation-id': 'cid'})
    called = {}
    def handler(r, *a, **k):
        called['called'] = True
        assert r.context['project'] == 'test'
        assert r.context['correlation_id'] == 'cid'
        assert r.context['arn'] == 'arn:dummy'
        return 'ok'
    wrapped = project_context_middleware(handler)
    result = wrapped(req)
    assert result == 'ok'
    assert called['called']
    mock_logger.info.assert_called()

@patch('middleware.project_context.get_project_arn', return_value='arn:dummy')
def test_middleware_missing_project(mock_get_arn):
    req = DummyReq(params={}, headers={})
    wrapped = project_context_middleware(lambda r: 'should not call')
    result = wrapped(req)
    assert result['status_code'] == 400
    assert 'Missing required query parameter' in result['body']


# Use a real ValidationError from a simple model for pydantic v2 compatibility
class DummyModel(BaseModel):
    x: int

@patch('middleware.project_context.logger')
@patch('middleware.project_context.get_project_arn')
def test_middleware_invalid_project(mock_get_arn, mock_logger):
    # Create a real ValidationError by trying to instantiate DummyModel with bad data
    try:
        DummyModel(x='not-an-int')
    except ValidationError as ve:
        validation_error = ve
    mock_get_arn.side_effect = validation_error
    req = DummyReq(params={'project': 'bad'}, headers={'correlation-id': 'cid'})
    wrapped = project_context_middleware(lambda r: 'should not call')
    result = wrapped(req)
    assert result['status_code'] == 400
    # The error message should mention 'type_error.integer' or similar
    assert 'type_error' in result['body'] or 'integer' in result['body'] or 'not-an-int' in result['body']
    mock_logger.error.assert_called()

@patch('middleware.project_context.get_project_arn', side_effect=Exception('fail'))
@patch('middleware.project_context.logger')
def test_middleware_arn_exception(mock_logger, mock_get_arn):
    req = DummyReq(params={'project': 'bad'}, headers={'correlation-id': 'cid'})
    wrapped = project_context_middleware(lambda r: 'should not call')
    result = wrapped(req)
    assert result['status_code'] == 500
    assert 'fail' in result['body']
    mock_logger.error.assert_called()
