"""
Maintainer dashboard for viewing advisory statistics and feedback.
"""

import json
import os
from typing import Dict, List
from datetime import datetime, timedelta
from collections import Counter


class MaintainerDashboard:
    """Dashboard for maintainers to view advisory metrics."""
    
    def __init__(self, learning_data_path: str = "config/learning_data.json"):
        self.learning_data_path = learning_data_path
        self.learning_data = self._load_learning_data()
    
    def _load_learning_data(self) -> Dict:
        """Load learning data."""
        if os.path.exists(self.learning_data_path):
            with open(self.learning_data_path, 'r') as f:
                return json.load(f)
        return {"patterns": [], "feedback": [], "intents": []}
    
    def generate_dashboard(self) -> str:
        """Generate maintainer dashboard report."""
        report = ["# 📊 BLT Preflight Maintainer Dashboard\n"]
        report.append(f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*\n")
        report.append("---\n")
        
        # Overview statistics
        report.append("## Overview\n")
        report.append(self._generate_overview())
        
        # Feedback analysis
        report.append("\n## 💬 Feedback Analysis\n")
        report.append(self._generate_feedback_analysis())
        
        # Intent analysis
        report.append("\n## 🎯 Contributor Intent Patterns\n")
        report.append(self._generate_intent_analysis())
        
        # Pattern effectiveness
        report.append("\n## 📈 Pattern Effectiveness\n")
        report.append(self._generate_pattern_effectiveness())
        
        # Recommendations
        report.append("\n## 🔧 Recommendations for Maintainers\n")
        report.append(self._generate_recommendations())
        
        return "\n".join(report)
    
    def _generate_overview(self) -> str:
        """Generate overview statistics."""
        feedback = self.learning_data.get("feedback", [])
        intents = self.learning_data.get("intents", [])
        
        total_feedback = len(feedback)
        helpful_count = sum(1 for f in feedback if f.get("helpful", 0) == 1)
        helpful_rate = (helpful_count / total_feedback * 100) if total_feedback > 0 else 0
        
        lines = [
            f"- **Total Advisory Feedback**: {total_feedback}",
            f"- **Helpful Rate**: {helpful_rate:.1f}%",
            f"- **Total Intents Captured**: {len(intents)}",
        ]
        
        # Recent activity (last 7 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_feedback = [
            f for f in feedback 
            if datetime.fromisoformat(f.get("timestamp", "1970-01-01")) > recent_cutoff
        ]
        lines.append(f"- **Feedback (Last 7 Days)**: {len(recent_feedback)}")
        
        return "\n".join(lines)
    
    def _generate_feedback_analysis(self) -> str:
        """Analyze feedback patterns."""
        feedback = self.learning_data.get("feedback", [])
        
        if not feedback:
            return "*No feedback data available yet.*\n"
        
        # Group by pattern
        pattern_feedback = {}
        for f in feedback:
            pattern = f.get("pattern", "Unknown")
            if pattern not in pattern_feedback:
                pattern_feedback[pattern] = {"helpful": 0, "total": 0, "comments": []}
            
            pattern_feedback[pattern]["total"] += 1
            pattern_feedback[pattern]["helpful"] += f.get("helpful", 0)
            if f.get("comments"):
                pattern_feedback[pattern]["comments"].append(f.get("comments"))
        
        lines = ["| Pattern | Helpful Rate | Total Feedback |"]
        lines.append("|---------|--------------|----------------|")
        
        for pattern, data in sorted(pattern_feedback.items(), key=lambda x: x[1]["total"], reverse=True):
            helpful_rate = (data["helpful"] / data["total"] * 100) if data["total"] > 0 else 0
            lines.append(f"| {pattern} | {helpful_rate:.1f}% | {data['total']} |")
        
        return "\n".join(lines)
    
    def _generate_intent_analysis(self) -> str:
        """Analyze contributor intent patterns."""
        intents = self.learning_data.get("intents", [])
        
        if not intents:
            return "*No intent data captured yet.*\n"
        
        # Common keywords in intents
        all_words = []
        for intent_data in intents:
            intent = intent_data.get("intent", "").lower()
            words = [w.strip(".,!?") for w in intent.split() if len(w) > 3]
            all_words.extend(words)
        
        common_words = Counter(all_words).most_common(10)
        
        lines = ["**Common themes in contributor intents:**\n"]
        for word, count in common_words:
            lines.append(f"- `{word}`: {count} occurrences")
        
        return "\n".join(lines)
    
    def _generate_pattern_effectiveness(self) -> str:
        """Analyze which patterns are most effective."""
        feedback = self.learning_data.get("feedback", [])
        
        if not feedback:
            return "*No pattern effectiveness data available yet.*\n"
        
        # Calculate effectiveness score
        pattern_scores = {}
        for f in feedback:
            pattern = f.get("pattern", "Unknown")
            if pattern not in pattern_scores:
                pattern_scores[pattern] = []
            pattern_scores[pattern].append(f.get("helpful", 0))
        
        effectiveness = []
        for pattern, scores in pattern_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            effectiveness.append((pattern, avg_score, len(scores)))
        
        # Sort by effectiveness
        effectiveness.sort(key=lambda x: x[1], reverse=True)
        
        lines = ["**Most effective patterns:**\n"]
        for i, (pattern, score, count) in enumerate(effectiveness[:5], 1):
            lines.append(f"{i}. **{pattern}** - {score:.2f} effectiveness ({count} samples)")
        
        if len(effectiveness) > 5:
            lines.append("\n**Patterns needing improvement:**\n")
            for pattern, score, count in effectiveness[-3:]:
                lines.append(f"- **{pattern}** - {score:.2f} effectiveness ({count} samples)")
        
        return "\n".join(lines)
    
    def _generate_recommendations(self) -> str:
        """Generate recommendations for maintainers."""
        feedback = self.learning_data.get("feedback", [])
        
        recommendations = []
        
        # Check for low-performing patterns
        pattern_scores = {}
        for f in feedback:
            pattern = f.get("pattern", "Unknown")
            if pattern not in pattern_scores:
                pattern_scores[pattern] = []
            pattern_scores[pattern].append(f.get("helpful", 0))
        
        for pattern, scores in pattern_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score < 0.5 and len(scores) >= 3:
                recommendations.append(
                    f"- **Review pattern '{pattern}'**: Low effectiveness ({avg_score:.2f}). "
                    "Consider updating guidance or documentation."
                )
        
        # Check feedback comments for common themes
        comments = [f.get("comments", "") for f in feedback if f.get("comments")]
        if comments:
            recommendations.append(
                f"- **Review feedback comments**: {len(comments)} contributors provided detailed feedback. "
                "Check learning_data.json for insights."
            )
        
        if not recommendations:
            recommendations.append("- ✅ All patterns are performing well! Keep up the good work.")
        
        return "\n".join(recommendations)
    
    def export_dashboard(self, output_path: str = "docs/MAINTAINER_DASHBOARD.md") -> None:
        """Export dashboard to file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        dashboard_content = self.generate_dashboard()
        
        with open(output_path, 'w') as f:
            f.write(dashboard_content)
        
        print(f"Dashboard exported to {output_path}")
