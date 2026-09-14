#!/usr/bin/env python3
"""Create the starting accounts on a new installation.

Safe to run again on a live system: an account that already exists is left
exactly as it is. This script used to overwrite the password of any account
whose username it recognised, so re-running the installer on a live server
silently reset the administrator's password back to ``admin123`` — reverting
a deliberate change and handing superadmin to anyone who knew the default.

Usage:
    python run_seed_users.py                  # create only what is missing
    python run_seed_users.py --reset-passwords  # also reset the seed accounts
    python run_seed_users.py --admin-only      # create only the admin account
"""

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.models import User, db

#: username, password, role, full name
SEED_ADMIN = ('admin', 'admin123', 'superadmin', 'System Administrator')
SEED_DEMO = [
    ('demoteacher1', 'demo123', 'instructor', 'Demo Teacher One'),
    ('demoteacher2', 'demo123', 'instructor', 'Demo Teacher Two'),
] + [
    (f'demostudent{n}', 'demo123', 'student', f'Demo Student {n}')
    for n in range(1, 6)
]


def hash_password(password: str) -> str:
    """Match the hashing used by the login route."""
    return hashlib.sha256(password.encode()).hexdigest()


def ensure_user(username, password, role, full_name, *, reset_passwords=False):
    """Create the account if missing. Returns what happened.

    An existing account is never modified unless ``reset_passwords`` is set,
    and even then only its password changes — the role, name and e-mail an
    administrator may have edited are left alone.
    """
    existing = User.query.filter_by(username=username).first()
    if existing:
        if not reset_passwords:
            return 'kept'
        existing.password_hash = hash_password(password)
        db.session.commit()
        return 'reset'

    db.session.add(User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        email=f'{username}@futurecoverage.ai',
    ))
    db.session.commit()
    return 'created'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--reset-passwords', action='store_true',
                        help='Also reset the seed accounts to their default '
                             'passwords. Destroys any password change made '
                             'since the account was created.')
    parser.add_argument('--admin-only', action='store_true',
                        help='Create only the admin account, no demo users.')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        total_users = User.query.count()
        wanted = [SEED_ADMIN] + ([] if args.admin_only else SEED_DEMO)

        if total_users and not args.reset_passwords:
            print(f'  Existing installation: {total_users} accounts already '
                  'present. Passwords will not be touched.')

        created, kept, reset = [], [], []
        for username, password, role, full_name in wanted:
            outcome = ensure_user(username, password, role, full_name,
                                  reset_passwords=args.reset_passwords)
            {'created': created, 'kept': kept, 'reset': reset}[outcome].append(username)

        print()
        if created:
            print(f'  Created {len(created)} account(s): {", ".join(created)}')
        if kept:
            print(f'  Left {len(kept)} existing account(s) untouched: '
                  f'{", ".join(kept)}')
        if reset:
            print(f'  Reset the password on {len(reset)} account(s): '
                  f'{", ".join(reset)}')

        if 'admin' in created:
            print()
            print('  ' + '-' * 60)
            print('  Sign in as        admin / admin123')
            if not args.admin_only:
                print('  Demo teachers     demoteacher1, demoteacher2 / demo123')
                print('  Demo students     demostudent1-5 / demo123')
            print('  Change the admin password immediately after first login.')
            print('  ' + '-' * 60)
        elif not created:
            print()
            print('  Nothing to do — every seed account already exists.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
