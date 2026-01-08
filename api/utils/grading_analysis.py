# api/utils/grading_analysis.py
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import math

@dataclass
class GradeStats:
    """Statistical metrics for grade distribution"""
    avg_points: float
    median_zone: str
    std_dev: float
    skewness: float
    pass_rate: float
    excellence_rate: float  # A zone
    failure_rate: float
    
def analyze_centric_grading(grades: List, total_students: int) -> Optional[str]:
    """
    Ultimate truth-telling grading analysis.
    Never disappoints. Always accurate. Pure insight.
    """
    if not grades or total_students == 0:
        return None
    
    # === STEP 1: DATA NORMALIZATION ===
    grade_points = {
        'A*': 10, 'A': 10, 'B+': 9, 'B': 8, 
        'C+': 7, 'C': 6, 'D+': 5, 'D': 4, 'F': 0, 'E': 0
    }
    
    grade_hierarchy = ['A*', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F', 'E']
    
    # Build clean grade map
    grade_map = {}
    for g in grades:
        grade_type = g.grade_type if hasattr(g, 'grade_type') else g.get('grade_type')
        count = g.count if hasattr(g, 'count') else g.get('count', 0)
        if grade_type in grade_points:
            grade_map[grade_type] = count
    
    total = sum(grade_map.values())
    if total == 0:
        return None
    
    # === STEP 2: CALCULATE CORE STATISTICS ===
    stats = _calculate_statistics(grade_map, grade_points, grade_hierarchy, total)
    
    # === STEP 3: PATTERN DETECTION ===
    pattern = _detect_distribution_pattern(grade_map, stats, total)
    
    # === STEP 4: GENERATE TRUTH ===
    return _generate_insight(pattern, stats)


def _calculate_statistics(grade_map: Dict[str, int], grade_points: Dict[str, int], 
                          grade_hierarchy: List[str], total: int) -> GradeStats:
    """Calculate comprehensive statistical metrics"""
    
    # Weighted average
    weighted_sum = sum(grade_points[g] * count for g, count in grade_map.items())
    avg = weighted_sum / total
    
    # Zone calculations
    a_count = sum(grade_map.get(g, 0) for g in ['A*', 'A'])
    b_count = sum(grade_map.get(g, 0) for g in ['B+', 'B'])
    c_count = sum(grade_map.get(g, 0) for g in ['C+', 'C'])
    fail_count = sum(grade_map.get(g, 0) for g in ['D+', 'D', 'F', 'E'])
    
    excellence_rate = (a_count / total) * 100
    pass_rate = ((total - fail_count) / total) * 100
    failure_rate = (fail_count / total) * 100
    
    # Find median zone
    cumulative = 0
    median_zone = 'C'
    for grade in grade_hierarchy:
        cumulative += grade_map.get(grade, 0)
        if cumulative >= total / 2:
            median_zone = grade
            break
    
    # Calculate standard deviation
    variance = sum(((grade_points[g] - avg) ** 2) * count 
                   for g, count in grade_map.items()) / total
    std_dev = math.sqrt(variance)
    
    # Calculate skewness (measure of asymmetry)
    skewness = sum(((grade_points[g] - avg) ** 3) * count 
                   for g, count in grade_map.items()) / (total * (std_dev ** 3)) if std_dev > 0 else 0
    
    return GradeStats(
        avg_points=avg,
        median_zone=median_zone,
        std_dev=std_dev,
        skewness=skewness,
        pass_rate=pass_rate,
        excellence_rate=excellence_rate,
        failure_rate=failure_rate
    )


def _detect_distribution_pattern(grade_map: Dict[str, int], stats: GradeStats, 
                                 total: int) -> Dict[str, any]:
    """Detect the TRUE pattern in grade distribution"""
    
    # Zone percentages
    a_pct = sum(grade_map.get(g, 0) for g in ['A*', 'A']) / total * 100
    b_pct = sum(grade_map.get(g, 0) for g in ['B+', 'B']) / total * 100
    c_pct = sum(grade_map.get(g, 0) for g in ['C+', 'C']) / total * 100
    d_pct = sum(grade_map.get(g, 0) for g in ['D+', 'D']) / total * 100
    f_pct = sum(grade_map.get(g, 0) for g in ['F', 'E']) / total * 100
    
    zones = {'A': a_pct, 'B': b_pct, 'C': c_pct, 'D': d_pct, 'F': f_pct}
    sorted_zones = sorted(zones.items(), key=lambda x: x[1], reverse=True)
    
    top_zone = sorted_zones[0][0]
    top_pct = sorted_zones[0][1]
    second_pct = sorted_zones[1][1] if len(sorted_zones) > 1 else 0
    
    # Pattern characteristics
    is_dominated = (top_pct - second_pct) > 12  # Clear winner
    is_bimodal = (a_pct > 20 and f_pct > 15) or (a_pct > 25 and d_pct + f_pct > 20)
    is_uniform = stats.std_dev < 1.8  # Low variance
    is_polarized = stats.std_dev > 3.0  # High variance
    is_left_skewed = stats.skewness < -0.5  # More high grades
    is_right_skewed = stats.skewness > 0.5  # More low grades
    
    top_heavy = a_pct + b_pct  # Excellence cluster
    bottom_heavy = d_pct + f_pct  # Struggle cluster
    middle_heavy = b_pct + c_pct  # Average cluster
    
    return {
        'zones': zones,
        'top_zone': top_zone,
        'top_pct': top_pct,
        'is_dominated': is_dominated,
        'is_bimodal': is_bimodal,
        'is_uniform': is_uniform,
        'is_polarized': is_polarized,
        'is_left_skewed': is_left_skewed,
        'is_right_skewed': is_right_skewed,
        'top_heavy': top_heavy,
        'bottom_heavy': bottom_heavy,
        'middle_heavy': middle_heavy,
        'a_pct': a_pct,
        'b_pct': b_pct,
        'c_pct': c_pct,
        'f_pct': f_pct
    }


def _generate_insight(pattern: Dict, stats: GradeStats) -> str:
    """Generate the ultimate one-liner truth"""
    
    avg = stats.avg_points
    zones = pattern['zones']
    
    # === TIER 1: EXTREME PATTERNS (Highest Priority) ===
    
    # Catastrophic failure
    if stats.failure_rate > 35:
        return f"💀 Course massacre—over 1/3rd struggle (D+ or below), survival mode activated (AGP: {avg:.1f})"
    
    # Grade inflation crisis
    if pattern['a_pct'] > 50:
        return f"🎪 Grade circus—A's handed out like candy, credibility zero (AGP: {avg:.1f})"
    
    # Bimodal nightmare
    if pattern['is_bimodal'] and pattern['a_pct'] > 25 and stats.failure_rate > 18:
        return f"⚡ Sink or swim—you either dominate or drown, no rescue boats (AGP: {avg:.1f})"
    
    # === TIER 2: STRONG PATTERNS ===
    
    # Ultra generous
    if pattern['top_heavy'] > 70:
        return f"Easy street—70%+ get B or better, barely a challenge😊 (AGP: {avg:.1f})"
    
    # Very tough grading
    if stats.failure_rate > 25 and avg < 6.5:
        return f"⚔️ Brutal grader—25%+ struggle rate, prepare for battle (AGP: {avg:.1f})"
    
    # High-stakes polarization
    if pattern['is_polarized'] and stats.std_dev > 3.2:
        return f"🎲 High-stakes lottery—massive variance, luck matters (AGP: {avg:.1f})"
    
    # === TIER 3: CLEAR TENDENCIES ===
    
    # A-dominated but reasonable
    if pattern['is_dominated'] and pattern['top_zone'] == 'A' and pattern['a_pct'] > 30:
        if stats.failure_rate < 10:
            return f"✨ A-friendly curve—30%+ excellence, low risk (AGP: {avg:.1f})"
        else:
            return f"🎯 Top-heavy split—many ace it, rest struggle (AGP: {avg:.1f})"
    
    # B-dominated standard
    if pattern['is_dominated'] and pattern['top_zone'] == 'B':
        if avg > 8.2:
            return f"🏆 B+ sweet spot—solid performance rewarded well (AGP: {avg:.1f})"
        else:
            return f"📊 B-zone parking lot—most land here, predictable (AGP: {avg:.1f})"
    
    # C-dominated mediocrity
    if pattern['is_dominated'] and pattern['top_zone'] == 'C':
        if stats.failure_rate > 20:
            return f"📉 C-heavy struggle—low bar, high struggle rate (AGP: {avg:.1f})"
        else:
            return f"😐 Mediocrity central—C's dominate, uninspiring (AGP: {avg:.1f})"
    
    # Failure-dominated disaster
    if pattern['top_zone'] in ['D', 'F']:
        return f"🚨 Failure factory—most students don't make it (AGP: {avg:.1f})"
    
    # === TIER 4: DISTRIBUTION SHAPE ===
    
    # Left skewed (high grades)
    if pattern['is_left_skewed'] and avg > 8.0:
        return f"📈 Grade inflation—curve heavily favors high performers (AGP: {avg:.1f})"
    
    # Right skewed (low grades)
    if pattern['is_right_skewed'] and avg < 7.0:
        return f"📊 Tough curve—skewed toward lower grades deliberately (AGP: {avg:.1f})"
    
    # Uniform but low
    if pattern['is_uniform'] and avg < 6.5:
        return f"⚠️ Consistently tough—low grades spread evenly (AGP: {avg:.1f})"
    
    # Uniform but high
    if pattern['is_uniform'] and avg > 8.0:
        return f"🌟 Consistently strong—high performance across board (AGP: {avg:.1f})"
    
    # === TIER 5: SPECIFIC SCENARIOS ===
    
    # High middle clustering
    if pattern['middle_heavy'] > 60 and 7.0 <= avg <= 8.0:
        return f"🎯 Classic bell curve—most land in B-C zone, textbook (AGP: {avg:.1f})"
    
    # Balanced excellence
    if 8.0 <= avg <= 8.8 and stats.std_dev < 2.2 and stats.failure_rate < 12:
        return f"💎 Balanced excellence—fair, achievable, well-designed (AGP: {avg:.1f})"
    
    # Mixed with high failure
    if not pattern['is_dominated'] and stats.failure_rate > 18:
        return f"🎢 Chaotic spread—scattered grades, high dropout risk (AGP: {avg:.1f})"
    
    # Boring average
    if 6.8 <= avg <= 7.5 and stats.std_dev < 2.0:
        return f"😴 Paint-drying average—nothing exciting, pure mediocre (AGP: {avg:.1f})"
    
    # === TIER 6: SAFETY NET (Context-aware fallbacks) ===
    
    # High average, varied distribution
    if avg > 8.5:
        return f"🔥 High-flying cohort—motivated batch, strong results (AGP: {avg:.1f})"
    
    # Low average, not dominated
    if avg < 6.5:
        return f"⛰️ Uphill climb—low scores common, tough material (AGP: {avg:.1f})"
    
    # Scattered distribution
    if stats.std_dev > 2.5:
        return f"🌪️ All over the map—no clear pattern, unpredictable (AGP: {avg:.1f})"
    
    # True middle ground
    if 7.0 <= avg <= 7.8:
        return f"⚖️ Dead center—neither easy nor hard, perfectly average (AGP: {avg:.1f})"
    
    # === ULTIMATE FALLBACK ===
    return f"📋 Standard distribution—nothing remarkable (AGP: {avg:.1f})"