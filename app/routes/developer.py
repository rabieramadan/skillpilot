"""Developer portal — self-service API key management + OpenAPI viewer.

Reuses the existing /api/v1/keys/* endpoints under the hood so this is
purely a presentation surface. Renders templates/developer_portal.html.
"""
from flask import Blueprint, render_template, session, redirect, url_for


developer_bp = Blueprint('developer', __name__, url_prefix='/developer')


@developer_bp.route('/')
def portal():
    if not session.get('logged_in'):
        return redirect(url_for('main.app_page'))
    return render_template('developer_portal.html')
