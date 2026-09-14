"""
Phase 3 — Smart Assessment, Retention & Transparent Proctoring
================================================================

This service powers three new capabilities:

1. **Spaced retention scheduler** — surfaces lightweight retention quizzes
   for previously-mastered skills whose `LearnerSkill` evidence is decaying.

2. **Rubric grading** — evaluates short-answer / essay responses against an
   explicit rubric and returns bilingual (EN/AR) per-criterion feedback.
   Falls back to a transparent heuristic grader when no AI key is available
   so the feature is never silently broken.

3. **Transparent proctoring** — exposes the *exhaustive* list of signals
   we may collect during an assessment, exactly what each one means, and
   why we collect it. Only signals appearing in `PROCTORING_SIGNALS` are
   accepted by the API. **No biometric, camera, microphone, keystroke
   timing, mouse-tracking, or face data is ever collected or stored.**
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Transparent proctoring signals (the *only* ones we accept)
# ---------------------------------------------------------------------------

PROCTORING_SIGNALS: Dict[str, Dict[str, Any]] = {
    'tab_blur': {
        'label_en': 'Tab/window lost focus',
        'label_ar': 'فقد التبويب التركيز',
        'why_en': 'Helps detect switching to other tabs during a timed exam.',
        'why_ar': 'يساعد على اكتشاف التنقل بين التبويبات أثناء الاختبار.',
        'severity': 'warn',
    },
    'tab_focus': {
        'label_en': 'Tab/window regained focus',
        'label_ar': 'استعاد التبويب التركيز',
        'why_en': 'Pairs with tab_blur so we can show fair time-away totals.',
        'why_ar': 'يقترن مع فقدان التركيز لعرض إجمالي وقت الانصراف بإنصاف.',
        'severity': 'info',
    },
    'paste_detected': {
        'label_en': 'Paste into an answer field',
        'label_ar': 'لصق في حقل الإجابة',
        'why_en': 'Large pastes can indicate copying from external sources.',
        'why_ar': 'قد يشير اللصق الكبير إلى نسخ من مصادر خارجية.',
        'severity': 'warn',
    },
    'copy_detected': {
        'label_en': 'Copy from the question area',
        'label_ar': 'نسخ من منطقة السؤال',
        'why_en': 'Tracks copying of question text to outside tools.',
        'why_ar': 'يتتبع نسخ نص السؤال إلى أدوات خارجية.',
        'severity': 'info',
    },
    'fullscreen_exit': {
        'label_en': 'Left fullscreen mode',
        'label_ar': 'الخروج من وضع ملء الشاشة',
        'why_en': 'Some institutions require fullscreen during high-stakes exams.',
        'why_ar': 'تشترط بعض المؤسسات وضع ملء الشاشة أثناء الاختبارات.',
        'severity': 'info',
    },
    'window_resize': {
        'label_en': 'Window resized significantly',
        'label_ar': 'تغيير حجم النافذة بشكل كبير',
        'why_en': 'May indicate opening another app side-by-side.',
        'why_ar': 'قد يشير إلى فتح تطبيق آخر جنبًا إلى جنب.',
        'severity': 'info',
    },
    'time_anomaly': {
        'label_en': 'Unusual gap between answers',
        'label_ar': 'فجوة غير اعتيادية بين الإجابات',
        'why_en': 'Long idle gaps are reported (no keystroke timing collected).',
        'why_ar': 'يتم الإبلاغ عن فجوات الخمول الطويلة دون تسجيل توقيت الضغطات.',
        'severity': 'info',
    },
    'navigation_attempt': {
        'label_en': 'Tried to leave the exam page',
        'label_ar': 'محاولة مغادرة صفحة الاختبار',
        'why_en': 'Browser back/forward or refresh attempts during the attempt.',
        'why_ar': 'محاولات الرجوع أو التحديث أثناء الاختبار.',
        'severity': 'warn',
    },
}

ALLOWED_EVENT_TYPES = set(PROCTORING_SIGNALS.keys())


def list_proctoring_signals() -> List[Dict[str, Any]]:
    """Return the public, transparent list of signals as JSON-friendly dicts."""
    return [
        {
            'code': code,
            'label_en': meta['label_en'],
            'label_ar': meta['label_ar'],
            'why_en': meta['why_en'],
            'why_ar': meta['why_ar'],
            'severity': meta['severity'],
        }
        for code, meta in PROCTORING_SIGNALS.items()
    ]


# ---------------------------------------------------------------------------
# Spaced retention scheduler
# ---------------------------------------------------------------------------

# Skills are considered "mastered" once they reach this level.
RETENTION_MASTERY_LEVEL = 2

# Half-life (in days) used for the exponential decay of confidence.
RETENTION_HALF_LIFE_DAYS = 21.0

# Minimum decayed confidence we will tolerate before scheduling a review.
RETENTION_REVIEW_CONFIDENCE = 0.6

# How many questions to put in a retention quiz.
RETENTION_QUIZ_SIZE = 5


def compute_decay(confidence: float, last_evidence_at: Optional[datetime],
                  now: Optional[datetime] = None) -> float:
    """Exponential decay of confidence with `RETENTION_HALF_LIFE_DAYS`.

    Returns a value in [0, confidence]. If we have no evidence, returns 0.
    """
    if confidence is None or confidence <= 0 or last_evidence_at is None:
        return 0.0
    now = now or datetime.utcnow()
    days = max(0.0, (now - last_evidence_at).total_seconds() / 86400.0)
    return float(confidence) * math.pow(0.5, days / RETENTION_HALF_LIFE_DAYS)


def get_due_retention_items(user_id: str, db, now: Optional[datetime] = None,
                            limit: int = 10) -> List[Dict[str, Any]]:
    """Return the retention quiz suggestions for a learner.

    A skill is *due* when:
      - `LearnerSkill.level >= RETENTION_MASTERY_LEVEL`
      - decayed confidence < `RETENTION_REVIEW_CONFIDENCE`
      - last evidence is at least 7 days old
    """
    from app.models import LearnerSkill, Skill

    now = now or datetime.utcnow()
    rows = (
        db.session.query(LearnerSkill, Skill)
        .join(Skill, Skill.id == LearnerSkill.skill_id)
        .filter(LearnerSkill.user_id == user_id)
        .filter(LearnerSkill.level >= RETENTION_MASTERY_LEVEL)
        .all()
    )

    due: List[Dict[str, Any]] = []
    for ls, skill in rows:
        if not ls.last_evidence_at:
            continue
        age_days = (now - ls.last_evidence_at).total_seconds() / 86400.0
        if age_days < 7:
            continue
        decayed = compute_decay(ls.confidence or 0.0, ls.last_evidence_at, now)
        if decayed >= RETENTION_REVIEW_CONFIDENCE:
            continue
        due.append({
            'skill_id': skill.id,
            'skill_code': getattr(skill, 'code', None),
            'skill_name': getattr(skill, 'name', None) or getattr(skill, 'title', None),
            'skill_name_ar': getattr(skill, 'name_ar', None) or getattr(skill, 'title_ar', None),
            'mastered_level': ls.level,
            'current_confidence': round(float(ls.confidence or 0.0), 3),
            'decayed_confidence': round(decayed, 3),
            'days_since_evidence': round(age_days, 1),
            'suggested_question_count': RETENTION_QUIZ_SIZE,
            'reason_en': (
                f'You mastered this {age_days:.0f} days ago — a quick refresher '
                f'will keep it sharp.'
            ),
            'reason_ar': (
                f'أتقنت هذه المهارة قبل {age_days:.0f} يومًا — مراجعة سريعة '
                f'ستحافظ على تمكنك.'
            ),
        })

    # Show the most-decayed first.
    due.sort(key=lambda d: d['decayed_confidence'])
    return due[:limit]


# ---------------------------------------------------------------------------
# Rubric grading
# ---------------------------------------------------------------------------

DEFAULT_RUBRIC: List[Dict[str, Any]] = [
    {
        'name': 'Accuracy',
        'name_ar': 'الدقة',
        'max': 5,
        'description': 'Answer is factually correct and addresses the question.',
        'description_ar': 'الإجابة صحيحة وقائمة على الموضوع.',
    },
    {
        'name': 'Completeness',
        'name_ar': 'الاكتمال',
        'max': 5,
        'description': 'Covers all required parts of the question.',
        'description_ar': 'يغطي جميع جوانب السؤال المطلوبة.',
    },
    {
        'name': 'Clarity',
        'name_ar': 'الوضوح',
        'max': 5,
        'description': 'Well-structured and easy to follow.',
        'description_ar': 'منظمة وسهلة الفهم.',
    },
]


def _heuristic_grade(answer: str, rubric: List[Dict[str, Any]],
                     reference: Optional[str] = None) -> Dict[str, Any]:
    """Transparent fallback grader used when no AI key is configured.

    The heuristic is intentionally simple and explainable:
      - Accuracy: keyword overlap with the reference answer (if any).
      - Completeness: scaled by answer length up to ~120 words.
      - Clarity: rewards sentence-like punctuation density.
    """
    answer = (answer or '').strip()
    words = re.findall(r"\w+", answer.lower())
    word_count = len(words)
    sentences = max(1, len(re.findall(r"[.!?؟]", answer)))

    # Accuracy
    if reference:
        ref_words = set(re.findall(r"\w+", reference.lower()))
        overlap = len(set(words) & ref_words)
        acc_ratio = min(1.0, overlap / max(5, len(ref_words) // 3))
    else:
        acc_ratio = min(1.0, word_count / 60.0)

    completeness_ratio = min(1.0, word_count / 120.0)
    clarity_ratio = min(1.0, sentences / 4.0)

    ratios = {
        'accuracy': acc_ratio,
        'completeness': completeness_ratio,
        'clarity': clarity_ratio,
    }

    criteria_out: List[Dict[str, Any]] = []
    total = 0.0
    max_total = 0.0
    for crit in rubric:
        name = (crit.get('name') or '').lower()
        ratio = ratios.get(name, (acc_ratio + completeness_ratio + clarity_ratio) / 3.0)
        max_pts = float(crit.get('max', 5))
        score = round(ratio * max_pts, 2)
        total += score
        max_total += max_pts
        criteria_out.append({
            'name': crit.get('name'),
            'name_ar': crit.get('name_ar'),
            'score': score,
            'max': max_pts,
            'feedback': _heuristic_feedback_en(name, ratio, word_count),
            'feedback_ar': _heuristic_feedback_ar(name, ratio, word_count),
        })

    return {
        'criteria': criteria_out,
        'total': round(total, 2),
        'max_total': round(max_total, 2),
        'percentage': round((total / max_total * 100) if max_total else 0.0, 1),
        'comment': (
            f'Heuristic grade based on {word_count} words across {sentences} '
            f'sentence(s). For higher precision, configure an AI provider.'
        ),
        'comment_ar': (
            f'تقييم تلقائي مبني على {word_count} كلمة و{sentences} جملة. '
            f'لتقييم أدق، فعّل مزود الذكاء الاصطناعي.'
        ),
        'grader': 'heuristic',
    }


def _heuristic_feedback_en(name: str, ratio: float, word_count: int) -> str:
    if ratio >= 0.85:
        return 'Strong — meets the criterion well.'
    if ratio >= 0.6:
        return 'Solid — minor gaps worth tightening.'
    if ratio >= 0.3:
        return f'Partial — expand your answer (currently {word_count} words).'
    return 'Needs work — add more detail and direct evidence.'


def _heuristic_feedback_ar(name: str, ratio: float, word_count: int) -> str:
    if ratio >= 0.85:
        return 'ممتاز — يستوفي المعيار بوضوح.'
    if ratio >= 0.6:
        return 'جيد — مع وجود فجوات بسيطة يمكن معالجتها.'
    if ratio >= 0.3:
        return f'جزئي — وسّع إجابتك (حاليًا {word_count} كلمة).'
    return 'يحتاج تطوير — أضف مزيدًا من التفاصيل والأدلة.'


class RubricGrader:
    """Grade short-answer / essay responses against a rubric.

    Tries an AI provider first (if `ai_service` is supplied and configured)
    and falls back to the transparent heuristic grader otherwise.
    """

    def __init__(self, ai_service: Any = None):
        self.ai_service = ai_service

    def grade(self, question: str, answer: str,
              rubric: Optional[List[Dict[str, Any]]] = None,
              reference: Optional[str] = None,
              language: str = 'en') -> Dict[str, Any]:
        rubric = rubric or DEFAULT_RUBRIC
        if not (answer or '').strip():
            return {
                'criteria': [
                    {
                        'name': c.get('name'),
                        'name_ar': c.get('name_ar'),
                        'score': 0,
                        'max': float(c.get('max', 5)),
                        'feedback': 'No answer provided.',
                        'feedback_ar': 'لم تُقدَّم إجابة.',
                    }
                    for c in rubric
                ],
                'total': 0.0,
                'max_total': float(sum(c.get('max', 5) for c in rubric)),
                'percentage': 0.0,
                'comment': 'No answer provided.',
                'comment_ar': 'لم تُقدَّم إجابة.',
                'grader': 'heuristic',
            }

        ai_result = self._try_ai_grade(question, answer, rubric, reference, language)
        if ai_result is not None:
            return ai_result
        return _heuristic_grade(answer, rubric, reference)

    # -- internal -----------------------------------------------------------

    def _try_ai_grade(self, question: str, answer: str,
                      rubric: List[Dict[str, Any]], reference: Optional[str],
                      language: str) -> Optional[Dict[str, Any]]:
        if not self.ai_service:
            return None
        try:
            prompt = self._build_prompt(question, answer, rubric, reference)
            # Best-effort across multiple ai_service shapes.
            text: Optional[str] = None
            if hasattr(self.ai_service, 'chat'):
                try:
                    resp = self.ai_service.chat(
                        'openai', prompt, '', [], [], '', language
                    )
                    if isinstance(resp, dict):
                        text = resp.get('text') or resp.get('response')
                except Exception:
                    text = None
            if not text:
                return None
            return self._parse_ai_response(text, rubric)
        except Exception:
            return None

    def _build_prompt(self, question: str, answer: str,
                      rubric: List[Dict[str, Any]],
                      reference: Optional[str]) -> str:
        rubric_lines = []
        for c in rubric:
            rubric_lines.append(
                f"- {c.get('name')} (max {c.get('max', 5)}): {c.get('description', '')}"
            )
        ref_block = f"\nReference answer:\n{reference}\n" if reference else ''
        return (
            "You are an exam grader. Grade the student's answer against the rubric. "
            "Respond ONLY with JSON of shape "
            '{"criteria":[{"name":str,"score":number,"max":number,'
            '"feedback":str,"feedback_ar":str}], '
            '"total":number,"max_total":number,"comment":str,"comment_ar":str}. '
            "Provide bilingual feedback (English and Arabic).\n\n"
            f"Question:\n{question}\n\nStudent answer:\n{answer}\n"
            f"{ref_block}\nRubric:\n" + '\n'.join(rubric_lines)
        )

    def _parse_ai_response(self, text: str,
                           rubric: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except Exception:
            return None
        criteria = data.get('criteria') or []
        if not isinstance(criteria, list) or not criteria:
            return None
        # Backfill name_ar from rubric definitions when missing.
        ar_lookup = {c.get('name'): c.get('name_ar') for c in rubric}
        for c in criteria:
            c.setdefault('name_ar', ar_lookup.get(c.get('name')))
            c.setdefault('feedback_ar', '')
        total = float(data.get('total', sum(float(c.get('score', 0)) for c in criteria)))
        max_total = float(
            data.get('max_total', sum(float(c.get('max', 5)) for c in criteria))
        )
        return {
            'criteria': criteria,
            'total': round(total, 2),
            'max_total': round(max_total, 2),
            'percentage': round((total / max_total * 100) if max_total else 0.0, 1),
            'comment': data.get('comment', ''),
            'comment_ar': data.get('comment_ar', ''),
            'grader': 'ai',
        }


# ---------------------------------------------------------------------------
# Flagging / explainability
# ---------------------------------------------------------------------------

# Thresholds are conservative on purpose so we under-flag rather than over-flag.
FLAG_RULES = [
    {
        'code': 'many_tab_blurs',
        'event_type': 'tab_blur',
        'threshold': 4,
        'description_en': 'The exam tab lost focus several times.',
        'description_ar': 'فقد تبويب الاختبار التركيز عدة مرات.',
    },
    {
        'code': 'large_paste',
        'event_type': 'paste_detected',
        'threshold': 1,
        'min_chars': 200,
        'description_en': 'A large paste (200+ characters) was detected in an answer.',
        'description_ar': 'تم رصد لصق كبير (200 حرف فأكثر) في الإجابة.',
    },
    {
        'code': 'frequent_pastes',
        'event_type': 'paste_detected',
        'threshold': 3,
        'description_en': 'Pasting happened multiple times during the attempt.',
        'description_ar': 'حدث اللصق عدة مرات خلال المحاولة.',
    },
    {
        'code': 'fullscreen_exit',
        'event_type': 'fullscreen_exit',
        'threshold': 1,
        'description_en': 'The student left fullscreen mode.',
        'description_ar': 'غادر الطالب وضع ملء الشاشة.',
    },
    {
        'code': 'navigation_attempts',
        'event_type': 'navigation_attempt',
        'threshold': 1,
        'description_en': 'Browser navigation away from the exam was attempted.',
        'description_ar': 'تمت محاولة التنقل خارج الاختبار.',
    },
]


def evaluate_flags(events: List[Any]) -> List[Dict[str, Any]]:
    """Return a list of human-readable flag entries for the given events.

    `events` may be ORM rows (with `event_type`/`payload`) or plain dicts.
    """
    counts: Dict[str, int] = {}
    max_paste_chars = 0
    for ev in events:
        et = getattr(ev, 'event_type', None) if not isinstance(ev, dict) else ev.get('event_type')
        payload = getattr(ev, 'payload', None) if not isinstance(ev, dict) else ev.get('payload')
        if not et:
            continue
        counts[et] = counts.get(et, 0) + 1
        if et == 'paste_detected' and isinstance(payload, dict):
            try:
                chars = int(payload.get('chars') or 0)
            except (TypeError, ValueError):
                chars = 0
            if chars > max_paste_chars:
                max_paste_chars = chars

    flags: List[Dict[str, Any]] = []
    for rule in FLAG_RULES:
        et = rule['event_type']
        count = counts.get(et, 0)
        if count < rule['threshold']:
            continue
        if rule.get('min_chars') and max_paste_chars < rule['min_chars']:
            continue
        flags.append({
            'code': rule['code'],
            'event_type': et,
            'evidence_count': count,
            'description_en': rule['description_en'],
            'description_ar': rule['description_ar'],
        })
    return flags
