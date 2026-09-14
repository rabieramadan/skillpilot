"""SAML signature verification + replay-protection tests for the ACS flow.

These tests build a self-signed RSA cert at runtime, sign a SAML Response
with signxml, then exercise both the service-level parser and the
``/api/v1/sso/<cid>/acs`` route to confirm:
  * a valid signed assertion is accepted and provisions a user.
  * unsigned, tampered, audience-mismatched, replay-protection-violating,
    and expired assertions are all rejected with a 4xx.
"""
import base64
import datetime
import secrets
from typing import Optional

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import DigestAlgorithm, SignatureMethod, XMLSigner

from app.services.sso_service import (
    SamlVerificationError,
    saml_parse_response,
)


SAMLP = 'urn:oasis:names:tc:SAML:2.0:protocol'
SAML = 'urn:oasis:names:tc:SAML:2.0:assertion'


def _gen_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'test-idp'),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=30))
            .sign(key, hashes.SHA256()))
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return cert_pem, key_pem


def _make_response_xml(*, request_id: str, audience: str, acs_url: str,
                        email: str = 'alice@example.com',
                        not_before_offset: int = -60,
                        not_on_or_after_offset: int = 600):
    now = datetime.datetime.now(datetime.timezone.utc)
    issue_instant = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    nb = (now + datetime.timedelta(seconds=not_before_offset)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    noa = (now + datetime.timedelta(seconds=not_on_or_after_offset)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    resp_id = '_resp' + secrets.token_hex(8)
    assertion_id = '_a' + secrets.token_hex(8)
    return f'''<samlp:Response xmlns:samlp="{SAMLP}" xmlns:saml="{SAML}"
        ID="{resp_id}" Version="2.0" IssueInstant="{issue_instant}"
        InResponseTo="{request_id}" Destination="{acs_url}">
  <saml:Issuer>https://idp.example.com/</saml:Issuer>
  <saml:Assertion ID="{assertion_id}" Version="2.0" IssueInstant="{issue_instant}">
    <saml:Issuer>https://idp.example.com/</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{email}</saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData InResponseTo="{request_id}"
            Recipient="{acs_url}" NotOnOrAfter="{noa}"/>
      </saml:SubjectConfirmation>
    </saml:Subject>
    <saml:Conditions NotBefore="{nb}" NotOnOrAfter="{noa}">
      <saml:AudienceRestriction>
        <saml:Audience>{audience}</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AttributeStatement>
      <saml:Attribute Name="email">
        <saml:AttributeValue>{email}</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="name">
        <saml:AttributeValue>Alice Example</saml:AttributeValue>
      </saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>'''


def _sign(xml_str: str, key_pem: str, cert_pem: str,
          *, sign_id: Optional[str] = None) -> bytes:
    """Sign the Assertion (or whichever element matches sign_id) enveloped."""
    root = etree.fromstring(xml_str.encode('utf-8'))
    if sign_id is None:
        target = root.find(f'{{{SAML}}}Assertion')
    else:
        target = root.xpath(f'.//*[@ID="{sign_id}"]')[0]
    signer = XMLSigner(
        method=__import__('signxml').methods.enveloped,
        signature_algorithm=SignatureMethod.RSA_SHA256,
        digest_algorithm=DigestAlgorithm.SHA256,
        c14n_algorithm='http://www.w3.org/2001/10/xml-exc-c14n#',
    )
    signed_target = signer.sign(target, key=key_pem, cert=cert_pem)
    # Replace target in tree with signed version
    parent = target.getparent()
    if parent is None:
        root = signed_target
    else:
        parent.replace(target, signed_target)
    return etree.tostring(root)


def _b64(xml_bytes: bytes) -> str:
    return base64.b64encode(xml_bytes).decode('ascii')


class _Cfg:
    """Lightweight stand-in for SsoConfiguration used by the parser."""
    def __init__(self, cert):
        self.saml_x509_cert = cert


# ---------- service-level tests ------------------------------------------

def test_parse_accepts_valid_signed_response():
    cert, key = _gen_keypair()
    req_id = '_req' + secrets.token_hex(8)
    audience = 'https://sp.example.com/saml'
    acs = 'https://sp.example.com/acs'
    xml = _make_response_xml(request_id=req_id, audience=audience, acs_url=acs)
    signed = _sign(xml, key, cert)
    parsed = saml_parse_response(
        _b64(signed), _Cfg(cert),
        expected_request_id=req_id,
        expected_audience=audience,
        expected_acs_url=acs,
    )
    assert parsed['_verified'] is True
    assert parsed['name_id'] == 'alice@example.com'
    assert parsed['attributes']['email'] == 'alice@example.com'


def test_parse_rejects_unsigned_response():
    cert, key = _gen_keypair()
    xml = _make_response_xml(request_id='_r', audience='aud', acs_url='acs')
    with pytest.raises(SamlVerificationError):
        saml_parse_response(_b64(xml.encode()), _Cfg(cert))


def test_parse_rejects_tampered_assertion():
    cert, key = _gen_keypair()
    req_id = '_req' + secrets.token_hex(8)
    xml = _make_response_xml(request_id=req_id, audience='aud', acs_url='acs')
    signed = _sign(xml, key, cert)
    tampered = signed.replace(b'alice@example.com', b'attacker@evil.com', 1)
    with pytest.raises(SamlVerificationError):
        saml_parse_response(_b64(tampered), _Cfg(cert),
                             expected_request_id=req_id)


def test_parse_rejects_wrong_audience():
    cert, key = _gen_keypair()
    req_id = '_req' + secrets.token_hex(8)
    xml = _make_response_xml(request_id=req_id,
                              audience='https://other.example.com',
                              acs_url='https://sp.example.com/acs')
    signed = _sign(xml, key, cert)
    with pytest.raises(SamlVerificationError, match='Audience'):
        saml_parse_response(_b64(signed), _Cfg(cert),
                             expected_request_id=req_id,
                             expected_audience='https://sp.example.com/saml')


def test_parse_rejects_in_response_to_mismatch():
    cert, key = _gen_keypair()
    xml = _make_response_xml(request_id='_attacker', audience='aud',
                              acs_url='acs')
    signed = _sign(xml, key, cert)
    with pytest.raises(SamlVerificationError, match='InResponseTo'):
        saml_parse_response(_b64(signed), _Cfg(cert),
                             expected_request_id='_real_request')


def test_parse_rejects_expired_assertion():
    cert, key = _gen_keypair()
    req_id = '_req' + secrets.token_hex(8)
    xml = _make_response_xml(request_id=req_id, audience='aud', acs_url='acs',
                              not_before_offset=-7200,
                              not_on_or_after_offset=-3600)
    signed = _sign(xml, key, cert)
    with pytest.raises(SamlVerificationError, match='expired'):
        saml_parse_response(_b64(signed), _Cfg(cert),
                             expected_request_id=req_id)


def test_parse_rejects_when_no_cert_configured():
    with pytest.raises(SamlVerificationError, match='saml_x509_cert'):
        saml_parse_response(_b64(b'<x/>'), _Cfg(None))


def _make_response_no_conditions(*, request_id, acs_url,
                                  email='alice@example.com'):
    now = datetime.datetime.now(datetime.timezone.utc)
    issue = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    noa = (now + datetime.timedelta(seconds=600)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    return f'''<samlp:Response xmlns:samlp="{SAMLP}" xmlns:saml="{SAML}"
        ID="_r{secrets.token_hex(4)}" Version="2.0" IssueInstant="{issue}">
  <saml:Assertion ID="_a{secrets.token_hex(4)}" Version="2.0" IssueInstant="{issue}">
    <saml:Issuer>https://idp.example.com/</saml:Issuer>
    <saml:Subject>
      <saml:NameID>{email}</saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData InResponseTo="{request_id}"
            Recipient="{acs_url}" NotOnOrAfter="{noa}"/>
      </saml:SubjectConfirmation>
    </saml:Subject>
  </saml:Assertion>
</samlp:Response>'''


def test_parse_rejects_assertion_without_conditions():
    cert, key = _gen_keypair()
    req_id = '_req' + secrets.token_hex(8)
    xml = _make_response_no_conditions(request_id=req_id, acs_url='acs')
    signed = _sign(xml, key, cert)
    with pytest.raises(SamlVerificationError, match='Conditions'):
        saml_parse_response(_b64(signed), _Cfg(cert),
                             expected_request_id=req_id)


def _make_response_no_recipient(*, request_id, audience,
                                 email='alice@example.com'):
    now = datetime.datetime.now(datetime.timezone.utc)
    issue = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    noa = (now + datetime.timedelta(seconds=600)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    return f'''<samlp:Response xmlns:samlp="{SAMLP}" xmlns:saml="{SAML}"
        ID="_r{secrets.token_hex(4)}" Version="2.0" IssueInstant="{issue}">
  <saml:Assertion ID="_a{secrets.token_hex(4)}" Version="2.0" IssueInstant="{issue}">
    <saml:Issuer>https://idp.example.com/</saml:Issuer>
    <saml:Subject>
      <saml:NameID>{email}</saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData InResponseTo="{request_id}"
            NotOnOrAfter="{noa}"/>
      </saml:SubjectConfirmation>
    </saml:Subject>
    <saml:Conditions NotBefore="{issue}" NotOnOrAfter="{noa}">
      <saml:AudienceRestriction>
        <saml:Audience>{audience}</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
  </saml:Assertion>
</samlp:Response>'''


def test_parse_rejects_subject_confirmation_without_recipient():
    cert, key = _gen_keypair()
    req_id = '_req' + secrets.token_hex(8)
    xml = _make_response_no_recipient(request_id=req_id, audience='aud')
    signed = _sign(xml, key, cert)
    with pytest.raises(SamlVerificationError, match='Recipient'):
        saml_parse_response(_b64(signed), _Cfg(cert),
                             expected_request_id=req_id,
                             expected_audience='aud',
                             expected_acs_url='https://sp/acs')


# ---------- ACS route tests ----------------------------------------------

def _make_saml_cfg(db, *, cert):
    from app.models import Organization, SsoConfiguration
    org = Organization(code='saml-test', name='SAML Test')
    db.session.add(org)
    db.session.flush()
    cfg = SsoConfiguration(
        organization_id=org.id, protocol='saml', display_name='Test IdP',
        enabled=True,
        saml_entity_id='https://sp.example.com/saml',
        saml_sso_url='https://idp.example.com/sso',
        saml_x509_cert=cert,
    )
    db.session.add(cfg)
    db.session.commit()
    return cfg.id


def _prime_session(client, cid, *, request_id, sp_entity, acs_url, relay):
    with client.session_transaction() as s:
        s['_sso_saml'] = {
            'cid': cid, 'relay': relay, 'request_id': request_id,
            'sp_entity_id': sp_entity, 'acs_url': acs_url,
            'next': '/',
        }


def test_acs_accepts_valid_signed_assertion(client, db, app):
    cert, key = _gen_keypair()
    with app.app_context():
        cid = _make_saml_cfg(db, cert=cert)
    req_id = '_req' + secrets.token_hex(8)
    sp = 'https://sp.example.com/saml'
    acs = f'http://localhost/api/v1/sso/{cid}/acs'
    xml = _make_response_xml(request_id=req_id, audience=sp, acs_url=acs)
    signed = _sign(xml, key, cert)
    _prime_session(client, cid, request_id=req_id, sp_entity=sp,
                    acs_url=acs, relay='r1')
    r = client.post(f'/api/v1/sso/{cid}/acs',
                     data={'SAMLResponse': _b64(signed), 'RelayState': 'r1'})
    # Successful login redirects.
    assert r.status_code in (302, 303)


def test_acs_rejects_unsigned(client, db, app):
    cert, key = _gen_keypair()
    with app.app_context():
        cid = _make_saml_cfg(db, cert=cert)
    req_id = '_req' + secrets.token_hex(8)
    sp = 'https://sp.example.com/saml'
    acs = f'http://localhost/api/v1/sso/{cid}/acs'
    xml = _make_response_xml(request_id=req_id, audience=sp, acs_url=acs)
    _prime_session(client, cid, request_id=req_id, sp_entity=sp,
                    acs_url=acs, relay='r1')
    r = client.post(f'/api/v1/sso/{cid}/acs',
                     data={'SAMLResponse': _b64(xml.encode()),
                           'RelayState': 'r1'})
    assert r.status_code == 401
    assert r.get_json()['error'] == 'SAML assertion rejected'


def test_acs_rejects_tampered(client, db, app):
    cert, key = _gen_keypair()
    with app.app_context():
        cid = _make_saml_cfg(db, cert=cert)
    req_id = '_req' + secrets.token_hex(8)
    sp = 'https://sp.example.com/saml'
    acs = f'http://localhost/api/v1/sso/{cid}/acs'
    xml = _make_response_xml(request_id=req_id, audience=sp, acs_url=acs)
    signed = _sign(xml, key, cert).replace(
        b'alice@example.com', b'attacker@evil.com', 1)
    _prime_session(client, cid, request_id=req_id, sp_entity=sp,
                    acs_url=acs, relay='r1')
    r = client.post(f'/api/v1/sso/{cid}/acs',
                     data={'SAMLResponse': _b64(signed), 'RelayState': 'r1'})
    assert r.status_code == 401


def test_acs_rejects_replay_with_stale_request_id(client, db, app):
    cert, key = _gen_keypair()
    with app.app_context():
        cid = _make_saml_cfg(db, cert=cert)
    sp = 'https://sp.example.com/saml'
    acs = f'http://localhost/api/v1/sso/{cid}/acs'
    # Assertion built for one request id, but session expects another.
    xml = _make_response_xml(request_id='_old_req', audience=sp, acs_url=acs)
    signed = _sign(xml, key, cert)
    _prime_session(client, cid, request_id='_new_req', sp_entity=sp,
                    acs_url=acs, relay='r1')
    r = client.post(f'/api/v1/sso/{cid}/acs',
                     data={'SAMLResponse': _b64(signed), 'RelayState': 'r1'})
    assert r.status_code == 401
    assert 'InResponseTo' in r.get_json()['reason']
