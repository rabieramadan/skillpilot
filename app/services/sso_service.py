"""
SAML 2.0 + OIDC single sign-on handshakes.

This service implements:
  * OIDC Authorization Code flow (with PKCE) using `requests` and the
    issuer's `.well-known/openid-configuration` document. ID tokens are
    decoded and verified against the issuer's JWKS (RS256) using the
    `cryptography` library. Verification is mandatory — failures raise.
  * SAML 2.0 SP that produces a deflated/base64-encoded AuthnRequest for the
    HTTP-Redirect binding and consumes a base64-encoded `SAMLResponse` posted
    to the ACS endpoint. SAML signatures are verified strictly using
    `signxml` against the configured `saml_x509_cert`; replay protection
    enforces Conditions/NotOnOrAfter, AudienceRestriction, and
    SubjectConfirmationData.InResponseTo + Recipient.

Just-in-time provisioning creates a `User` with the configured default role
and links them to the SSO configuration's `Organization` via
`OrganizationMember`.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
import defusedxml.ElementTree as ET  # XXE-safe parser
import zlib
from typing import Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


# ---------- OIDC ----------------------------------------------------------

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data: str) -> bytes:
    pad = 4 - (len(data) % 4)
    if pad and pad != 4:
        data += '=' * pad
    return base64.urlsafe_b64decode(data)


def _discover(issuer: str) -> dict:
    if not requests:
        raise RuntimeError('requests not available for OIDC discovery')
    url = issuer.rstrip('/') + '/.well-known/openid-configuration'
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    return r.json()


def oidc_build_auth_url(cfg, *, state: str, nonce: str,
                         code_verifier: str) -> str:
    """Return an authorization URL the user-agent should be redirected to."""
    disc = _discover(cfg.oidc_issuer)
    auth_ep = disc['authorization_endpoint']
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode()).digest())
    params = {
        'response_type': 'code',
        'client_id': cfg.oidc_client_id,
        'redirect_uri': cfg.oidc_redirect_uri,
        'scope': cfg.oidc_scopes or 'openid profile email',
        'state': state,
        'nonce': nonce,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    return auth_ep + ('&' if '?' in auth_ep else '?') + urllib.parse.urlencode(params)


def oidc_exchange_code(cfg, *, code: str, code_verifier: str) -> dict:
    """Exchange the authorization code for tokens + decoded id_token claims."""
    disc = _discover(cfg.oidc_issuer)
    token_ep = disc['token_endpoint']
    secret = None
    if getattr(cfg, 'oidc_client_secret_encrypted', None):
        try:
            from app.utils.encryption import decrypt_api_key
            secret = decrypt_api_key(cfg.oidc_client_secret_encrypted)
        except Exception:
            secret = None
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': cfg.oidc_redirect_uri,
        'client_id': cfg.oidc_client_id,
        'code_verifier': code_verifier,
    }
    if secret:
        data['client_secret'] = secret
    r = requests.post(token_ep, data=data, timeout=10,
                      headers={'Accept': 'application/json'})
    r.raise_for_status()
    tokens = r.json()
    id_token = tokens.get('id_token')
    if not id_token:
        raise ValueError('OIDC token endpoint did not return id_token')
    claims = _decode_id_token(id_token, disc, cfg)
    return {'tokens': tokens, 'claims': claims}


_ALLOWED_OIDC_ALGS = {'RS256', 'RS384', 'RS512'}


def _decode_id_token(id_token: str, disc: dict, cfg) -> dict:
    """Decode + verify an OIDC id_token. Fails closed: the function raises
    `ValueError` if the algorithm is unsupported, the JWKS lookup fails, or
    the signature does not verify. The returned payload is therefore always
    cryptographically verified."""
    parts = id_token.split('.')
    if len(parts) != 3:
        raise ValueError('malformed id_token')
    header = json.loads(_b64url_decode(parts[0]))
    payload = json.loads(_b64url_decode(parts[1]))

    alg = header.get('alg', '')
    if alg not in _ALLOWED_OIDC_ALGS:
        raise ValueError(f'OIDC id_token uses unsupported algorithm: {alg!r}')
    if not disc.get('jwks_uri'):
        raise ValueError('OIDC discovery document missing jwks_uri')

    jwks = requests.get(disc['jwks_uri'], timeout=8).json()
    kid = header.get('kid')
    jwk = next((k for k in jwks.get('keys', [])
                if not kid or k.get('kid') == kid), None)
    if not jwk:
        raise ValueError('no matching JWK found for id_token kid')
    if jwk.get('kty') != 'RSA' or 'n' not in jwk or 'e' not in jwk:
        raise ValueError('only RSA JWKs are supported for id_token verification')

    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes
    n = int.from_bytes(_b64url_decode(jwk['n']), 'big')
    e = int.from_bytes(_b64url_decode(jwk['e']), 'big')
    pub = RSAPublicNumbers(e, n).public_key()
    signing_input = (parts[0] + '.' + parts[1]).encode('ascii')
    sig = _b64url_decode(parts[2])
    hash_alg = {'RS256': hashes.SHA256(), 'RS384': hashes.SHA384(),
                'RS512': hashes.SHA512()}[alg]
    try:
        pub.verify(sig, signing_input, padding.PKCS1v15(), hash_alg)
    except Exception as e_sig:
        raise ValueError(f'OIDC id_token signature invalid: {e_sig}')
    verified = True

    # claim checks
    iss = payload.get('iss')
    aud = payload.get('aud')
    exp = payload.get('exp')
    if iss and cfg.oidc_issuer and iss.rstrip('/') != cfg.oidc_issuer.rstrip('/'):
        raise ValueError('id_token issuer mismatch')
    if aud and cfg.oidc_client_id:
        aud_list = aud if isinstance(aud, list) else [aud]
        if cfg.oidc_client_id not in aud_list:
            raise ValueError('id_token audience mismatch')
    if exp and exp < int(time.time()) - 30:
        raise ValueError('id_token expired')

    payload['_verified'] = verified
    payload['_alg'] = alg
    return payload


# ---------- SAML 2.0 ------------------------------------------------------

_SAML_NS = {
    'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
    'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
}


class SamlVerificationError(ValueError):
    """Raised when a SAMLResponse fails cryptographic or replay-protection
    checks. Callers should treat this as a hard 4xx (never trust the
    assertion)."""


def saml_build_authn_redirect_url(cfg, *, sp_entity_id: str, acs_url: str,
                                    relay_state: str) -> tuple[str, str]:
    """Build the IdP redirect URL with deflated/base64 AuthnRequest.

    Returns ``(url, request_id)``. Callers must persist ``request_id`` in
    the user's session so the ACS endpoint can enforce InResponseTo replay
    protection on the returned assertion.
    """
    req_id = '_' + secrets.token_hex(16)
    issue_instant = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    xml = (
        f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" '
        f'ID="{req_id}" Version="2.0" IssueInstant="{issue_instant}" '
        f'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
        f'AssertionConsumerServiceURL="{acs_url}">'
        f'<saml:Issuer>{sp_entity_id}</saml:Issuer>'
        f'<samlp:NameIDPolicy '
        f'Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" '
        f'AllowCreate="true"/></samlp:AuthnRequest>'
    )
    deflated = zlib.compress(xml.encode('utf-8'))[2:-4]  # raw deflate
    encoded = base64.b64encode(deflated).decode('ascii')
    qs = urllib.parse.urlencode({
        'SAMLRequest': encoded, 'RelayState': relay_state,
    })
    sso_url = cfg.saml_sso_url
    url = sso_url + ('&' if '?' in sso_url else '?') + qs
    return url, req_id


def _saml_parse_iso(s: str) -> int:
    """Parse a SAML/XSD dateTime in UTC into an epoch second."""
    import datetime as _dt
    s = s.strip()
    if s.endswith('Z'):
        s = s[:-1]
    if '.' in s:
        s = s.split('.', 1)[0]
    dt = _dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
    return int(dt.replace(tzinfo=_dt.timezone.utc).timestamp())


def saml_parse_response(saml_response_b64: str, cfg, *,
                         expected_request_id: Optional[str] = None,
                         expected_audience: Optional[str] = None,
                         expected_acs_url: Optional[str] = None,
                         clock_skew_seconds: int = 120,
                         now: Optional[int] = None) -> dict:
    """Strictly parse and verify a base64-encoded SAMLResponse.

    Performs, in order:
      1. base64 decode of the POSTed body.
      2. Cryptographic XML-signature verification using ``signxml`` against
         ``cfg.saml_x509_cert``. Fails closed if signxml is unavailable, the
         cert is missing, the document is unsigned, or the signature does
         not verify.
      3. Replay-protection on the *signed* XML only:
         ``Conditions/@NotBefore`` & ``@NotOnOrAfter`` (with clock skew),
         ``AudienceRestriction`` against ``expected_audience``,
         ``SubjectConfirmationData/@InResponseTo`` against
         ``expected_request_id``, ``@Recipient`` against
         ``expected_acs_url``, and ``@NotOnOrAfter`` on
         SubjectConfirmationData. Response-level ``@InResponseTo`` is also
         checked when present in the signed payload.

    All failures raise :class:`SamlVerificationError`. On success returns
    ``{'name_id', 'attributes', '_verified': True}`` with values extracted
    only from the signed element to defeat XML-signature-wrapping attacks.
    """
    if not cfg.saml_x509_cert:
        raise SamlVerificationError(
            'SAML configuration has no saml_x509_cert; cannot verify signature')
    try:
        xml_bytes = base64.b64decode(saml_response_b64)
    except Exception as e:
        raise SamlVerificationError(f'invalid base64 SAMLResponse: {e}')

    try:
        from signxml import XMLVerifier  # type: ignore
        from lxml import etree as LET    # type: ignore
    except ImportError as e:  # pragma: no cover
        raise SamlVerificationError(
            f'signxml/lxml are required for SAML signature verification: {e}')

    try:
        verified = XMLVerifier().verify(
            xml_bytes, x509_cert=cfg.saml_x509_cert)
    except Exception as e:
        raise SamlVerificationError(f'SAML signature verification failed: {e}')

    signed_el = verified.signed_xml
    if signed_el is None:
        raise SamlVerificationError('SAML signature did not cover any element')
    # Re-parse from the signed bytes only — never trust unsigned siblings.
    signed_bytes = LET.tostring(signed_el)
    root = ET.fromstring(signed_bytes)

    tag = root.tag.split('}', 1)[-1]
    if tag == 'Response':
        assertion = root.find('saml:Assertion', _SAML_NS)
        response_el = root
    elif tag == 'Assertion':
        assertion = root
        response_el = None
    else:
        raise SamlVerificationError(
            f'signed element is neither Response nor Assertion (got {tag!r})')
    if assertion is None:
        raise SamlVerificationError('signed SAML payload missing Assertion')

    now_ts = now if now is not None else int(time.time())

    # ----- Conditions (mandatory) ---------------------------------------
    conds = assertion.find('saml:Conditions', _SAML_NS)
    if conds is None:
        raise SamlVerificationError(
            'SAML assertion missing Conditions element')
    nb = conds.attrib.get('NotBefore')
    noa = conds.attrib.get('NotOnOrAfter')
    if not noa:
        raise SamlVerificationError(
            'SAML Conditions missing NotOnOrAfter')
    if nb and _saml_parse_iso(nb) > now_ts + clock_skew_seconds:
        raise SamlVerificationError('SAML assertion not yet valid')
    if _saml_parse_iso(noa) <= now_ts - clock_skew_seconds:
        raise SamlVerificationError('SAML assertion expired')

    # ----- AudienceRestriction (mandatory when expected_audience set) ---
    audiences: list[str] = []
    for ar in conds.findall('saml:AudienceRestriction', _SAML_NS):
        for aud in ar.findall('saml:Audience', _SAML_NS):
            if aud.text:
                audiences.append(aud.text.strip())
    if expected_audience is not None:
        if not audiences:
            raise SamlVerificationError(
                'SAML assertion missing AudienceRestriction')
        if expected_audience not in audiences:
            raise SamlVerificationError(
                'SAML AudienceRestriction does not include this SP')

    # ----- SubjectConfirmationData replay protection --------------------
    subject = assertion.find('saml:Subject', _SAML_NS)
    if subject is None:
        raise SamlVerificationError('SAML assertion missing Subject')
    scd_seen = False
    for sc in subject.findall('saml:SubjectConfirmation', _SAML_NS):
        scd = sc.find('saml:SubjectConfirmationData', _SAML_NS)
        if scd is None:
            continue
        scd_seen = True
        scd_irt = scd.attrib.get('InResponseTo')
        if expected_request_id is not None:
            if not scd_irt:
                raise SamlVerificationError(
                    'SubjectConfirmationData missing InResponseTo')
            if scd_irt != expected_request_id:
                raise SamlVerificationError(
                    'SubjectConfirmationData InResponseTo mismatch')
        scd_recipient = scd.attrib.get('Recipient')
        if expected_acs_url is not None:
            if not scd_recipient:
                raise SamlVerificationError(
                    'SubjectConfirmationData missing Recipient')
            if scd_recipient != expected_acs_url:
                raise SamlVerificationError(
                    'SubjectConfirmationData Recipient mismatch')
        scd_noa = scd.attrib.get('NotOnOrAfter')
        if not scd_noa:
            raise SamlVerificationError(
                'SubjectConfirmationData missing NotOnOrAfter')
        if _saml_parse_iso(scd_noa) <= now_ts - clock_skew_seconds:
            raise SamlVerificationError('SubjectConfirmationData expired')
    if not scd_seen:
        raise SamlVerificationError(
            'assertion has no SubjectConfirmationData; cannot verify replay protection')

    # ----- Response-level InResponseTo ----------------------------------
    if expected_request_id is not None and response_el is not None:
        irt = response_el.attrib.get('InResponseTo')
        if irt and irt != expected_request_id:
            raise SamlVerificationError('Response InResponseTo mismatch')

    # ----- Extract claims (from the signed element only) ----------------
    name_id_el = (subject.find('saml:NameID', _SAML_NS)
                  if subject is not None else None)
    name_id = (name_id_el.text.strip()
               if (name_id_el is not None and name_id_el.text) else None)

    attrs: dict = {}
    attrstmt = assertion.find('saml:AttributeStatement', _SAML_NS)
    if attrstmt is not None:
        for a in attrstmt.findall('saml:Attribute', _SAML_NS):
            name = a.attrib.get('Name')
            vals = [v.text for v in a.findall('saml:AttributeValue', _SAML_NS)
                    if v.text is not None]
            if name and vals:
                attrs[name] = vals[0] if len(vals) == 1 else vals

    return {
        'name_id': name_id,
        'attributes': attrs,
        '_verified': True,
    }


# ---------- JIT provisioning ---------------------------------------------

def jit_provision_user(cfg, *, email: str, full_name: Optional[str] = None,
                        external_id: Optional[str] = None) -> dict:
    """Find-or-create a User from SSO claims and link to the org. Returns
    {user_id, created}."""
    from app.models import db, User, OrganizationMember
    from werkzeug.security import generate_password_hash

    if not email:
        raise ValueError('SSO claims missing email/NameID')

    user = User.query.filter_by(email=email).first()
    created = False
    if not user:
        if not getattr(cfg, 'just_in_time_provisioning', True):
            raise ValueError('SSO user not found and JIT provisioning is disabled')
        username = email.split('@', 1)[0]
        # Ensure unique username
        base = username
        i = 1
        while User.query.filter_by(username=username).first():
            i += 1
            username = f'{base}{i}'
        user = User(
            username=username, email=email, full_name=full_name or email,
            role=getattr(cfg, 'default_role', 'student') or 'student',
            password_hash=generate_password_hash(secrets.token_urlsafe(24)),
        )
        db.session.add(user)
        db.session.flush()
        created = True

    if cfg.organization_id:
        already = OrganizationMember.query.filter_by(
            organization_id=cfg.organization_id, user_id=user.id,
        ).first()
        if not already:
            db.session.add(OrganizationMember(
                organization_id=cfg.organization_id,
                user_id=user.id,
                org_role='member',
            ))
    db.session.commit()
    return {'user_id': user.id, 'created': created, 'email': email,
             'role': user.role}
