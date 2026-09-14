"""Image generation has to be reachable from the chat, and the picture has
to actually appear.

Two things stopped it. The endpoint that fills the chat's model picker
filtered the image provider out, so there was no way to select it. And the
generated file was written to ``uploads/`` and handed back as
``/uploads/<name>``, but only ``/uploads/materials/`` had a route -- so even
when an image was produced it came back 404 and rendered as a broken picture.
"""

import os

import pytest

from app.models import User, db


@pytest.fixture
def fake_image(monkeypatch):
    """Stand in for the one HTTP call, so no picture is paid for."""
    png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 40

    def generate(**kwargs):
        return {'image_bytes': png,
                'model': kwargs.get('model') or 'gpt-image-2',
                'revised_prompt': 'A watercolour of Nizwa fort at sunrise.'}

    monkeypatch.setattr('app.services.ai_transport.generate_image', generate)
    return png


@pytest.fixture
def signed_in(app, client):
    def _login(role='student'):
        with app.app_context():
            user = User.query.filter_by(username=f'chat_{role}').first()
            if user is None:
                user = User(username=f'chat_{role}', full_name='C',
                            email=f'chat_{role}@test.local', role=role,
                            password_hash='x')
                db.session.add(user)
                db.session.commit()
            user_id = user.id
        with client.session_transaction() as s:
            s.update(user_id=user_id, role=role, logged_in=True)
        return user_id
    return _login


def cleanup(path):
    if path and os.path.exists(path):
        os.remove(path)


class TestThePickerOffersImageGeneration:
    def test_the_image_provider_is_listed(self, client):
        models = client.get('/api/admin/models').get_json()['models']
        assert 'images' in models, \
            'image generation was filtered out of the chat picker'

    def test_it_is_marked_as_an_image_provider(self, client):
        entry = client.get('/api/admin/models').get_json()['models']['images']
        assert entry['kind'] == 'image'
        assert entry['versions'], 'no image models offered'
        assert entry['default_version']

    def test_the_chat_providers_are_still_chat(self, client):
        models = client.get('/api/admin/models').get_json()['models']
        assert models['claude']['kind'] == 'chat'
        assert models['openai']['kind'] == 'chat'

    def test_every_catalogued_provider_is_offered(self, client):
        """Nothing the platform can call should be hidden from the picker."""
        from app.services import model_registry as registry

        models = client.get('/api/admin/models').get_json()['models']
        assert set(models) == set(registry.list_providers())

    def test_each_entry_carries_a_readable_label(self, client):
        models = client.get('/api/admin/models').get_json()['models']
        assert models['images']['label'] == 'OpenAI Images'
        for name, entry in models.items():
            assert entry['label'], f'{name} has no label to show'


class TestGeneratingAnImageThroughTheChat:
    def test_the_chat_returns_an_image(self, client, signed_in, fake_image):
        signed_in()
        response = client.post('/api/chat/images', data={
            'message': 'a watercolour of Nizwa fort at sunrise',
            'version': 'gpt-image-2', 'language': 'en',
            'conversation_history': '[]'})
        assert response.status_code == 200
        body = response.get_json()
        assert 'error' not in body, body
        assert body['image_url'].startswith('/uploads/')
        assert body['model'] == 'gpt-image-2'
        cleanup(body.get('image_path'))

    def test_the_image_can_actually_be_fetched(self, client, signed_in,
                                               fake_image):
        """The whole point: it has to render, not 404."""
        signed_in()
        body = client.post('/api/chat/images', data={
            'message': 'a cat', 'version': 'gpt-image-2', 'language': 'en',
            'conversation_history': '[]'}).get_json()

        served = client.get(body['image_url'])
        assert served.status_code == 200, \
            f"{body['image_url']} came back {served.status_code}: broken image"
        assert served.data[:8] == fake_image[:8]
        cleanup(body.get('image_path'))

    def test_the_retired_name_still_works(self, client, signed_in,
                                          fake_image):
        """Chat sessions saved before the rename still say 'dalle'."""
        signed_in()
        body = client.post('/api/chat/dalle', data={
            'message': 'a cat', 'version': '', 'language': 'en',
            'conversation_history': '[]'}).get_json()
        assert body.get('image_url'), body
        cleanup(body.get('image_path'))

    def test_a_provider_failure_is_reported_not_crashed(self, client,
                                                        signed_in,
                                                        monkeypatch):
        from app.services.ai_transport import AIError

        def boom(**kwargs):
            raise AIError('the image service refused')

        monkeypatch.setattr('app.services.ai_transport.generate_image', boom)
        signed_in()
        response = client.post('/api/chat/images', data={
            'message': 'a cat', 'version': '', 'language': 'en',
            'conversation_history': '[]'})
        assert response.status_code == 200
        assert 'refused' in response.get_json()['error']


class TestServingUploads:
    def test_a_signed_out_caller_is_refused(self, client, tmp_path):
        """uploads/ holds documents people attached to their own chats."""
        name = 'test_privacy_probe.txt'
        path = os.path.join('uploads', name)
        os.makedirs('uploads', exist_ok=True)
        with open(path, 'w') as handle:
            handle.write('someone else\'s document')
        try:
            response = client.get(f'/uploads/{name}')
            assert response.status_code == 401
        finally:
            cleanup(path)

    def test_climbing_out_of_the_folder_is_refused(self, client, signed_in):
        signed_in()
        for attempt in ('/uploads/../config.yaml',
                        '/uploads/....//config.yaml'):
            response = client.get(attempt)
            assert response.status_code in (400, 401, 403, 404), \
                f'{attempt} returned {response.status_code}'
            assert b'api_keys' not in response.data

    def test_materials_are_still_served_by_their_own_route(self, app):
        """The new catch-all must not shadow the existing one."""
        adapter = app.url_map.bind('localhost')
        assert adapter.match('/uploads/materials/x.pdf')[0] == \
            'main.serve_material'
        assert adapter.match('/uploads/x.png')[0] == 'main.serve_upload'

    def test_a_missing_file_is_a_clean_404(self, client, signed_in):
        signed_in()
        assert client.get('/uploads/not_here_at_all.png').status_code == 404


class TestThePickerSaysWhatIsUsable:
    """"Active" has to mean "you can use this now"."""

    def test_the_endpoint_reports_key_presence_per_provider(self, client,
                                                            monkeypatch):
        from app.utils import api_key_helper

        monkeypatch.setattr(api_key_helper, '_from_environment', lambda p: None)
        monkeypatch.setattr(api_key_helper, '_from_database', lambda p: None)
        monkeypatch.setattr(api_key_helper, '_from_config_file',
                            lambda p: 'k' if p == 'claude' else None)

        models = client.get('/api/admin/models').get_json()['models']
        assert models['claude']['has_api_key'] is True
        assert models['bedrock']['has_api_key'] is False
        assert models['bedrock']['api_key_missing'] is True

    def test_the_screen_gates_on_the_key_not_just_the_flag(self):
        """A provider switched on in config.yaml but with no key was shown
        as Active, and failed the moment anyone sent a message."""
        import pathlib

        source = pathlib.Path('static/js/app.js').read_text(encoding='utf-8')
        block = source[source.index('renderModels()'):]
        block = block[:block.index('selectModel(')]
        assert 'has_api_key' in block, \
            'the picker must consider whether a key exists'
        assert "config.enabled \n" not in block
