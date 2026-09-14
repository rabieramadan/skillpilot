"""Phase 2/3 — Student & teacher AI tools (`/api/ai-tools/*`).

These cover only the auth surface; actually invoking external LLM APIs
is out of scope for the suite.
"""


def test_list_requires_login(client):
    r = client.get('/api/ai-tools/list')
    assert r.status_code == 401


def test_list_returns_role_scoped_tools(client, login_as):
    login_as('student')
    r = client.get('/api/ai-tools/list')
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert body['role'] == 'student'
    assert isinstance(body['tools'], list)


def test_all_tools_requires_admin(client, login_as):
    login_as('student')
    r = client.get('/api/ai-tools/all')
    assert r.status_code == 403


def test_all_tools_admin_ok(client, login_as):
    login_as('admin')
    r = client.get('/api/ai-tools/all')
    assert r.status_code == 200
    assert 'tools' in r.get_json()


def test_execute_requires_login(client):
    r = client.post('/api/ai-tools/execute', json={'tool_id': 'x'})
    assert r.status_code == 401


def test_execute_requires_tool_id(client, login_as):
    login_as('student')
    r = client.post('/api/ai-tools/execute', json={})
    assert r.status_code == 400


def test_execute_blocks_tool_outside_role(client, login_as):
    login_as('student')
    # lesson_planner is teacher-only — students must be refused.
    r = client.post('/api/ai-tools/execute',
                    json={'tool_id': 'lesson_planner', 'params': {}})
    assert r.status_code == 403


def test_lesson_planner_blocks_students(client, login_as):
    login_as('student')
    r = client.post('/api/ai-tools/lesson-planner', json={'topic': 'AI'})
    assert r.status_code == 403


def test_question_generator_blocks_students(client, login_as):
    login_as('student')
    r = client.post('/api/ai-tools/question-generator', json={'topic': 'AI'})
    assert r.status_code == 403
