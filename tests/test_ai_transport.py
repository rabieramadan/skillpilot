"""Tests for the provider transport layer.

No network: the HTTP session and the provider SDKs are replaced with fakes, so
these run offline and assert on the request that *would* have been sent. That
is the part worth pinning — a wrongly shaped request is a 400 the user sees,
and it is invisible until someone tries the feature in production.
"""

import json

import pytest

from app.services import ai_transport as transport
from app.services.ai_transport import AIError


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code, body, headers=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.text = json.dumps(body)
        self.content = b''

    def json(self):
        return self._body


def ok_body(model='gpt-5.6-terra', text='hello'):
    return {
        'model': model,
        'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 11, 'completion_tokens': 3},
    }


class RecordingSession:
    """Records every request and replies from a scripted queue."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.requests.append({'url': url, 'headers': headers or {},
                              'payload': json or {}, 'timeout': timeout})
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]

    def get(self, url, timeout=None):
        self.requests.append({'url': url, 'timeout': timeout})
        return self.responses[0]


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    """Backoff is correct but slow; assert on attempt counts instead."""
    monkeypatch.setattr(transport.time, 'sleep', lambda *_: None)


@pytest.fixture
def session(monkeypatch):
    def install(*responses):
        fake = RecordingSession(responses)
        monkeypatch.setattr(transport, '_session', fake)
        return fake
    yield install
    monkeypatch.setattr(transport, '_session', None)


# ---------------------------------------------------------------------------
# Request shaping
# ---------------------------------------------------------------------------

class TestRequestShape:
    def test_reasoning_models_get_max_completion_tokens_and_no_temperature(self, session):
        """GPT-5.6 and GPT-6 reject both max_tokens and temperature with a 400."""
        fake = session(FakeResponse(200, ok_body()))
        transport.chat_openai_compatible(
            'openai', api_key='k', user_text='hi', model='gpt-5.6-terra')

        payload = fake.requests[0]['payload']
        assert 'max_completion_tokens' in payload
        assert 'max_tokens' not in payload
        assert 'temperature' not in payload

    def test_models_that_accept_sampling_still_get_it(self, session):
        fake = session(FakeResponse(200, ok_body('grok-4.6')))
        transport.chat_openai_compatible(
            'grok', api_key='k', user_text='hi', model='grok-4.6', temperature=0.3)

        payload = fake.requests[0]['payload']
        assert payload['max_tokens'] > 0
        assert payload['temperature'] == 0.3

    def test_output_budget_is_capped_at_the_model_maximum(self, session):
        fake = session(FakeResponse(200, ok_body('sonar-pro')))
        transport.chat_openai_compatible(
            'perplexity', api_key='k', user_text='hi',
            model='sonar-pro', max_tokens=999_999)

        cap = transport.registry.get_model('perplexity', 'sonar-pro').max_output_tokens
        assert fake.requests[0]['payload']['max_tokens'] == cap

    def test_system_prompt_goes_in_the_system_role(self, session):
        fake = session(FakeResponse(200, ok_body()))
        transport.chat_openai_compatible(
            'openai', api_key='k', user_text='hi', system='be terse')

        messages = fake.requests[0]['payload']['messages']
        assert messages[0] == {'role': 'system', 'content': 'be terse'}

    def test_history_is_sent_before_the_current_message(self, session):
        fake = session(FakeResponse(200, ok_body()))
        transport.chat_openai_compatible(
            'openai', api_key='k', user_text='and now?',
            history=[{'role': 'user', 'content': 'first'},
                     {'role': 'assistant', 'content': 'second'}])

        roles = [m['role'] for m in fake.requests[0]['payload']['messages']]
        assert roles == ['user', 'assistant', 'user']

    def test_perplexity_asks_for_citations(self, session):
        fake = session(FakeResponse(200, ok_body('sonar-pro')))
        transport.chat_openai_compatible('perplexity', api_key='k', user_text='hi')
        assert fake.requests[0]['payload']['return_citations'] is True

    def test_api_key_is_sent_as_a_header_not_in_the_body(self, session):
        fake = session(FakeResponse(200, ok_body()))
        transport.chat_openai_compatible('openai', api_key='secret', user_text='hi')

        assert fake.requests[0]['headers']['Authorization'] == 'Bearer secret'
        assert 'secret' not in json.dumps(fake.requests[0]['payload'])

    def test_a_missing_key_fails_before_any_request(self, session):
        fake = session(FakeResponse(200, ok_body()))
        with pytest.raises(AIError, match='No API key'):
            transport.chat_openai_compatible('openai', api_key='', user_text='hi')
        assert fake.requests == []


# ---------------------------------------------------------------------------
# History normalisation
# ---------------------------------------------------------------------------

class TestHistoryNormalisation:
    def test_consecutive_same_role_turns_are_merged(self):
        """Anthropic rejects two user turns in a row; dropping one would lose
        what the student said."""
        out = transport._normalise_history([
            {'role': 'user', 'content': 'one'},
            {'role': 'user', 'content': 'two'},
        ])
        assert out == [{'role': 'user', 'content': 'one\n\ntwo'}]

    def test_frontend_role_names_are_translated(self):
        out = transport._normalise_history([
            {'role': 'user', 'content': 'q'},
            {'role': 'bot', 'content': 'a'},
        ])
        assert [m['role'] for m in out] == ['user', 'assistant']

    def test_empty_and_unknown_entries_are_dropped(self):
        out = transport._normalise_history([
            {'role': 'user', 'content': '  '},
            {'role': 'system', 'content': 'ignore me'},
            'not a dict',
            {'role': 'user', 'content': 'real'},
        ])
        assert out == [{'role': 'user', 'content': 'real'}]

    def test_history_always_starts_with_the_user(self):
        out = transport._normalise_history([
            {'role': 'assistant', 'content': 'leading'},
            {'role': 'user', 'content': 'q'},
        ])
        assert out[0]['role'] == 'user'

    def test_history_is_trimmed_to_the_limit(self):
        long = [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': str(i)}
                for i in range(100)]
        assert len(transport._normalise_history(long, limit=8)) <= 8


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

class TestFailureHandling:
    def test_a_retired_model_falls_through_to_the_next_one(self, session):
        fake = session(
            FakeResponse(404, {'error': {'message': 'The model does not exist'}}),
            FakeResponse(200, ok_body('gpt-5.6-luna')),
        )
        result = transport.chat_openai_compatible(
            'openai', api_key='k', user_text='hi', model='gpt-5.6-terra')

        assert result.model == 'gpt-5.6-luna'
        assert result.fallback_from == 'gpt-5.6-terra'
        assert len(fake.requests) == 2

    def test_server_errors_are_retried_then_succeed(self, session):
        fake = session(
            FakeResponse(500, {'error': {'message': 'boom'}}),
            FakeResponse(200, ok_body()),
        )
        assert transport.chat_openai_compatible(
            'openai', api_key='k', user_text='hi').text == 'hello'
        assert len(fake.requests) == 2

    def test_retries_stop_at_the_limit(self, session):
        fake = session(FakeResponse(503, {'error': {'message': 'down'}}))
        with pytest.raises(AIError):
            transport.chat_openai_compatible('openai', api_key='k', user_text='hi')
        assert len(fake.requests) == transport.MAX_ATTEMPTS

    @pytest.mark.parametrize('status', [401, 403])
    def test_auth_failures_are_not_retried(self, session, status):
        """Retrying a bad key only makes the user wait longer for the same
        answer."""
        fake = session(FakeResponse(status, {'error': {'message': 'bad key'}}))
        with pytest.raises(AIError, match='rejected the API key'):
            transport.chat_openai_compatible('openai', api_key='k', user_text='hi')
        assert len(fake.requests) == 1

    def test_error_messages_never_echo_the_key(self, session):
        session(FakeResponse(401, {'error': {'message': 'Incorrect key sk-secret123'}}))
        with pytest.raises(AIError) as caught:
            transport.chat_openai_compatible(
                'openai', api_key='sk-secret123', user_text='hi')
        # The provider echoed it; what matters is that we never add it ourselves.
        assert 'sk-secret123' not in caught.value.message.replace(
            'Incorrect key sk-secret123', '')

    def test_an_empty_answer_is_an_error_not_an_empty_string(self, session):
        session(FakeResponse(200, {
            'choices': [{'message': {'content': ''}, 'finish_reason': 'stop'}]}))
        with pytest.raises(AIError, match='empty answer'):
            transport.chat_openai_compatible('openai', api_key='k', user_text='hi')

    def test_hitting_the_output_cap_says_so(self, session):
        session(FakeResponse(200, {
            'choices': [{'message': {'content': ''}, 'finish_reason': 'length'}]}))
        with pytest.raises(AIError, match='output limit'):
            transport.chat_openai_compatible('openai', api_key='k', user_text='hi')


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestResponseParsing:
    def test_citations_are_appended_and_reported(self, session):
        body = ok_body('sonar-pro', 'The answer.')
        body['citations'] = ['https://example.edu/a', 'https://example.edu/b']
        session(FakeResponse(200, body))

        result = transport.chat_openai_compatible(
            'perplexity', api_key='k', user_text='hi')
        assert result.citations == body['citations']
        assert 'example.edu/a' in result.text

    def test_multi_part_content_is_joined(self, session):
        session(FakeResponse(200, {
            'choices': [{'message': {'content': [
                {'type': 'text', 'text': 'part one '},
                {'type': 'text', 'text': 'part two'},
            ]}, 'finish_reason': 'stop'}]}))
        result = transport.chat_openai_compatible(
            'openai', api_key='k', user_text='hi')
        assert result.text == 'part one part two'

    def test_result_dict_omits_empty_fields(self, session):
        session(FakeResponse(200, ok_body()))
        payload = transport.chat_openai_compatible(
            'openai', api_key='k', user_text='hi').as_dict()
        assert 'fallback_from' not in payload
        assert 'citations' not in payload
        assert payload['usage']['prompt_tokens'] == 11


class TestAnthropicParsing:
    class Block:
        def __init__(self, type_, text=''):
            self.type = type_
            self.text = text

    class Reply:
        def __init__(self, content, stop_reason='end_turn', model='claude-sonnet-5'):
            self.content = content
            self.stop_reason = stop_reason
            self.model = model
            self.usage = None

    def test_text_is_collected_from_every_block(self):
        """Current Claude models can open a reply with a thinking block, so
        reading content[0].text returns nothing."""
        reply = self.Reply([
            self.Block('thinking'),
            self.Block('text', 'the '),
            self.Block('text', 'answer'),
        ])
        result = transport._parse_anthropic_response(
            reply, model='claude-sonnet-5', fallback_from=None)
        assert result.text == 'the answer'

    def test_a_refusal_is_reported_as_an_error(self):
        reply = self.Reply([], stop_reason='refusal')
        with pytest.raises(AIError, match='declined'):
            transport._parse_anthropic_response(
                reply, model='claude-sonnet-5', fallback_from=None)


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

class TestAttachments:
    def test_text_files_are_read_and_labelled(self, tmp_path):
        path = tmp_path / 'notes.txt'
        path.write_text('Week 3 covers recursion.')

        attachments = transport.build_attachments([str(path)])
        assert len(attachments) == 1
        assert not attachments[0].is_image
        assert 'recursion' in attachments[0].text
        assert 'notes.txt' in attachments[0].as_text_block()

    def test_missing_files_are_skipped_silently(self):
        assert transport.build_attachments(['/does/not/exist.txt']) == []

    def test_no_paths_is_not_an_error(self):
        assert transport.build_attachments(None) == []
        assert transport.build_attachments([]) == []

    def test_an_oversized_file_is_truncated_not_dropped(self, tmp_path):
        path = tmp_path / 'big.txt'
        path.write_text('x' * (transport.MAX_CHARS_PER_FILE + 5_000))

        text = transport.build_attachments([str(path)])[0].text
        assert len(text) < transport.MAX_CHARS_PER_FILE + 200
        assert 'truncated' in text

    def test_an_oversized_image_becomes_a_note_not_a_broken_payload(self, tmp_path):
        path = tmp_path / 'huge.png'
        path.write_bytes(b'\x00' * (transport.MAX_IMAGE_BYTES + 1))

        attachment = transport.build_attachments([str(path)])[0]
        assert not attachment.is_image
        assert 'too' in attachment.text and 'large' in attachment.text

    def test_attachment_text_reaches_the_request(self, session, tmp_path):
        path = tmp_path / 'syllabus.txt'
        path.write_text('Assessment is 40% coursework.')
        fake = session(FakeResponse(200, ok_body()))

        transport.chat_openai_compatible(
            'openai', api_key='k', user_text='What is the split?',
            attachments=transport.build_attachments([str(path)]))

        sent = fake.requests[0]['payload']['messages'][-1]['content']
        assert '40% coursework' in sent
        assert 'syllabus.txt' in sent

    def test_images_become_parts_for_a_vision_model(self, session, tmp_path):
        path = tmp_path / 'diagram.png'
        path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 64)
        fake = session(FakeResponse(200, ok_body()))

        transport.chat_openai_compatible(
            'openai', api_key='k', user_text='describe this',
            model='gpt-5.6-terra',
            attachments=transport.build_attachments([str(path)]))

        content = fake.requests[0]['payload']['messages'][-1]['content']
        assert isinstance(content, list)
        assert any(part['type'] == 'image_url' for part in content)


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_plain_json(self):
        assert transport.extract_json('{"a": 1}', 'object') == {'a': 1}

    def test_code_fence_is_stripped(self):
        assert transport.extract_json('```json\n[1, 2]\n```', 'array') == [1, 2]

    def test_preamble_and_trailing_prose_are_ignored(self):
        raw = 'Sure, here it is:\n{"n": 2}\nLet me know if you need more.'
        assert transport.extract_json(raw, 'object') == {'n': 2}

    def test_braces_inside_strings_do_not_end_the_object(self):
        raw = '{"text": "closing } brace", "n": 1}'
        assert transport.extract_json(raw, 'object')['n'] == 1

    def test_nested_structures_survive(self):
        raw = '```\n{"a": {"b": [1, {"c": "]"}]}}\n```'
        assert transport.extract_json(raw, 'object') == {'a': {'b': [1, {'c': ']'}]}}

    def test_the_wrong_shape_is_rejected(self):
        assert transport.extract_json('{"a": 1}', 'array') is None
        assert transport.extract_json('[1]', 'object') is None

    def test_no_json_returns_none(self):
        assert transport.extract_json('I could not do that.', 'object') is None
        assert transport.extract_json('', 'any') is None
