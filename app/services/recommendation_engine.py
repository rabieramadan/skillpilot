"""
AI-Driven Personalized Learning Recommendation Engine

This module provides intelligent recommendations based on student performance,
learning patterns, and course content to optimize the learning experience.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import os

try:
    from app.models import (
        db, User, Course, Enrollment, Assignment, AssignmentSubmission,
        Exam, ExamResult, ExamQuestion, LearningProgress, LearningRecommendation,
        WeekMaterial, CourseWeek
    )
    HAS_DB = True
except ImportError:
    db = None
    User = Course = Enrollment = Assignment = AssignmentSubmission = None
    Exam = ExamResult = ExamQuestion = LearningProgress = LearningRecommendation = None
    WeekMaterial = CourseWeek = None
    HAS_DB = False


def _normalize_topic(t):
    return str(t).strip().lower() if t is not None else ''


class RecommendationEngine:
    """AI-powered recommendation engine for personalized learning paths."""
    
    DIFFICULTY_LEVELS = ['beginner', 'intermediate', 'advanced', 'expert']
    
    def __init__(self, user_id: str, course_id: str = None):
        self.user_id = user_id
        self.course_id = course_id
        self.user = None
        self.performance_data = {}
        
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze student's overall performance across all metrics."""
        if not db:
            return self._get_mock_performance()
            
        analysis = {
            'user_id': self.user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'overall_score': 0,
            'strengths': [],
            'weaknesses': [],
            'learning_velocity': 'normal',
            'engagement_level': 'active',
            'completion_rate': 0,
            'average_assignment_score': 0,
            'average_exam_score': 0,
            'materials_progress': 0,
            'recommended_focus_areas': [],
            'suggested_pace': 'maintain'
        }
        
        try:
            self.user = User.query.get(self.user_id)
            if not self.user:
                return analysis
                
            enrollments = Enrollment.query.filter_by(
                user_id=self.user_id, 
                status='active'
            ).all()
            
            if self.course_id:
                course_ids = [self.course_id]
            else:
                course_ids = [e.course_id for e in enrollments]
            
            assignment_scores = []
            exam_scores = []
            completed_materials = 0
            total_materials = 0
            topic_performance = {}
            
            submissions = []
            progress = []
            for course_id in course_ids:
                # Assignments belong to a week; week belongs to course.
                course_week_ids = [
                    w.id for w in CourseWeek.query.filter_by(course_id=course_id).all()
                ] if CourseWeek else []

                if course_week_ids:
                    course_subs = AssignmentSubmission.query.join(
                        Assignment, AssignmentSubmission.assignment_id == Assignment.id
                    ).filter(
                        AssignmentSubmission.user_id == self.user_id,
                        Assignment.week_id.in_(course_week_ids)
                    ).all()
                else:
                    course_subs = []
                submissions.extend(course_subs)
                for sub in course_subs:
                    if sub.score is not None:
                        assignment_scores.append(sub.score)

                results = ExamResult.query.filter(
                    ExamResult.user_id == self.user_id,
                    ExamResult.exam.has(course_id=course_id)
                ).all()
                for result in results:
                    if result.percentage is not None:
                        exam_scores.append(result.percentage)

                # Per-question topic mastery from exam answers.
                for result in results:
                    answers = result.answers or {}
                    if not isinstance(answers, dict):
                        continue
                    questions = ExamQuestion.query.filter(
                        ExamQuestion.exam_id == result.exam_id
                    ).all()
                    for q in questions:
                        topic = _normalize_topic(q.topic)
                        if not topic:
                            continue
                        student_ans = answers.get(q.id)
                        if student_ans is None:
                            continue
                        correct = (
                            str(student_ans).strip().lower()
                            == str(q.correct_answer or '').strip().lower()
                        )
                        topic_performance.setdefault(topic, []).append({
                            'mastery': 1.0 if correct else 0.0,
                            'time_spent': 0,
                        })

                # Material progress + topic mastery from learning progress.
                if WeekMaterial and course_week_ids:
                    course_progress = LearningProgress.query.join(
                        WeekMaterial, LearningProgress.material_id == WeekMaterial.id
                    ).filter(
                        LearningProgress.user_id == self.user_id,
                        WeekMaterial.week_id.in_(course_week_ids)
                    ).all()
                    course_total_materials = WeekMaterial.query.filter(
                        WeekMaterial.week_id.in_(course_week_ids)
                    ).count()
                else:
                    course_progress = []
                    course_total_materials = 0

                progress.extend(course_progress)
                total_materials += course_total_materials
                for p in course_progress:
                    pct = float(p.progress_percent or 0)
                    is_complete = (p.status == 'completed') or pct >= 100.0
                    if is_complete:
                        completed_materials += 1
                    mastery = min(1.0, max(0.0, pct / 100.0))
                    material = WeekMaterial.query.get(p.material_id) if WeekMaterial else None
                    topics = (material.topics if material else None) or []
                    if isinstance(topics, str):
                        topics = [topics]
                    for t in topics:
                        topic = _normalize_topic(t)
                        if not topic:
                            continue
                        topic_performance.setdefault(topic, []).append({
                            'mastery': mastery,
                            'time_spent': int((p.time_spent_seconds or 0) / 60),
                        })
            
            if assignment_scores:
                analysis['average_assignment_score'] = sum(assignment_scores) / len(assignment_scores)
                
            if exam_scores:
                analysis['average_exam_score'] = sum(exam_scores) / len(exam_scores)
                
            if total_materials > 0:
                analysis['materials_progress'] = (completed_materials / total_materials) * 100
                analysis['completion_rate'] = analysis['materials_progress']
                
            analysis['overall_score'] = self._calculate_overall_score(
                analysis['average_assignment_score'],
                analysis['average_exam_score'],
                analysis['materials_progress']
            )
            
            for topic, perf in topic_performance.items():
                avg_mastery = sum(p['mastery'] for p in perf) / len(perf) if perf else 0
                if avg_mastery >= 0.8:
                    analysis['strengths'].append(topic)
                elif avg_mastery < 0.5:
                    analysis['weaknesses'].append(topic)
                    
            analysis['learning_velocity'] = self._calculate_velocity(progress)
            analysis['engagement_level'] = self._calculate_engagement(submissions, progress)
            analysis['suggested_pace'] = self._suggest_pace(analysis)
            analysis['recommended_focus_areas'] = self._identify_focus_areas(analysis)
            
        except Exception as e:
            print(f"Error analyzing performance: {e}")
            
        self.performance_data = analysis
        return analysis
    
    def _calculate_overall_score(self, assignment_avg: float, exam_avg: float, progress: float) -> float:
        """Calculate weighted overall score."""
        weights = {'assignments': 0.4, 'exams': 0.4, 'progress': 0.2}
        score = (
            (assignment_avg * weights['assignments']) +
            (exam_avg * weights['exams']) +
            (progress * weights['progress'])
        )
        return round(score, 2)
    
    def _calculate_velocity(self, progress_list: List) -> str:
        """Determine learning velocity based on progress history."""
        if not progress_list:
            return 'normal'
            
        cutoff = datetime.utcnow() - timedelta(days=7)
        recent_progress = [
            p for p in progress_list
            if getattr(p, 'last_accessed', None) and p.last_accessed > cutoff
        ]
        
        if len(recent_progress) > 5:
            return 'fast'
        elif len(recent_progress) > 2:
            return 'normal'
        else:
            return 'slow'
    
    def _calculate_engagement(self, submissions: List, progress: List) -> str:
        """Calculate engagement level based on activity."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        recent_submissions = len([
            s for s in submissions
            if getattr(s, 'submitted_at', None) and s.submitted_at > cutoff
        ])
        recent_progress = len([
            p for p in progress
            if getattr(p, 'last_accessed', None) and p.last_accessed > cutoff
        ])
        
        total_activity = recent_submissions + recent_progress
        
        if total_activity > 10:
            return 'very_active'
        elif total_activity > 5:
            return 'active'
        elif total_activity > 0:
            return 'moderate'
        else:
            return 'inactive'
    
    def _suggest_pace(self, analysis: Dict) -> str:
        """Suggest learning pace adjustment."""
        if analysis['overall_score'] >= 85 and analysis['learning_velocity'] == 'fast':
            return 'accelerate'
        elif analysis['overall_score'] < 60 or analysis['learning_velocity'] == 'slow':
            return 'slow_down'
        else:
            return 'maintain'
    
    def _identify_focus_areas(self, analysis: Dict) -> List[str]:
        """Identify areas that need more attention."""
        focus = []
        
        if analysis['average_assignment_score'] < 70:
            focus.append('practice_assignments')
        if analysis['average_exam_score'] < 70:
            focus.append('exam_preparation')
        if analysis['materials_progress'] < 50:
            focus.append('complete_materials')
            
        focus.extend(analysis['weaknesses'][:3])
        return focus
    
    def generate_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Generate personalized learning recommendations."""
        if not self.performance_data:
            self.analyze_performance()
            
        recommendations = []
        
        if self.performance_data.get('suggested_pace') == 'accelerate':
            recommendations.append({
                'type': 'pace',
                'priority': 'medium',
                'title': 'Ready for a Challenge',
                'description': 'Your performance suggests you can handle more advanced content. Consider exploring optional advanced materials.',
                'action': 'view_advanced_content',
                'metadata': {}
            })
        elif self.performance_data.get('suggested_pace') == 'slow_down':
            recommendations.append({
                'type': 'pace',
                'priority': 'high',
                'title': 'Review Fundamentals',
                'description': 'Taking time to review earlier materials will help strengthen your foundation.',
                'action': 'review_materials',
                'metadata': {}
            })
            
        for weakness in self.performance_data.get('weaknesses', [])[:2]:
            recommendations.append({
                'type': 'focus_area',
                'priority': 'high',
                'title': f'Improve in {weakness.replace("_", " ").title()}',
                'description': f'This topic needs additional practice. We recommend reviewing related materials and completing extra exercises.',
                'action': 'practice_topic',
                'metadata': {'topic': weakness}
            })
            
        if self.performance_data.get('materials_progress', 0) < 80:
            recommendations.append({
                'type': 'completion',
                'priority': 'medium',
                'title': 'Complete Course Materials',
                'description': f'You\'ve completed {self.performance_data.get("materials_progress", 0):.0f}% of course materials. Finish the remaining content to ensure comprehensive understanding.',
                'action': 'view_materials',
                'metadata': {}
            })
            
        if self.performance_data.get('engagement_level') in ['moderate', 'inactive']:
            recommendations.append({
                'type': 'engagement',
                'priority': 'medium',
                'title': 'Stay on Track',
                'description': 'Regular practice helps retain knowledge better. Try to spend at least 30 minutes daily on course materials.',
                'action': 'set_study_schedule',
                'metadata': {}
            })
            
        for strength in self.performance_data.get('strengths', [])[:1]:
            recommendations.append({
                'type': 'strength',
                'priority': 'low',
                'title': f'Excellent in {strength.replace("_", " ").title()}',
                'description': 'You\'re excelling in this area! Consider helping other students or exploring advanced applications.',
                'action': 'explore_advanced',
                'metadata': {'topic': strength}
            })
            
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
        
        return recommendations[:limit]
    
    def get_next_suggested_content(self) -> Dict[str, Any]:
        """Get the next recommended content for the student."""
        if not db:
            return {
                'type': 'material',
                'title': 'Continue Learning',
                'description': 'Pick up where you left off',
                'action_url': '/courses'
            }
            
        try:
            if not self.course_id:
                return {'type': 'no_course', 'message': 'No course selected'}
                
            weeks = CourseWeek.query.filter_by(course_id=self.course_id).order_by(CourseWeek.week_number).all()
            
            for week in weeks:
                materials = WeekMaterial.query.filter_by(week_id=week.id).order_by(WeekMaterial.order_index).all()
                
                for material in materials:
                    progress = LearningProgress.query.filter_by(
                        user_id=self.user_id,
                        course_id=self.course_id,
                        material_id=material.id
                    ).first()
                    
                    if not progress or not progress.completed:
                        return {
                            'type': 'material',
                            'id': material.id,
                            'title': material.title,
                            'description': material.description or 'Continue with this material',
                            'week': week.week_number,
                            'material_type': material.material_type,
                            'action_url': f'/courses/{self.course_id}/weeks/{week.week_number}/materials/{material.id}'
                        }
                        
                assignments = Assignment.query.filter_by(
                    course_id=self.course_id,
                    week_number=week.week_number
                ).order_by(Assignment.due_date).all()
                
                for assignment in assignments:
                    submission = AssignmentSubmission.query.filter_by(
                        user_id=self.user_id,
                        assignment_id=assignment.id
                    ).first()
                    
                    if not submission:
                        return {
                            'type': 'assignment',
                            'id': assignment.id,
                            'title': assignment.title,
                            'description': assignment.description or 'Complete this assignment',
                            'week': week.week_number,
                            'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                            'action_url': f'/courses/{self.course_id}/assignments/{assignment.id}'
                        }
            
            return {
                'type': 'completed',
                'title': 'Course Completed!',
                'description': 'You have completed all materials and assignments.',
                'action_url': f'/courses/{self.course_id}/certificate'
            }
            
        except Exception as e:
            print(f"Error getting next content: {e}")
            return {'type': 'error', 'message': str(e)}
    
    def save_recommendations(self) -> List[str]:
        """Save generated recommendations to database."""
        if not db:
            return []
            
        recommendations = self.generate_recommendations()
        saved_ids = []
        
        try:
            for rec in recommendations:
                existing = LearningRecommendation.query.filter_by(
                    user_id=self.user_id,
                    course_id=self.course_id,
                    recommendation_type=rec['type'],
                    status='pending'
                ).first()
                
                if existing:
                    continue
                    
                db_rec = LearningRecommendation(
                    user_id=self.user_id,
                    course_id=self.course_id,
                    recommendation_type=rec['type'],
                    title=rec['title'],
                    description=rec['description'],
                    priority=rec['priority'],
                    action=rec['action'],
                    metadata=rec.get('metadata', {}),
                    status='pending'
                )
                db.session.add(db_rec)
                db.session.flush()
                saved_ids.append(db_rec.id)
                
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving recommendations: {e}")
            
        return saved_ids
    
    def _get_mock_performance(self) -> Dict[str, Any]:
        """Return mock performance data for testing."""
        return {
            'user_id': self.user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'overall_score': 75,
            'strengths': ['prompt_engineering', 'ai_basics'],
            'weaknesses': ['advanced_llm_concepts'],
            'learning_velocity': 'normal',
            'engagement_level': 'active',
            'completion_rate': 65,
            'average_assignment_score': 78,
            'average_exam_score': 72,
            'materials_progress': 65,
            'recommended_focus_areas': ['complete_materials', 'advanced_llm_concepts'],
            'suggested_pace': 'maintain'
        }


