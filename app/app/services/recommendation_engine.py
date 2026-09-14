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
            
            for course_id in course_ids:
                submissions = AssignmentSubmission.query.filter(
                    AssignmentSubmission.user_id == self.user_id,
                    AssignmentSubmission.assignment.has(course_id=course_id)
                ).all()
                
                for sub in submissions:
                    if sub.score is not None:
                        assignment_scores.append(sub.score)
                        
                results = ExamResult.query.filter(
                    ExamResult.user_id == self.user_id,
                    ExamResult.exam.has(course_id=course_id)
                ).all()
                
                for result in results:
                    if result.percentage is not None:
                        exam_scores.append(result.percentage)
                        
                progress = LearningProgress.query.filter(
                    LearningProgress.user_id == self.user_id,
                    LearningProgress.course_id == course_id
                ).all()
                
                for p in progress:
                    completed_materials += p.completed_count
                    total_materials += p.total_items
                    if p.topic:
                        if p.topic not in topic_performance:
                            topic_performance[p.topic] = []
                        topic_performance[p.topic].append({
                            'mastery': p.mastery_level,
                            'time_spent': p.time_spent_minutes
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
            
        recent_progress = [p for p in progress_list 
                         if p.updated_at and p.updated_at > datetime.utcnow() - timedelta(days=7)]
        
        if len(recent_progress) > 5:
            return 'fast'
        elif len(recent_progress) > 2:
            return 'normal'
        else:
            return 'slow'
    
    def _calculate_engagement(self, submissions: List, progress: List) -> str:
        """Calculate engagement level based on activity."""
        recent_submissions = len([s for s in submissions 
                                 if s.submitted_at and s.submitted_at > datetime.utcnow() - timedelta(days=7)])
        recent_progress = len([p for p in progress 
                              if p.updated_at and p.updated_at > datetime.utcnow() - timedelta(days=7)])
        
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
