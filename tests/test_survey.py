"""Phase 1 — Entry survey, exit exam, certificates (`/api/survey/*`).

The survey blueprint persists state to JSON files in the working
directory. Tests redirect those paths to a tmp_path so the suite never
touches real data.
"""
import json
import os

import pytest


@pytest.fixture
def survey_tmpdir(tmp_path, monkeypatch):
    """Redirect every survey JSON path to a fresh tmp directory."""
    from app.routes import survey as survey_mod

    surveys_dir = tmp_path / 'surveys'
    exit_dir = tmp_path / 'exit_exams'
    surveys_dir.mkdir()
    exit_dir.mkdir()

    questions = {'questions': [
        {
            'id': 1,
            'question': 'Is prompt engineering useful?',
            'type': 'true_false',
            'options': ['True', 'False'],
            'correct_answer': 'True',
        },
        {
            'id': 2,
            'question': 'Are LLMs deterministic by default?',
            'type': 'true_false',
            'options': ['True', 'False'],
            'correct_answer': 'False',
        },
    ]}
    qpath = tmp_path / 'survey_questions.json'
    qpath.write_text(json.dumps(questions))

    exit_qpath = tmp_path / 'exit_exam_questions.json'
    exit_qpath.write_text(json.dumps({'questions': questions['questions']}))

    monkeypatch.setattr(survey_mod, 'SURVEY_DATA_FILE',
                        str(tmp_path / 'users_survey_data.json'))
    monkeypatch.setattr(survey_mod, 'SURVEY_QUESTIONS_FILE', str(qpath))
    monkeypatch.setattr(survey_mod, 'EXIT_EXAM_DATA_FILE',
                        str(tmp_path / 'users_exit_exam_data.json'))
    monkeypatch.setattr(survey_mod, 'EXIT_EXAM_QUESTIONS_FILE', str(exit_qpath))
    monkeypatch.setattr(survey_mod, 'SURVEYS_DIR', str(surveys_dir))
    monkeypatch.setattr(survey_mod, 'EXIT_EXAMS_DIR', str(exit_dir))
    monkeypatch.setattr(survey_mod, 'CERTIFICATES_DIR',
                        str(tmp_path / 'certificates'))
    return tmp_path


# --- /questions ----------------------------------------------------------

def test_questions_public(client, survey_tmpdir):
    r = client.get('/api/survey/questions')
    assert r.status_code == 200
    body = r.get_json()
    assert len(body['questions']) == 2


def test_exit_exam_questions_public(client, survey_tmpdir):
    r = client.get('/api/survey/exit-exam/questions')
    assert r.status_code == 200
    assert isinstance(r.get_json()['questions'], list)


# --- /submit -------------------------------------------------------------

def test_submit_requires_login(client, survey_tmpdir):
    r = client.post('/api/survey/submit', json={'answers': []})
    assert r.status_code == 401


def test_submit_scores_answers(client, login_as, survey_tmpdir):
    login_as('student')
    r = client.post('/api/survey/submit',
                    json={'answers': ['True', 'False']})
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert body['correct_count'] == 2
    assert body['percentage'] == 100.0
    assert body['pass_status'] == 'passed'
    assert body['certificate_status'] == 'pending'

    # Persisted to redirected file
    data = json.loads((survey_tmpdir / 'users_survey_data.json').read_text())
    assert len(data['users']) == 1


def test_submit_failing_score_marks_fail(client, login_as, survey_tmpdir):
    login_as('student')
    r = client.post('/api/survey/submit',
                    json={'answers': ['False', 'True']})
    body = r.get_json()
    assert body['percentage'] == 0.0
    assert body['pass_status'] == 'failed'
    assert body['certificate_status'] == 'fail'
    assert body['can_retake'] is True


# --- /exit-exam/submit ---------------------------------------------------

def test_exit_exam_submit_requires_login(client, survey_tmpdir):
    r = client.post('/api/survey/exit-exam/submit', json={'answers': []})
    assert r.status_code == 401


# --- /my-certificates ---------------------------------------------------

def test_my_certificates_requires_login(client, survey_tmpdir):
    r = client.get('/api/survey/my-certificates')
    assert r.status_code == 401


def test_my_certificates_for_logged_in_student(client, login_as, survey_tmpdir):
    login_as('student')
    r = client.get('/api/survey/my-certificates')
    # Endpoint should respond (200 with empty results) for a logged in user.
    assert r.status_code == 200


# --- /users (admin) -----------------------------------------------------

def test_users_listing_requires_admin(client, login_as, survey_tmpdir):
    login_as('student')
    r = client.get('/api/survey/users')
    assert r.status_code == 403


def test_users_listing_admin_ok(client, login_as, survey_tmpdir):
    login_as('admin')
    r = client.get('/api/survey/users')
    assert r.status_code == 200
    assert 'users' in r.get_json()


def test_force_certificate_requires_admin(client, login_as, survey_tmpdir):
    login_as('student')
    r = client.post('/api/survey/user/abc/force-certificate', json={})
    assert r.status_code == 403


def test_settings_get_public(client, survey_tmpdir):
    r = client.get('/api/survey/settings')
    assert r.status_code == 200
    body = r.get_json()
    assert 'survey_enabled' in body


def test_settings_put_admin(client, login_as, survey_tmpdir, monkeypatch, tmp_path):
    from app.routes import survey as survey_mod
    monkeypatch.setattr(survey_mod, 'SETTINGS_FILE',
                        str(tmp_path / 'admin_settings.json'))
    login_as('admin')
    r = client.put('/api/survey/settings', json={'survey_enabled': False})
    assert r.status_code == 200
    assert r.get_json()['settings']['survey_enabled'] is False
