"""Release enrolments that were left waiting for an approval nobody could give.

Every self-enrolment used to be written as ``pending``. Nothing could move it
on: the approve and reject endpoints read the legacy ``enrollments.json`` and
expect the status ``requested``, so they never saw a database row, and the
admin screens dropped the pending queue on purpose ("Enrollments are now
auto-approved upon student enrollment request", static/js/classes.js).

So a student who enrolled in a free course was told it had worked, saw it in
their course list, and could never open it. ``/api/classes/enroll`` now grants
access immediately unless the course is paid; this releases the people who
enrolled before that fix.

Only enrolments that are ``pending`` on a course that does not require payment
are touched, and they become ``active`` — exactly what enrolling in that course
does today. Paid courses are left alone: those genuinely wait for
/api/classes/verify-payment. Nothing is deleted.

    python -m migrations.release_stranded_enrolments            # show what would change
    python -m migrations.release_stranded_enrolments --apply    # make the change
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402  (needs the path above)
from app.models import db, Course, Enrollment, User  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='write the change; without it, only report')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        stranded = (
            db.session.query(Enrollment, Course, User)
            .join(Course, Course.id == Enrollment.course_id)
            .join(User, User.id == Enrollment.user_id)
            .filter(Enrollment.status == 'pending')
            .filter((Course.requires_payment.is_(False))
                    | (Course.requires_payment.is_(None)))
            .all()
        )

        paid_waiting = (
            Enrollment.query.join(Course, Course.id == Enrollment.course_id)
            .filter(Enrollment.status == 'pending')
            .filter(Course.requires_payment.is_(True))
            .count()
        )

        if not stranded:
            print('Nothing to release: no pending enrolment on a free course.')
        else:
            print(f'{len(stranded)} enrolment(s) stuck on a free course:\n')
            by_course = {}
            for enrollment, course, user in stranded:
                by_course.setdefault(course.title, []).append(user.username)
            for title, students in sorted(by_course.items()):
                shown = ', '.join(students[:6])
                more = f' and {len(students) - 6} more' if len(students) > 6 else ''
                print(f'  {title}: {shown}{more}')

        if paid_waiting:
            print(f'\n{paid_waiting} enrolment(s) on paid courses left as they '
                  'are; those wait for payment verification.')

        if not stranded:
            return 0

        if not args.apply:
            print('\nThis was a dry run. Re-run with --apply to release them.')
            return 0

        for enrollment, _course, _user in stranded:
            enrollment.status = 'active'
            enrollment.payment_status = 'not_required'
        db.session.commit()
        print(f'\nReleased {len(stranded)} enrolment(s). Those students can '
              'open their courses now.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