class AdaptiveContentEngine:
    """Engine for adapting course content based on student performance."""
    
    def __init__(self, course_id: str):
        self.course_id = course_id
        
    def get_difficulty_adjusted_content(self, user_id: str, content_type: str = 'material') -> List[Dict]:
        """Get content adjusted to student's current level."""
        engine = RecommendationEngine(user_id, self.course_id)
        performance = engine.analyze_performance()
        
        if performance['overall_score'] >= 85:
            target_difficulty = 'advanced'
        elif performance['overall_score'] >= 70:
            target_difficulty = 'intermediate'
        else:
            target_difficulty = 'beginner'
            
        return self._filter_content_by_difficulty(content_type, target_difficulty)
    
    def _filter_content_by_difficulty(self, content_type: str, difficulty: str) -> List[Dict]:
        """Filter content by difficulty level."""
        content = []
        
        if not db:
            return content
            
        try:
            if content_type == 'material':
                materials = WeekMaterial.query.filter(
                    WeekMaterial.week.has(course_id=self.course_id),
                    WeekMaterial.difficulty == difficulty
                ).all()
                
                content = [{
                    'id': m.id,
                    'title': m.title,
                    'type': m.material_type,
                    'difficulty': m.difficulty,
                    'week': m.week.week_number if m.week else None
                } for m in materials]
                
            elif content_type == 'assignment':
                assignments = Assignment.query.filter_by(
                    course_id=self.course_id,
                    difficulty=difficulty
                ).all()
                
                content = [{
                    'id': a.id,
                    'title': a.title,
                    'difficulty': a.difficulty,
                    'week': a.week_number
                } for a in assignments]
                
        except Exception as e:
            print(f"Error filtering content: {e}")
            
        return content
    
    def generate_study_plan(self, user_id: str, weeks: int = 4) -> Dict[str, Any]:
        """Generate a personalized study plan."""
        engine = RecommendationEngine(user_id, self.course_id)
        performance = engine.analyze_performance()
        
        plan = {
            'user_id': user_id,
            'course_id': self.course_id,
            'duration_weeks': weeks,
            'generated_at': datetime.utcnow().isoformat(),
            'current_level': self._determine_level(performance['overall_score']),
            'target_level': self._next_level(performance['overall_score']),
            'weekly_goals': [],
            'focus_areas': performance.get('recommended_focus_areas', []),
            'estimated_hours_per_week': self._estimate_hours(performance)
        }
        
        for week_num in range(1, weeks + 1):
            week_goal = {
                'week': week_num,
                'objectives': [],
                'materials': [],
                'assignments': [],
                'estimated_hours': plan['estimated_hours_per_week']
            }
            
            if week_num <= len(plan['focus_areas']):
                focus = plan['focus_areas'][week_num - 1]
                week_goal['objectives'].append(f"Improve understanding of {focus}")
                
            week_goal['objectives'].append(f"Complete week {week_num} materials")
            
            if week_num % 2 == 0:
                week_goal['objectives'].append("Take practice quiz")
                
            plan['weekly_goals'].append(week_goal)
            
        return plan
    
    def _determine_level(self, score: float) -> str:
        """Determine current proficiency level."""
        if score >= 90:
            return 'expert'
        elif score >= 75:
            return 'advanced'
        elif score >= 60:
            return 'intermediate'
        else:
            return 'beginner'
    
    def _next_level(self, score: float) -> str:
        """Determine target proficiency level."""
        current = self._determine_level(score)
        levels = ['beginner', 'intermediate', 'advanced', 'expert']
        idx = levels.index(current)
        return levels[min(idx + 1, len(levels) - 1)]
    
    def _estimate_hours(self, performance: Dict) -> int:
        """Estimate recommended weekly study hours."""
        if performance.get('learning_velocity') == 'slow':
            return 10
        elif performance.get('learning_velocity') == 'fast':
            return 5
        else:
            return 7


