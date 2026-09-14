"""
SkillPilot v2 — Phase 8: Enterprise, compliance, accessibility & public API.

Mounted at:
  /api/v1/enterprise/*       organizations, members
  /api/v1/sso/*              SAML / OIDC configuration (metadata only)
  /api/v1/keys/*             API key management
  /api/v1/audit/*            audit log read API
  /api/v1/compliance/*       consent + data subject requests
  /api/v1/accessibility/*    accessibility profile + TTS request
  /api/v1/public/*           versioned public REST surface
  /api/v1/spec               OpenAPI 3.0 spec
"""
from datetime import datetime
import hashlib
import secrets

from flask import (
    Blueprint, jsonify, request, session, current_app, redirect, url_for,
)

from app.utils.decorators import (
    login_required, admin_required, superadmin_required,
)


enterprise_bp = Blueprint('enterprise_v2', __name__, url_prefix='/api/v1/enterprise')
sso_bp = Blueprint('sso_v2', __name__, url_prefix='/api/v1/sso')
keys_bp = Blueprint('keys_v2', __name__, url_prefix='/api/v1/keys')
audit_bp = Blueprint('audit_v2', __name__, url_prefix='/api/v1/audit')
compliance_bp = Blueprint('compliance_v2', __name__, url_prefix='/api/v1/compliance')
accessibility_bp = Blueprint('accessibility_v2', __name__, url_prefix='/api/v1/accessibility')
public_api_bp = Blueprint('public_api_v2', __name__, url_prefix='/api/v1/public')
spec_bp = Blueprint('spec_v2', __name__, url_prefix='/api/v1')


_SSO_PROTOCOLS = {'saml', 'oidc'}
_CONSENT_TYPES = {'tos', 'privacy', 'marketing', 'proctoring', 'parental', 'cookies'}
_DR_TYPES = {'export', 'erasure', 'rectification'}


def _record_audit(action, resource_type=None, resource_id=None, details=None,
                  severity='info'):
    """Append an audit event. Best-effort — never raises."""
    try:
        from app.models import db, AuditEvent
        ev = AuditEvent(
            actor_user_id=session.get('user_id'),
            action=action[:80],
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=(request.headers.get('User-Agent') or '')[:255],
            details=details or {},
            severity=severity,
        )
        db.session.add(ev); db.session.commit()
    except Exception:
        try:
            from app.models import db as _db
            _db.session.rollback()
        except Exception:
            pass


# ---------- Organizations -------------------------------------------------

