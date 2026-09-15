"""The AI chat has to stay put, and be reachable from the menu.

The chat is the tab the app opens on, but its menu entry was marked
instructor-or-admin-only and the whole "Artificial Intelligence" group with
it, while app.js pushed any student off the chat tab a moment after it
rendered. A student therefore saw the chat appear, saw it vanish, and had no
menu entry to get back to it -- whatever the administrator's AI chat switch
was set to.

The switch is now what decides: on, and the chat stays with a menu entry for
everyone who may use the app; off, and the tab and the entry are gone
everywhere, including the shared top menu used by the standalone pages.
"""

import pathlib

import pytest

from app.models import KeyValueSetting, User, db


@pytest.fixture
def switch(app):
    """Set the administrator's AI chat switch."""
    def _set(hidden):
        with app.app_context():
            row = KeyValueSetting.query.filter_by(key='ai_chat_hidden').first()
            if row is None:
                row = KeyValueSetting(key='ai_chat_hidden',
                                      value='1' if hidden else '0')
                db.session.add(row)
            else:
                row.value = '1' if hidden else '0'
            db.session.commit()
    return _set


@pytest.fixture
def signed_in(app, client):
    def _login(role='student'):
        with app.app_context():
            user = User.query.filter_by(username=f'vis_{role}').first()
            if user is None:
                user = User(username=f'vis_{role}', full_name='V',
                            email=f'vis_{role}@test.local', role=role,
                            password_hash='x')
                db.session.add(user)
                db.session.commit()
            user_id = user.id
        with client.session_transaction() as s:
            s.update(user_id=user_id, role=role, logged_in=True,
                     is_admin=role in ('admin', 'superadmin'))
        return user_id
    return _login


def page(client):
    response = client.get('/app/')
    assert response.status_code == 200, response.status_code
    return response.get_data(as_text=True)


class TestTheSwitchReachesThePage:
    def test_the_page_says_the_chat_is_on(self, client, signed_in, switch):
        signed_in('student')
        switch(hidden=False)
        html = page(client)
        assert 'window.SKP_AI_CHAT_ENABLED = true' in html
        assert '#chat-tab { display: none' not in html

    def test_the_page_says_the_chat_is_off(self, client, signed_in, switch):
        signed_in('student')
        switch(hidden=True)
        html = page(client)
        assert 'window.SKP_AI_CHAT_ENABLED = false' in html
        assert '#chat-tab { display: none !important; }' in html
        assert '[data-testid="menu-ai-chat"] { display: none !important; }' in html

    def test_an_untouched_switch_leaves_the_chat_on(self, client, signed_in):
        """No row in the settings table means nobody has switched it off."""
        signed_in('student')
        assert 'window.SKP_AI_CHAT_ENABLED = true' in page(client)


class TestTheMenuEntryIsNotRoleLocked:
    def test_the_chat_entry_is_not_instructor_only(self):
        """It was instructor-or-admin-only, so no student could reach it."""
        import re

        html = pathlib.Path('templates/index.html').read_text(encoding='utf-8')
        button = re.search(
            r'<button[^>]*data-testid="menu-ai-chat"[^>]*>', html)
        assert button, 'the chat menu button is gone'
        assert 'instructor-or-admin-only' not in button.group(0)
        assert 'ai-chat-item' in button.group(0)

    def test_the_stylesheet_hides_it_until_the_switch_is_read(self):
        """Hidden by default, shown by app.js -- so it cannot flash up and
        then disappear."""
        css = pathlib.Path('static/css/advanced.css').read_text(encoding='utf-8')
        assert '.menu-item.ai-chat-item { display: none; }' in css
        assert '.menu-item.ai-chat-item.role-visible { display: flex; }' in css

    def test_students_are_no_longer_pushed_off_the_chat(self):
        source = pathlib.Path('static/js/app.js').read_text(encoding='utf-8')
        block = source[source.index('staffOnlyTabs'):]
        block = block[:block.index('showTab')]
        assert "'chat'" not in block.split('if (!this.aiChatEnabled())')[0], \
            'the chat must only be off-limits when the switch says so'
        assert 'aiChatEnabled()' in block

    def test_a_group_is_shown_when_it_still_holds_something(self):
        """The AI group carried its own role class and hid the chat entry
        with it."""
        source = pathlib.Path('static/js/app.js').read_text(encoding='utf-8')
        assert 'syncMenuGroupVisibility' in source


class TestTheSharedTopMenu:
    """The admin pages and every standalone page use it."""

    def test_it_offers_the_chat_when_the_switch_is_on(self, client, signed_in,
                                                      switch):
        signed_in('superadmin')
        switch(hidden=False)
        html = client.get('/admin/dashboard').get_data(as_text=True)
        assert 'data-testid="menu-ai-chat"' in html

    def test_it_drops_the_chat_when_the_switch_is_off(self, client, signed_in,
                                                      switch):
        """It used to keep offering a link to a chat that was switched off."""
        signed_in('superadmin')
        switch(hidden=True)
        html = client.get('/admin/dashboard').get_data(as_text=True)
        assert 'data-testid="menu-ai-chat"' not in html

    def test_the_other_ai_entries_are_untouched(self, client, signed_in,
                                                switch):
        signed_in('superadmin')
        switch(hidden=True)
        html = client.get('/admin/dashboard').get_data(as_text=True)
        assert 'data-testid="menu-ai-tools-suite"' in html


class TestTheAdminSwitchItself:
    def test_an_admin_can_read_and_change_it(self, client, signed_in):
        signed_in('superadmin')

        assert client.get(
            '/admin/api/settings/ai-chat-visibility').get_json()['hidden'] is False

        response = client.post('/admin/api/settings/ai-chat-visibility',
                               json={'hidden': True})
        assert response.status_code == 200
        assert response.get_json()['hidden'] is True
        assert client.get(
            '/admin/api/settings/ai-chat-visibility').get_json()['hidden'] is True

    def test_a_student_cannot_change_it(self, client, signed_in):
        signed_in('student')
        response = client.post('/admin/api/settings/ai-chat-visibility',
                               json={'hidden': True})
        assert response.status_code == 403


class TestTheChatIsUsableOnArrival:
    def test_a_provider_is_selected_without_clicking(self):
        """Nothing was selected until a card was clicked, so opening the chat
        and typing did nothing: sendMessage() bails with no model set."""
        source = pathlib.Path('static/js/app.js').read_text(encoding='utf-8')
        assert 'selectDefaultModel()' in source
        block = source[source.index('selectDefaultModel() {'):]
        block = block[:block.index('\n    selectModel(')]
        assert 'has_api_key' in block, 'must not preselect a provider with no key'
        assert "kind !== 'image'" in block, \
            'a question should not be answered with a picture by default'