def get_user_recommendations(user_id: str, course_id: str = None, limit: int = 5) -> List[Dict]:
    """Convenience function to get recommendations for a user."""
    engine = RecommendationEngine(user_id, course_id)
    return engine.generate_recommendations(limit)


def analyze_user_performance(user_id: str, course_id: str = None) -> Dict:
    """Convenience function to analyze user performance."""
    engine = RecommendationEngine(user_id, course_id)
    return engine.analyze_performance()


def get_study_plan(user_id: str, course_id: str, weeks: int = 4) -> Dict:
    """Convenience function to generate a study plan."""
    engine = AdaptiveContentEngine(course_id)
    return engine.generate_study_plan(user_id, weeks)


# ============================================================
# Phase 2 — Adaptive engine: skill recompute + path re-ranking
# ============================================================

class AdaptiveEngine:
    """
    Phase 2 adaptive engine.

    Consumes LearningProgress + LearnerSkill + StudentPerformanceSnapshot
    (and ExamResult / AssignmentSubmission when available) to:
      1) recompute LearnerSkill levels for a learner, and
      2) re-rank PathSteps so weak skills/topics surface first.

    Designed to be safe in environments where some tables/columns aren't
    populated yet — every block is wrapped to fail soft and never break
    the existing chat or recommendations flow.
    """

    def __init__(self, user_id: str, course_id: str = None):
        self.user_id = user_id
        self.course_id = course_id

    # ---------- public API -----------------------------------------------

    def recompute_skill_levels(self, source: str = 'adaptive') -> Dict[str, Any]:
        """Walk recent evidence and update LearnerSkill rows.

        Returns a summary dict: {updated: [...], created: [...], skipped: int}.
        Each entry in `updated`/`created` includes previous_level / new_level
        / delta so callers can surface "skills you grew" deltas.
        Also writes a LearnerSkillHistory row for every change.
        """
        result = {'updated': [], 'created': [], 'skipped': 0,
                  'overall_score': None}
        if not db:
            return result

        try:
            from app.models import (
                LearnerSkill, Skill, WeekMaterial, CourseWeek,
                LearningProgress, StudentPerformanceSnapshot,
                LearnerSkillHistory,
            )

            perf = RecommendationEngine(self.user_id, self.course_id).analyze_performance()
            result['overall_score'] = perf.get('overall_score', 0)
            overall = float(perf.get('overall_score') or 0)

            # Aggregate evidence by topic across the learner's progress.
            # We collect: (1) topics from completed materials; (2) topics
            # from materials with significant time spent.
            topic_evidence: Dict[str, Dict[str, float]] = {}

            progress_rows = LearningProgress.query.filter_by(
                user_id=self.user_id
            ).all()

            for p in progress_rows:
                try:
                    material = WeekMaterial.query.get(p.material_id)
                    if not material:
                        continue
                    if self.course_id:
                        wk = CourseWeek.query.get(material.week_id)
                        if not wk or wk.course_id != self.course_id:
                            continue
                    topics = material.topics or []
                    completed = (p.status == 'completed')
                    weight = 1.0 if completed else min(
                        (p.progress_percent or 0) / 100.0, 0.6
                    )
                    if weight <= 0:
                        continue
                    for topic in topics:
                        slot = topic_evidence.setdefault(
                            str(topic).lower().strip(),
                            {'weight': 0.0, 'count': 0}
                        )
                        slot['weight'] += weight
                        slot['count'] += 1
                except Exception:
                    continue

            # Map topic -> Skill via skill.code or skill.name (case-insensitive)
            updated, created = [], []
            for topic, ev in topic_evidence.items():
                if not topic:
                    continue
                skill = (
                    Skill.query.filter(db.func.lower(Skill.code) == topic).first()
                    or Skill.query.filter(db.func.lower(Skill.name) == topic).first()
                )
                if not skill:
                    result['skipped'] += 1
                    continue

                level_max = skill.level_max or 5
                # Combine evidence count + overall score into a 0..level_max level.
                # Each unit of evidence is worth ~1 level, capped by overall score band.
                score_cap = max(1, int(round((overall / 100.0) * level_max)))
                ev_level = min(level_max, int(round(ev['weight'])))
                new_level = min(level_max, max(ev_level, score_cap if ev['count'] > 0 else 0))
                confidence = max(0.0, min(1.0, 0.3 + 0.1 * ev['count']))

                ls = LearnerSkill.query.filter_by(
                    user_id=self.user_id, skill_id=skill.id
                ).first()
                if not ls:
                    ls = LearnerSkill(
                        user_id=self.user_id,
                        skill_id=skill.id,
                        level=new_level,
                        confidence=confidence,
                        evidence_count=int(ev['count']),
                        source='system',
                        last_evidence_at=datetime.utcnow(),
                    )
                    db.session.add(ls)
                    db.session.add(LearnerSkillHistory(
                        user_id=self.user_id,
                        skill_id=skill.id,
                        previous_level=0,
                        new_level=new_level,
                        level_max=level_max,
                        confidence=confidence,
                        source=source,
                        course_id=self.course_id,
                    ))
                    created.append({'skill_code': skill.code,
                                    'skill_name': skill.name,
                                    'level': new_level,
                                    'previous_level': 0,
                                    'delta': new_level,
                                    'level_max': level_max,
                                    'confidence': confidence})
                else:
                    prev_level = int(ls.level or 0)
                    level_changed = ls.level != new_level
                    if (level_changed
                            or (ls.confidence or 0) < confidence):
                        ls.level = new_level
                        ls.confidence = confidence
                        ls.evidence_count = int(ev['count'])
                        ls.last_evidence_at = datetime.utcnow()
                        if level_changed:
                            db.session.add(LearnerSkillHistory(
                                user_id=self.user_id,
                                skill_id=skill.id,
                                previous_level=prev_level,
                                new_level=new_level,
                                level_max=level_max,
                                confidence=confidence,
                                source=source,
                                course_id=self.course_id,
                            ))
                        updated.append({'skill_code': skill.code,
                                        'skill_name': skill.name,
                                        'level': new_level,
                                        'previous_level': prev_level,
                                        'delta': new_level - prev_level,
                                        'level_max': level_max,
                                        'confidence': confidence})

            # Persist a snapshot row so other surfaces can read the result.
            if self.course_id:
                snap = StudentPerformanceSnapshot(
                    user_id=self.user_id,
                    course_id=self.course_id,
                    average_assignment_score=perf.get('average_assignment_score'),
                    average_exam_score=perf.get('average_exam_score'),
                    materials_completed_percent=perf.get('materials_progress'),
                    engagement_score=overall,
                    strong_topics=perf.get('strengths') or [],
                    weak_topics=perf.get('weaknesses') or [],
                )
                db.session.add(snap)

            db.session.commit()
            result['updated'] = updated
            result['created'] = created
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            result['error'] = str(e)
        return result

    def rerank_path_steps(self, path_id: str = None) -> Dict[str, Any]:
        """Reorder pending PathSteps so weak-skill steps come first.

        If path_id is None, rerank every active LearningPath for this user.
        Completed/in-progress steps keep their relative order at the front.
        """
        out = {'paths_reranked': [], 'errors': []}
        if not db:
            return out

        try:
            from app.models import LearningPath, PathStep, LearnerSkill, Skill

            # Build a weakness score map: lower mastery => higher priority.
            weakness: Dict[str, float] = {}
            ls_rows = (LearnerSkill.query
                       .filter_by(user_id=self.user_id).all())
            for ls in ls_rows:
                skill = ls.skill or Skill.query.get(ls.skill_id)
                if not skill or not skill.code:
                    continue
                level_max = skill.level_max or 5
                # weakness in [0..1], 1 = weakest
                weakness[skill.code] = 1.0 - (
                    (ls.level or 0) / float(level_max)
                )

            paths_q = LearningPath.query.filter_by(user_id=self.user_id)
            if path_id:
                paths_q = paths_q.filter_by(id=path_id)
            else:
                paths_q = paths_q.filter_by(status='active')
            paths = paths_q.all()

            for path in paths:
                try:
                    steps = PathStep.query.filter_by(path_id=path.id).all()
                    if not steps:
                        continue
                    # Sort: completed first (in original order), then pending
                    # ranked by skill weakness (desc) then original order.
                    def step_key(s):
                        is_completed = s.status in ('completed', 'in_progress')
                        w = weakness.get(s.primary_skill_code or '', 0.0)
                        return (
                            0 if is_completed else 1,           # finished first
                            -w if not is_completed else 0,      # weakest pending next
                            s.order_index or 0,                 # stable tiebreaker
                        )
                    steps.sort(key=step_key)
                    for new_idx, s in enumerate(steps):
                        s.order_index = new_idx
                    out['paths_reranked'].append({
                        'path_id': path.id,
                        'count': len(steps),
                    })
                except Exception as e:
                    out['errors'].append({'path_id': path.id, 'error': str(e)})

            db.session.commit()
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            out['errors'].append({'error': str(e)})
        return out

    def run(self, path_id: str = None, source: str = 'adaptive') -> Dict[str, Any]:
        """Convenience: recompute skills + rerank steps in one call."""
        return {
            'skills': self.recompute_skill_levels(source=source),
            'paths': self.rerank_path_steps(path_id),
        }


def adaptive_recompute(user_id: str, course_id: str = None,
                       path_id: str = None,
                       source: str = 'adaptive') -> Dict[str, Any]:
    """Module-level convenience wrapper used by the tutor route."""
    return AdaptiveEngine(user_id, course_id).run(path_id, source=source)


def trigger_adaptive_recompute(user_id: str, course_id: str = None,
                               source: str = 'adaptive') -> None:
    """Best-effort, side-effect-free trigger used by tutor/material routes.

    Never raises — designed to be called inline after a learner action
    (tutor reply, material completion) without affecting the caller's
    response on failure.
    """
    try:
        AdaptiveEngine(user_id, course_id).run(source=source)
    except Exception as e:
        try:
            import logging
            logging.exception('adaptive recompute trigger failed: %s', e)
        except Exception:
            pass