@enterprise_bp.route('/organizations', methods=['POST'])
@superadmin_required
def org_create():
    try:
        from app.models import db, Organization
        data = request.get_json(silent=True) or {}
        if not data.get('code') or not data.get('name'):
            return jsonify({'error': 'code and name required'}), 400
        o = Organization(
            code=data['code'][:64], name=data['name'][:255],
            name_ar=data.get('name_ar'),
            domain=data.get('domain'),
            region=data.get('region', 'OM'),
            data_residency=data.get('data_residency', 'OM'),
        )
        db.session.add(o); db.session.commit()
        _record_audit('org.create', 'organization', o.id, {'code': o.code})
        return jsonify({'success': True, 'id': o.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@enterprise_bp.route('/organizations', methods=['GET'])
@admin_required
def org_list():
    from app.models import Organization
    rows = Organization.query.filter_by(is_active=True).all()
    return jsonify({'success': True, 'count': len(rows), 'organizations': [{
        'id': o.id, 'code': o.code, 'name': o.name, 'domain': o.domain,
        'region': o.region, 'data_residency': o.data_residency,
    } for o in rows]})


@enterprise_bp.route('/organizations/<oid>/members', methods=['POST'])
@superadmin_required
def org_add_member(oid):
    try:
        from app.models import db, OrganizationMember
        data = request.get_json(silent=True) or {}
        uid = data.get('user_id')
        if not uid:
            return jsonify({'error': 'user_id required'}), 400
        m = OrganizationMember(
            organization_id=oid, user_id=uid,
            org_role=data.get('org_role', 'member'),
        )
        db.session.add(m); db.session.commit()
        _record_audit('org.member_add', 'organization', oid, {'user_id': uid})
        return jsonify({'success': True, 'id': m.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- SSO (config only) ---------------------------------------------

@sso_bp.route('/configurations', methods=['POST'])
@superadmin_required
def sso_configure():
    try:
        from app.models import db, SsoConfiguration
        data = request.get_json(silent=True) or {}
        proto = data.get('protocol')
        org_id = data.get('organization_id')
        if proto not in _SSO_PROTOCOLS or not org_id:
            return jsonify({'error': 'organization_id and protocol (saml|oidc) required'}), 400
        cfg = SsoConfiguration(
            organization_id=org_id, protocol=proto,
            display_name=data.get('display_name'),
            enabled=bool(data.get('enabled', False)),
            saml_entity_id=data.get('saml_entity_id'),
            saml_sso_url=data.get('saml_sso_url'),
            saml_x509_cert=data.get('saml_x509_cert'),
            saml_attribute_map=data.get('saml_attribute_map') or {},
            oidc_issuer=data.get('oidc_issuer'),
            oidc_client_id=data.get('oidc_client_id'),
            oidc_redirect_uri=data.get('oidc_redirect_uri'),
            oidc_scopes=data.get('oidc_scopes', 'openid profile email'),
            just_in_time_provisioning=bool(data.get('just_in_time_provisioning', True)),
            default_role=data.get('default_role', 'student'),
        )
        # Encrypt OIDC client secret using the platform's Fernet helper.
        # Fail closed: if encryption is unavailable, refuse to store the secret.
        if data.get('oidc_client_secret'):
            try:
                from app.utils.encryption import encrypt_api_key
                cfg.oidc_client_secret_encrypted = encrypt_api_key(
                    data['oidc_client_secret']
                )
            except Exception as enc_err:
                return jsonify({
                    'error': 'Unable to securely store OIDC client secret',
                    'detail': str(enc_err),
                }), 500
        db.session.add(cfg); db.session.commit()
        _record_audit('sso.configure', 'sso_configuration', cfg.id, {'protocol': proto})
        return jsonify({'success': True, 'id': cfg.id,
                        'metadata_url': f'/api/v1/sso/{cfg.id}/metadata'}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@sso_bp.route('/configurations', methods=['GET'])
@admin_required
def sso_list():
    from app.models import SsoConfiguration
    rows = SsoConfiguration.query.all()
    return jsonify({'success': True, 'count': len(rows), 'configurations': [{
        'id': c.id, 'organization_id': c.organization_id, 'protocol': c.protocol,
        'display_name': c.display_name, 'enabled': c.enabled,
    } for c in rows]})


@sso_bp.route('/<cid>/metadata', methods=['GET'])
def sso_metadata(cid):
    """SP metadata endpoint (SAML) or discovery doc reference (OIDC)."""
    from app.models import SsoConfiguration
    cfg = SsoConfiguration.query.filter_by(id=cid).first()
    if not cfg:
        return jsonify({'error': 'not found'}), 404
    if cfg.protocol == 'oidc':
        return jsonify({
            'protocol': 'oidc',
            'issuer': cfg.oidc_issuer,
            'client_id': cfg.oidc_client_id,
            'redirect_uri': cfg.oidc_redirect_uri,
            'scopes': cfg.oidc_scopes,
        })
    sp_entity = f'{request.host_url.rstrip("/")}/api/v1/sso/{cid}'
    acs = f'{sp_entity}/acs'
    xml = f"""<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{sp_entity}">
  <SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="{acs}" index="1"/>
  </SPSSODescriptor>
</EntityDescriptor>"""
    return current_app.response_class(xml, mimetype='application/samlmetadata+xml')


# ---------- SSO real handshakes -------------------------------------------

def _sso_after_login_redirect():
    """Where to send the user after a successful SSO handshake.

    Constrains `next` to a same-origin, relative path (must start with `/`
    and must not start with `//` or contain a scheme/host) to prevent
    open-redirect abuse via crafted login links.
    """
    nxt = request.args.get('next') or '/'
    from urllib.parse import urlparse
    try:
        if (not nxt.startswith('/') or nxt.startswith('//')
                or urlparse(nxt).netloc or urlparse(nxt).scheme):
            return '/'
    except Exception:
        return '/'
    return nxt


def _login_user(uid, role):
    """Establish a Flask session for the JIT-provisioned/SSO user."""
    session.clear()
    session['user_id'] = uid
    session['role'] = role
    session.permanent = True


@sso_bp.route('/<cid>/login', methods=['GET'])
def sso_login(cid):
    """Begin an SSO handshake. For OIDC, returns/redirects to the IdP
    authorization endpoint. For SAML, redirects to the IdP SSO URL with a
    deflated AuthnRequest."""
    from app.models import SsoConfiguration
    cfg = SsoConfiguration.query.filter_by(id=cid).first()
    if not cfg or not cfg.enabled:
        return jsonify({'error': 'SSO configuration not found or disabled'}), 404

    if cfg.protocol == 'oidc':
        if not (cfg.oidc_issuer and cfg.oidc_client_id and cfg.oidc_redirect_uri):
            return jsonify({'error': 'OIDC configuration incomplete'}), 400
        try:
            from app.services.sso_service import oidc_build_auth_url
            state = secrets.token_urlsafe(24)
            nonce = secrets.token_urlsafe(16)
            verifier = secrets.token_urlsafe(48)
            session['_sso_oidc'] = {
                'cid': cid, 'state': state, 'nonce': nonce,
                'verifier': verifier,
                'next': _sso_after_login_redirect(),
            }
            url = oidc_build_auth_url(cfg, state=state, nonce=nonce,
                                       code_verifier=verifier)
            return redirect(url)
        except Exception as e:
            _record_audit('sso.oidc_init_failed', 'sso_configuration', cid,
                          {'error': str(e)}, severity='warning')
            return jsonify({'error': f'OIDC init failed: {e}'}), 502

    if cfg.protocol == 'saml':
        if not cfg.saml_sso_url:
            return jsonify({'error': 'SAML SSO URL not configured'}), 400
        try:
            from app.services.sso_service import saml_build_authn_redirect_url
            sp_entity = (cfg.saml_entity_id
                         or f'{request.host_url.rstrip("/")}/api/v1/sso/{cid}')
            acs = f'{request.host_url.rstrip("/")}/api/v1/sso/{cid}/acs'
            relay = secrets.token_urlsafe(16)
            url, req_id = saml_build_authn_redirect_url(
                cfg, sp_entity_id=sp_entity, acs_url=acs, relay_state=relay,
            )
            session['_sso_saml'] = {
                'cid': cid, 'relay': relay,
                'request_id': req_id,
                'sp_entity_id': sp_entity,
                'acs_url': acs,
                'next': _sso_after_login_redirect(),
            }
            return redirect(url)
        except Exception as e:
            _record_audit('sso.saml_init_failed', 'sso_configuration', cid,
                          {'error': str(e)}, severity='warning')
            return jsonify({'error': f'SAML init failed: {e}'}), 502

    return jsonify({'error': f'unsupported protocol {cfg.protocol}'}), 400


@sso_bp.route('/<cid>/callback', methods=['GET', 'POST'])
def sso_oidc_callback(cid):
    """OIDC redirect URI: exchanges the authorization code for tokens,
    verifies the id_token, and provisions the user just-in-time."""
    from app.models import SsoConfiguration
    cfg = SsoConfiguration.query.filter_by(id=cid).first()
    if not cfg or cfg.protocol != 'oidc':
        return jsonify({'error': 'OIDC configuration not found'}), 404
    if not cfg.enabled:
        return jsonify({'error': 'OIDC configuration is disabled'}), 403
    pending = session.get('_sso_oidc') or {}
    if pending.get('cid') != cid:
        return jsonify({'error': 'no pending OIDC handshake'}), 400
    state = request.values.get('state')
    code = request.values.get('code')
    err = request.values.get('error')
    if err:
        return jsonify({'error': f'IdP returned error: {err}'}), 400
    if not code or state != pending.get('state'):
        return jsonify({'error': 'invalid state or missing code'}), 400
    try:
        from app.services.sso_service import (
            oidc_exchange_code, jit_provision_user,
        )
        result = oidc_exchange_code(cfg, code=code,
                                     code_verifier=pending['verifier'])
        claims = result['claims']
        if claims.get('nonce') and pending.get('nonce') \
                and claims.get('nonce') != pending['nonce']:
            return jsonify({'error': 'OIDC nonce mismatch'}), 400
        user_info = jit_provision_user(
            cfg,
            email=claims.get('email') or claims.get('preferred_username'),
            full_name=claims.get('name')
                       or claims.get('preferred_username') or claims.get('email'),
            external_id=claims.get('sub'),
        )
        _login_user(user_info['user_id'], user_info['role'])
        _record_audit('sso.oidc_login', 'user', user_info['user_id'],
                      {'cid': cid, 'created': user_info['created'],
                       'verified': claims.get('_verified', False)})
        session.pop('_sso_oidc', None)
        return redirect(pending.get('next') or '/')
    except Exception as e:
        _record_audit('sso.oidc_failed', 'sso_configuration', cid,
                      {'error': str(e)}, severity='warning')
        return jsonify({'error': str(e)}), 502


@sso_bp.route('/<cid>/acs', methods=['POST'])
def sso_saml_acs(cid):
    """SAML AssertionConsumerService — accepts SAMLResponse from the IdP.

    Fail-closed:
      * The SsoConfiguration row must exist, be the SAML protocol, AND be
        explicitly `enabled`.
      * The browser must carry a server-issued pending handshake in its
        session (`_sso_saml`) that matches both `cid` and `RelayState`.
        Unsolicited POSTs are rejected.
      * The SAMLResponse must pass cryptographic signature verification
        against the configured x509 cert. If signxml/cert are unavailable
        the request is rejected — we never trust unverified assertions.
    """
    from app.models import SsoConfiguration
    cfg = SsoConfiguration.query.filter_by(id=cid).first()
    if not cfg or cfg.protocol != 'saml':
        return jsonify({'error': 'SAML configuration not found'}), 404
    if not cfg.enabled:
        return jsonify({'error': 'SAML configuration is disabled'}), 403

    pending = session.get('_sso_saml') or {}
    if pending.get('cid') != cid:
        _record_audit('sso.saml_unsolicited', 'sso_configuration', cid,
                      {'reason': 'no pending handshake'}, severity='warning')
        return jsonify({'error': 'no pending SAML handshake'}), 400
    posted_relay = request.form.get('RelayState') or request.values.get('RelayState')
    if not posted_relay or posted_relay != pending.get('relay'):
        _record_audit('sso.saml_relay_mismatch', 'sso_configuration', cid,
                      {}, severity='warning')
        return jsonify({'error': 'RelayState mismatch'}), 400

    saml_resp = request.form.get('SAMLResponse')
    if not saml_resp:
        return jsonify({'error': 'SAMLResponse missing'}), 400
    if not cfg.saml_x509_cert:
        _record_audit('sso.saml_no_cert', 'sso_configuration', cid,
                      {}, severity='error')
        return jsonify({
            'error': 'SAML signature verification not available: no x509 '
                     'cert configured for this IdP',
        }), 503
    from app.services.sso_service import (
        saml_parse_response, jit_provision_user, SamlVerificationError,
    )
    try:
        parsed = saml_parse_response(
            saml_resp, cfg,
            expected_request_id=pending.get('request_id'),
            expected_audience=pending.get('sp_entity_id'),
            expected_acs_url=pending.get('acs_url'),
        )
    except SamlVerificationError as e:
        # Fail-closed: signature/replay-protection failure. Never trust the
        # assertion. Audit with the specific reason for SOC review.
        _record_audit('sso.saml_signature_invalid', 'sso_configuration',
                      cid, {'reason': str(e)}, severity='error')
        return jsonify({
            'error': 'SAML assertion rejected',
            'reason': str(e),
        }), 401
    try:
        attrs = parsed.get('attributes') or {}
        amap = cfg.saml_attribute_map or {}
        email = (attrs.get(amap.get('email', 'email'))
                 or attrs.get('mail') or attrs.get('emailAddress')
                 or parsed.get('name_id'))
        full_name = (attrs.get(amap.get('name', 'name'))
                     or attrs.get('displayName') or attrs.get('cn'))
        user_info = jit_provision_user(
            cfg, email=email, full_name=full_name,
            external_id=parsed.get('name_id'),
        )
        _login_user(user_info['user_id'], user_info['role'])
        _record_audit('sso.saml_login', 'user', user_info['user_id'],
                      {'cid': cid, 'created': user_info['created'],
                       'verified': parsed.get('_verified', False)})
        nxt = (session.pop('_sso_saml', {}) or {}).get('next') or '/'
        return redirect(nxt)
    except Exception as e:
        _record_audit('sso.saml_failed', 'sso_configuration', cid,
                      {'error': str(e)}, severity='warning')
        return jsonify({'error': str(e)}), 502


# ---------- API keys ------------------------------------------------------

def _hash_key(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


@keys_bp.route('', methods=['POST'])
@admin_required
def key_create():
    try:
        from app.models import db, ApiKey
        data = request.get_json(silent=True) or {}
        if not data.get('name'):
            return jsonify({'error': 'name required'}), 400
        scopes = data.get('scopes') or ['read:public']
        if not isinstance(scopes, list):
            return jsonify({'error': 'scopes must be a list'}), 400
        raw = 'sp_' + secrets.token_urlsafe(32)
        prefix = raw[:8]
        k = ApiKey(
            organization_id=data.get('organization_id'),
            user_id=session.get('user_id'),
            name=data['name'][:120],
            prefix=prefix, key_hash=_hash_key(raw),
            scopes=scopes,
            rate_limit_per_minute=int(data.get('rate_limit_per_minute', 120)),
        )
        db.session.add(k); db.session.commit()
        _record_audit('apikey.create', 'api_key', k.id,
                      {'name': k.name, 'scopes': scopes})
        return jsonify({'success': True, 'id': k.id, 'prefix': prefix,
                        'api_key': raw, 'note': 'Store this key now; it will not be shown again.'}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@keys_bp.route('', methods=['GET'])
@admin_required
def key_list():
    from app.models import ApiKey
    rows = ApiKey.query.filter_by(revoked=False).order_by(ApiKey.created_at.desc()).all()
    return jsonify({'success': True, 'count': len(rows), 'keys': [{
        'id': k.id, 'name': k.name, 'prefix': k.prefix, 'scopes': k.scopes,
        'rate_limit_per_minute': k.rate_limit_per_minute,
        'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
        'created_at': k.created_at.isoformat() if k.created_at else None,
    } for k in rows]})


@keys_bp.route('/<kid>/revoke', methods=['POST'])
@admin_required
def key_revoke(kid):
    try:
        from app.models import db, ApiKey
        k = ApiKey.query.filter_by(id=kid).first()
        if not k:
            return jsonify({'error': 'not found'}), 404
        k.revoked = True
        db.session.commit()
        _record_audit('apikey.revoke', 'api_key', kid, severity='warning')
        return jsonify({'success': True})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- Audit ---------------------------------------------------------

@audit_bp.route('/events', methods=['GET'])
@admin_required
def audit_list():
    from app.models import AuditEvent
    action = request.args.get('action')
    severity = request.args.get('severity')
    limit = min(500, int(request.args.get('limit', 100)))
    q = AuditEvent.query
    if action: q = q.filter_by(action=action)
    if severity: q = q.filter_by(severity=severity)
    rows = q.order_by(AuditEvent.created_at.desc()).limit(limit).all()
    return jsonify({'success': True, 'count': len(rows), 'events': [{
        'id': e.id, 'action': e.action, 'actor_user_id': e.actor_user_id,
        'resource_type': e.resource_type, 'resource_id': e.resource_id,
        'ip_address': e.ip_address, 'severity': e.severity,
        'details': e.details,
        'created_at': e.created_at.isoformat() if e.created_at else None,
    } for e in rows]})


# ---------- Compliance: consent + DSR -------------------------------------

@compliance_bp.route('/consent', methods=['POST'])
@login_required
def consent_record():
    try:
        from app.models import db, ConsentRecord
        data = request.get_json(silent=True) or {}
        ct = data.get('consent_type')
        if ct not in _CONSENT_TYPES:
            return jsonify({'error': f'consent_type must be one of {sorted(_CONSENT_TYPES)}'}), 400
        c = ConsentRecord(
            user_id=session['user_id'],
            consent_type=ct,
            framework=data.get('framework'),
            version=data.get('version'),
            granted=bool(data.get('granted', True)),
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=(request.headers.get('User-Agent') or '')[:255],
        )
        db.session.add(c); db.session.commit()
        _record_audit('consent.record', 'consent', c.id,
                      {'type': ct, 'granted': c.granted})
        return jsonify({'success': True, 'id': c.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@compliance_bp.route('/consent', methods=['GET'])
@login_required
def consent_list():
    from app.models import ConsentRecord
    rows = (ConsentRecord.query.filter_by(user_id=session['user_id'])
            .order_by(ConsentRecord.granted_at.desc()).all())
    return jsonify({'success': True, 'count': len(rows), 'consents': [{
        'id': c.id, 'consent_type': c.consent_type, 'framework': c.framework,
        'version': c.version, 'granted': c.granted,
        'granted_at': c.granted_at.isoformat() if c.granted_at else None,
        'revoked_at': c.revoked_at.isoformat() if c.revoked_at else None,
    } for c in rows]})


@compliance_bp.route('/data-requests', methods=['POST'])
@login_required
def dsr_create():
    try:
        from app.models import db, DataRequest
        data = request.get_json(silent=True) or {}
        rt = data.get('request_type')
        if rt not in _DR_TYPES:
            return jsonify({'error': f'request_type must be one of {sorted(_DR_TYPES)}'}), 400
        r = DataRequest(
            user_id=session['user_id'], request_type=rt,
            framework=data.get('framework', 'gdpr'),
            notes=data.get('notes'),
        )
        db.session.add(r); db.session.commit()
        _record_audit('compliance.data_request', 'data_request', r.id,
                      {'type': rt}, severity='warning')
        return jsonify({'success': True, 'id': r.id, 'status': r.status}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@compliance_bp.route('/data-requests', methods=['GET'])
@admin_required
def dsr_list():
    from app.models import DataRequest
    rows = DataRequest.query.order_by(DataRequest.created_at.desc()).limit(500).all()
    return jsonify({'success': True, 'count': len(rows), 'requests': [{
        'id': r.id, 'user_id': r.user_id, 'request_type': r.request_type,
        'framework': r.framework, 'status': r.status,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in rows]})


@compliance_bp.route('/export/me', methods=['GET'])
@login_required
def export_me():
    """Self-service data export (GDPR Art.15 / PDPL parity)."""
    from app.models import (
        User, Enrollment, ExamResult, LearnerProfile, ConsentRecord,
    )
    uid = session['user_id']
    u = User.query.filter_by(id=uid).first()
    return jsonify({
        'success': True, 'exported_at': datetime.utcnow().isoformat(),
        'user': {
            'id': u.id, 'username': u.username, 'email': u.email,
            'full_name': u.full_name, 'role': u.role,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        } if u else None,
        'enrollments': [{
            'course_id': e.course_id,
            'progress_percent': getattr(e, 'progress_percent', None),
        } for e in Enrollment.query.filter_by(user_id=uid).all()],
        'exam_results': [{
            'exam_id': r.exam_id, 'score': r.score,
        } for r in ExamResult.query.filter_by(user_id=uid).limit(500).all()],
        'profile': bool(LearnerProfile.query.filter_by(user_id=uid).first()),
        'consents': [{
            'type': c.consent_type, 'granted': c.granted,
            'at': c.granted_at.isoformat() if c.granted_at else None,
        } for c in ConsentRecord.query.filter_by(user_id=uid).all()],
    })


# ---------- Accessibility -------------------------------------------------

@accessibility_bp.route('/profile', methods=['GET'])
@login_required
def a11y_get():
    from app.models import LearnerProfile, db
    p = LearnerProfile.query.filter_by(user_id=session['user_id']).first()
    if not p:
        p = LearnerProfile(user_id=session['user_id'])
        db.session.add(p); db.session.commit()
    return jsonify({'success': True, 'accessibility': {
        'high_contrast': p.high_contrast,
        'dyslexia_mode': p.dyslexia_mode,
        'text_to_speech': p.text_to_speech,
        'reduce_motion': p.reduce_motion,
        'font_scale': p.font_scale,
    }})


@accessibility_bp.route('/profile', methods=['PUT'])
@login_required
def a11y_set():
    try:
        from app.models import db, LearnerProfile
        data = request.get_json(silent=True) or {}
        p = LearnerProfile.query.filter_by(user_id=session['user_id']).first()
        if not p:
            p = LearnerProfile(user_id=session['user_id'])
            db.session.add(p); db.session.flush()
        for f in ('high_contrast', 'dyslexia_mode', 'text_to_speech', 'reduce_motion'):
            if f in data:
                setattr(p, f, bool(data[f]))
        if 'font_scale' in data:
            try:
                p.font_scale = max(0.8, min(1.6, float(data['font_scale'])))
            except (TypeError, ValueError):
                pass
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@accessibility_bp.route('/tts', methods=['POST'])
@login_required
def a11y_tts():
    """Request text-to-speech for any material chunk.
    Returns SSML + voice metadata. Audio rendering is delegated to provider
    integrations available to the AIService."""
    try:
        from app.services.ai_service import AIService
    except Exception:
        AIService = None
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'text required'}), 400
    lang = data.get('language', 'en')
    voice = 'ar-XA-Standard-A' if lang == 'ar' else 'en-US-Standard-C'
    ssml = f"<speak><lang xml:lang=\"{('ar-OM' if lang=='ar' else 'en-US')}\">{text[:5000]}</lang></speak>"
    audio_url = None
    if AIService is not None and hasattr(AIService, 'synthesize_speech'):
        try:
            audio_url = AIService().synthesize_speech(text, lang=lang)
        except Exception:
            audio_url = None
    return jsonify({'success': True, 'language': lang, 'voice': voice,
                    'ssml': ssml, 'audio_url': audio_url})


# ---------- Public REST API -----------------------------------------------

def _require_api_key():
    """Validate `Authorization: Bearer <key>` for public endpoints. Returns
    the ApiKey row or None."""
    from app.models import db, ApiKey
    auth = request.headers.get('Authorization', '')
    if not auth.lower().startswith('bearer '):
        return None
    raw = auth.split(' ', 1)[1].strip()
    if not raw:
        return None
    h = _hash_key(raw)
    k = ApiKey.query.filter_by(key_hash=h, revoked=False).first()
    if k and getattr(k, 'expires_at', None) and k.expires_at < datetime.utcnow():
        return None
    if k:
        k.last_used_at = datetime.utcnow()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    return k


def _scope_required(scope):
    def deco(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*a, **kw):
            k = _require_api_key()
            if not k:
                return jsonify({'error': 'API key required'}), 401
            if scope not in (k.scopes or []):
                return jsonify({'error': f'missing scope {scope}'}), 403
            return fn(*a, **kw)
        return wrapper
    return deco


@public_api_bp.route('/courses', methods=['GET'])
@_scope_required('read:courses')
def public_courses():
    from app.models import Course
    rows = Course.query.filter_by(is_published=True).limit(200).all()
    return jsonify({'success': True, 'count': len(rows), 'courses': [{
        'id': c.id, 'title': c.title, 'title_ar': c.title_ar,
        'description': c.description,
    } for c in rows]})


@public_api_bp.route('/learners/<uid>/skills', methods=['GET'])
@_scope_required('read:learners')
def public_learner_skills(uid):
    """Return a learner's skills. Scoped to the API key's organization:
    if the key is bound to an organization, the requested learner must be a
    member of that same organization. Unbound (global) keys are allowed but
    rate-limited to organization-scoped keys in production deployments."""
    from app.models import LearnerSkill, ApiKey, OrganizationMember
    k = _require_api_key()
    if k and k.organization_id:
        member = OrganizationMember.query.filter_by(
            organization_id=k.organization_id, user_id=uid,
        ).first()
        if not member:
            return jsonify({'error': 'learner is not in your organization'}), 403
    rows = LearnerSkill.query.filter_by(user_id=uid).all()
    return jsonify({'success': True, 'count': len(rows), 'skills': [{
        'skill_id': r.skill_id, 'level': r.level, 'confidence': r.confidence,
    } for r in rows]})


# ---------- OpenAPI spec --------------------------------------------------

@spec_bp.route('/spec', methods=['GET'])
def openapi_spec():
    """Lightweight OpenAPI 3.0 listing of v2 surfaces (additive)."""
    return jsonify({
        'openapi': '3.0.3',
        'info': {
            'title': 'SkillPilot Public REST API',
            'version': '1.0.0',
            'description': 'Versioned public API for SkillPilot v2. '
                           'Authenticate with `Authorization: Bearer <api_key>`.',
        },
        'servers': [{'url': '/api/v1'}],
        'paths': {
            '/personalization/profile': {'get': {'summary': 'Get learner profile'}},
            '/personalization/home': {'get': {'summary': 'Aggregated home payload'}},
            '/authoring/drafts': {'get': {'summary': 'List authoring drafts'},
                                   'post': {'summary': 'Create draft'}},
            '/scorm/import': {'post': {'summary': 'Import SCORM package (metadata)'}},
            '/scorm/upload': {'post': {'summary': 'Upload + unpack SCORM ZIP'}},
            '/scorm/export': {'post': {'summary': 'Export Course as SCORM ZIP'}},
            '/scorm/packages/{id}/download': {
                'get': {'summary': 'Download exported SCORM ZIP'}
            },
            '/xapi/statements': {'post': {'summary': 'Emit xAPI statement (forwarded to LRS)'}},
            '/xapi/retry': {'post': {'summary': 'Retry failed xAPI deliveries'}},
            '/sso/{cid}/login': {'get': {'summary': 'Begin SAML/OIDC SSO handshake'}},
            '/sso/{cid}/callback': {'get': {'summary': 'OIDC callback'}},
            '/sso/{cid}/acs': {'post': {'summary': 'SAML AssertionConsumerService'}},
            '/skillmatch/labour-market/sync': {
                'post': {'summary': 'Sync labour-market signals from MoL/NCSI/job portals'}
            },
            '/engagement/badges': {'get': {'summary': 'List badges'}},
            '/engagement/leaderboard': {'get': {'summary': 'XP leaderboard'}},
            '/social/forums/threads': {'get': {'summary': 'List forum threads'}},
            '/guardian/dashboard': {'get': {'summary': 'Parent/guardian dashboard'}},
            '/live/sessions': {'get': {'summary': 'List live sessions'},
                                'post': {'summary': 'Schedule live session'}},
            '/insights/cohort': {'get': {'summary': 'Cohort analytics snapshot'}},
            '/insights/at-risk': {'get': {'summary': 'List at-risk alerts'}},
            '/skillmatch/readiness': {'get': {'summary': 'Job readiness score'}},
            '/pd/tracks': {'get': {'summary': 'List Teacher PD tracks'}},
            '/pd/certificates/{cert_id}/verify': {
                'get': {'summary': 'Verify a PD certificate (public)'}
            },
            '/enterprise/organizations': {'get': {'summary': 'List organizations'}},
            '/sso/configurations': {'get': {'summary': 'List SSO configs'}},
            '/keys': {'get': {'summary': 'List API keys'}},
            '/audit/events': {'get': {'summary': 'Audit log'}},
            '/compliance/consent': {'get': {'summary': 'List consents'}},
            '/compliance/export/me': {'get': {'summary': 'Self-service export'}},
            '/accessibility/profile': {'get': {'summary': 'Accessibility prefs'}},
            '/accessibility/tts': {'post': {'summary': 'Text-to-speech'}},
            '/public/courses': {'get': {'summary': 'Public catalog (API key)'}},
        },
        'components': {
            'securitySchemes': {
                'BearerAuth': {'type': 'http', 'scheme': 'bearer'}
            }
        },
        'security': [{'BearerAuth': []}],
    })
