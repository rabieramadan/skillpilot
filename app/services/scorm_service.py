"""
SCORM 1.2 / 2004 import + export service.

Real implementation:
  * `import_package(zip_path, course_id, user_id)` — unpacks a SCORM ZIP,
    parses `imsmanifest.xml`, extracts files into
    `uploads/scorm/<package_id>/`, registers each launchable resource as a
    `WeekMaterial` row, and stores the parsed manifest on the
    `ScormPackage` record.
  * `export_course(course_id, scorm_version, user_id)` — bundles a course's
    weeks + materials into a SCORM-compliant ZIP saved under
    `uploads/scorm/exports/`. Generates a minimal `imsmanifest.xml` and a
    launcher `index.html` per material.

The implementation only depends on the Python stdlib (`zipfile`,
`xml.etree.ElementTree`) and the existing Flask app config.
"""
from __future__ import annotations

import os
import re
import shutil
import zipfile
import defusedxml.ElementTree as ET  # XXE-safe parser
from datetime import datetime
from typing import Optional


def _scorm_root(app):
    folder = os.path.join(app.config.get('UPLOAD_FOLDER',
                                          os.path.join(os.getcwd(), 'uploads')),
                          'scorm')
    os.makedirs(folder, exist_ok=True)
    return folder


def _strip_ns(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _walk(elem):
    yield elem
    for child in list(elem):
        yield from _walk(child)


def parse_manifest(manifest_path: str) -> dict:
    """Parse imsmanifest.xml into a normalized dict.

    Returns: {
        'scorm_version': '1.2'|'2004',
        'title': str,
        'organizations': [...],
        'resources': [{identifier, type, href, files:[...]}, ...],
        'items': [{identifier, title, resource_id, href}, ...],
    }
    """
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    ns = {k or 'm': v for k, v in re.findall(r'xmlns:?(\w*)="([^"]+)"',
                                              ET.tostring(root, encoding='unicode'))}
    # detect SCORM version
    schemaversion = '1.2'
    for el in _walk(root):
        if _strip_ns(el.tag) == 'schemaversion' and el.text:
            t = el.text.strip()
            schemaversion = '2004' if '2004' in t or t.startswith('CAM') else '1.2'
            break

    title = ''
    resources = []
    items = []

    for el in _walk(root):
        tag = _strip_ns(el.tag)
        if tag == 'title' and not title and el.text:
            title = el.text.strip()
        elif tag == 'resource':
            files = [f.attrib.get('href')
                     for f in el if _strip_ns(f.tag) == 'file' and f.attrib.get('href')]
            resources.append({
                'identifier': el.attrib.get('identifier'),
                'type': el.attrib.get('type'),
                'href': el.attrib.get('href'),
                'scorm_type': (el.attrib.get(
                    '{http://www.adlnet.org/xsd/adlcp_rootv1p2}scormtype')
                               or el.attrib.get(
                    '{http://www.adlnet.org/xsd/adlcp_v1p3}scormType')),
                'files': files,
            })
        elif tag == 'item':
            ititle = ''
            for child in el:
                if _strip_ns(child.tag) == 'title' and child.text:
                    ititle = child.text.strip()
                    break
            items.append({
                'identifier': el.attrib.get('identifier'),
                'title': ititle,
                'resource_id': el.attrib.get('identifierref'),
            })

    res_by_id = {r['identifier']: r for r in resources if r.get('identifier')}
    for it in items:
        rid = it.get('resource_id')
        it['href'] = res_by_id.get(rid, {}).get('href') if rid else None

    return {
        'scorm_version': schemaversion,
        'title': title,
        'resources': resources,
        'items': items,
    }


def import_package(zip_path: str, *, course_id: Optional[str], user_id: str,
                   package_name: Optional[str] = None) -> dict:
    """Unpack a SCORM ZIP, parse its manifest, register materials.

    Returns a dict with keys: package_id, materials_added, manifest, dest_dir.
    Raises ValueError on invalid SCORM ZIPs.
    """
    from flask import current_app
    from app.models import db, ScormPackage, CourseWeek, WeekMaterial

    root = _scorm_root(current_app)
    pkg = ScormPackage(
        course_id=course_id,
        package_name=package_name or os.path.basename(zip_path),
        scorm_version='2004',
        direction='import',
        status='processing',
        created_by=user_id,
        size_bytes=os.path.getsize(zip_path) if os.path.exists(zip_path) else None,
    )
    db.session.add(pkg)
    db.session.flush()
    dest = os.path.join(root, pkg.id)
    os.makedirs(dest, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Validate manifest exists
            names = zf.namelist()
            if not any(n.endswith('imsmanifest.xml') for n in names):
                raise ValueError('imsmanifest.xml not found in SCORM package')
            # Safe extraction (block path traversal)
            for n in names:
                target = os.path.realpath(os.path.join(dest, n))
                if not target.startswith(os.path.realpath(dest) + os.sep) \
                        and target != os.path.realpath(dest):
                    raise ValueError(f'unsafe path in SCORM zip: {n}')
            zf.extractall(dest)

        manifest_path = None
        for r, _d, files in os.walk(dest):
            if 'imsmanifest.xml' in files:
                manifest_path = os.path.join(r, 'imsmanifest.xml')
                break
        if not manifest_path:
            raise ValueError('imsmanifest.xml missing after extraction')

        info = parse_manifest(manifest_path)
        pkg.manifest = info
        pkg.scorm_version = info['scorm_version']
        pkg.storage_path = dest

        # Register each item as a WeekMaterial under week 1 (best-effort).
        materials_added = 0
        if course_id:
            week = (CourseWeek.query.filter_by(course_id=course_id, week_number=1)
                    .first())
            if not week:
                week = CourseWeek(course_id=course_id, week_number=1,
                                  title=info.get('title') or 'SCORM Content',
                                  is_published=False)
                db.session.add(week)
                db.session.flush()
            base_dir = os.path.dirname(manifest_path)
            for idx, item in enumerate(info.get('items') or []):
                if not item.get('href'):
                    continue
                rel = os.path.relpath(os.path.join(base_dir, item['href']),
                                      current_app.config.get('UPLOAD_FOLDER', 'uploads'))
                m = WeekMaterial(
                    week_id=week.id,
                    title=item.get('title') or f"SCORM item {idx+1}",
                    material_type='link',
                    file_url=f"/uploads/{rel.replace(os.sep, '/')}",
                    description=f"Imported from SCORM package {pkg.package_name}",
                    order_index=idx,
                    is_published=False,
                    visibility_state='draft',
                )
                db.session.add(m)
                materials_added += 1

        pkg.status = 'ready'
        db.session.commit()
        return {
            'package_id': pkg.id,
            'materials_added': materials_added,
            'manifest': info,
            'dest_dir': dest,
        }
    except Exception as e:
        pkg.status = 'failed'
        pkg.error_message = str(e)[:2000]
        db.session.commit()
        # Clean up failed extraction directory
        try:
            shutil.rmtree(dest, ignore_errors=True)
        except Exception:
            pass
        raise


def _xml_escape(s: str) -> str:
    return (s or '').replace('&', '&amp;').replace('<', '&lt;') \
        .replace('>', '&gt;').replace('"', '&quot;')


def export_course(course_id: str, *, scorm_version: str = '2004',
                  user_id: Optional[str] = None) -> dict:
    """Export a Course to a SCORM ZIP. Returns {package_id, zip_path, download_url}."""
    from flask import current_app
    from app.models import db, ScormPackage, Course, CourseWeek, WeekMaterial

    course = Course.query.filter_by(id=course_id).first()
    if not course:
        raise ValueError('course not found')
    if scorm_version not in ('1.2', '2004'):
        raise ValueError('scorm_version must be 1.2 or 2004')

    root = _scorm_root(current_app)
    exports_dir = os.path.join(root, 'exports')
    os.makedirs(exports_dir, exist_ok=True)

    pkg = ScormPackage(
        course_id=course_id,
        package_name=f'course-{course_id}-{scorm_version}.zip',
        scorm_version=scorm_version,
        direction='export',
        status='processing',
        created_by=user_id,
    )
    db.session.add(pkg)
    db.session.flush()

    work_dir = os.path.join(exports_dir, pkg.id)
    os.makedirs(work_dir, exist_ok=True)

    try:
        items_xml = []
        resources_xml = []
        weeks = (CourseWeek.query.filter_by(course_id=course_id)
                 .order_by(CourseWeek.week_number).all())
        for week in weeks:
            mats = (WeekMaterial.query.filter_by(week_id=week.id)
                    .order_by(WeekMaterial.order_index).all())
            for m in mats:
                rid = f'res_{m.id}'
                fname = f'launch_{m.id}.html'
                # Each material gets its own minimal SCO launcher.
                body_link = m.file_url or m.external_url or ''
                html = (f'<!doctype html><meta charset="utf-8">'
                        f'<title>{_xml_escape(m.title)}</title>'
                        f'<h1>{_xml_escape(m.title)}</h1>'
                        f'<p>{_xml_escape(m.description or "")}</p>'
                        + (f'<p><a href="{_xml_escape(body_link)}">Open content</a></p>'
                           if body_link else '')
                        + (m.content_html or ''))
                with open(os.path.join(work_dir, fname), 'w', encoding='utf-8') as fh:
                    fh.write(html)
                title = f'Week {week.week_number}: {m.title}'
                items_xml.append(
                    f'<item identifier="item_{m.id}" identifierref="{rid}">'
                    f'<title>{_xml_escape(title)}</title></item>'
                )
                if scorm_version == '2004':
                    resources_xml.append(
                        f'<resource identifier="{rid}" type="webcontent" '
                        f'adlcp:scormType="sco" href="{fname}">'
                        f'<file href="{fname}"/></resource>'
                    )
                else:
                    resources_xml.append(
                        f'<resource identifier="{rid}" type="webcontent" '
                        f'adlcp:scormtype="sco" href="{fname}">'
                        f'<file href="{fname}"/></resource>'
                    )

        if scorm_version == '2004':
            manifest = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<manifest identifier="MANIFEST-{course_id}" version="1.0" '
                'xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" '
                'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                '<metadata><schema>ADL SCORM</schema>'
                '<schemaversion>2004 4th Edition</schemaversion></metadata>'
                f'<organizations default="ORG-{course_id}">'
                f'<organization identifier="ORG-{course_id}">'
                f'<title>{_xml_escape(course.title)}</title>'
                + ''.join(items_xml) +
                '</organization></organizations>'
                '<resources>' + ''.join(resources_xml) + '</resources>'
                '</manifest>'
            )
        else:
            manifest = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<manifest identifier="MANIFEST-{course_id}" version="1.2" '
                'xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" '
                'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                '<metadata><schema>ADL SCORM</schema>'
                '<schemaversion>1.2</schemaversion></metadata>'
                f'<organizations default="ORG-{course_id}">'
                f'<organization identifier="ORG-{course_id}">'
                f'<title>{_xml_escape(course.title)}</title>'
                + ''.join(items_xml) +
                '</organization></organizations>'
                '<resources>' + ''.join(resources_xml) + '</resources>'
                '</manifest>'
            )

        with open(os.path.join(work_dir, 'imsmanifest.xml'), 'w', encoding='utf-8') as fh:
            fh.write(manifest)

        zip_path = os.path.join(exports_dir, f'{pkg.id}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for r, _d, files in os.walk(work_dir):
                for f in files:
                    full = os.path.join(r, f)
                    arc = os.path.relpath(full, work_dir)
                    zf.write(full, arc)

        pkg.storage_path = zip_path
        pkg.size_bytes = os.path.getsize(zip_path)
        pkg.manifest = {'exported': True, 'course_id': course_id,
                         'version': scorm_version,
                         'item_count': len(items_xml)}
        pkg.status = 'ready'
        db.session.commit()
        return {
            'package_id': pkg.id,
            'zip_path': zip_path,
            'download_url': f'/api/v1/scorm/packages/{pkg.id}/download',
            'item_count': len(items_xml),
        }
    except Exception as e:
        pkg.status = 'failed'
        pkg.error_message = str(e)[:2000]
        db.session.commit()
        raise
    finally:
        # Keep work_dir for inspection but it's not strictly needed once zipped.
        pass
