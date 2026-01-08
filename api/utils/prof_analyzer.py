import io
import math
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any, Optional
from collections import Counter
from PIL import Image

GRADE_POINTS = {'A*': 10, 'A': 10, 'B+': 9, 'B': 8, 'C+': 7, 'C': 6, 'D+': 5, 'D': 4, 'F': 0, 'E': 0}

def _safe_count(val) -> int:
    try:
        return int(float(val)) if val is not None else 0
    except (ValueError, TypeError):
        return 0

def _offering_spi_and_count(grades):
    total_points, total_students, grade_counts = 0, 0, Counter()
    for g in grades:
        gt, cnt = getattr(g, 'grade_type', None), _safe_count(getattr(g, 'count', 0))
        if cnt > 0 and gt:
            grade_counts[gt] += cnt
            pts = GRADE_POINTS.get(gt)
            if pts is not None:
                total_points += pts * cnt
                total_students += cnt
    spi = round(total_points / total_students, 2) if total_students > 0 else None
    return spi, total_students, dict(grade_counts)

def _weighted_stats(values: List[float], weights: List[float]) -> Dict[str, Optional[float]]:
    if not values or sum(weights) == 0:
        return {'mean': None, 'sigma': None}
    mean = sum(v * w for v, w in zip(values, weights)) / sum(weights)
    variance = sum(w * ((v - mean) ** 2) for v, w in zip(values, weights)) / sum(weights)
    return {'mean': mean, 'sigma': math.sqrt(variance)}

def calculate_career_stats(offerings: List[Any]) -> Dict[str, Any]:
    if not offerings: return {}
    career_grade_counts, spi_trend_data, course_offering_counts = Counter(), [], Counter()

    for o in offerings:
        course_code = getattr(o, 'course_code', None) or (o.course.code if getattr(o, 'course', None) else 'N/A')
        course_offering_counts[course_code] += 1
        spi, students, grades = _offering_spi_and_count(getattr(o, 'grades', []))
        career_grade_counts.update(grades)
        if spi is not None and students > 0:
            spi_trend_data.append({
                'spi': spi, 'student_count': students, 'academic_year': o.academic_year,
                'semester': o.semester, 'course_code': course_code, 'label': f"{o.academic_year} {o.semester}"
            })

    sem_order = {'Odd': 1, 'Even': 2, 'Summer': 3}
    spi_trend_data.sort(key=lambda x: (int(x['academic_year'].split('-')[0]), sem_order.get(x['semester'], 99)))

    spis, weights = [d['spi'] for d in spi_trend_data], [d['student_count'] for d in spi_trend_data]
    weighted = _weighted_stats(spis, weights)
    career_spi = round(weighted['mean'], 2) if weighted['mean'] is not None else 0.0
    consistency_sigma = round(weighted['sigma'], 3) if weighted['sigma'] is not None else 0.0
    
    total_graded = sum(career_grade_counts.values())
    career_centric = 'No Grade Data'
    if total_graded > 0:
        zone_defs = { 'A_Zone': ['A*', 'A'], 'B_Zone': ['B+', 'B'], 'C_Zone': ['C+', 'C'], 'DF_Zone': ['D+', 'D', 'F', 'E'] }
        zone_counts = {zn: sum(career_grade_counts.get(g, 0) for g in gl) for zn, gl in zone_defs.items()}
        zone_percentages = {z: (c / total_graded) * 100 for z, c in zone_counts.items()}
        max_zone = max(zone_percentages, key=zone_percentages.get)
        
        if 'A_Zone' == max_zone: career_centric = 'Generous (A Centric)'
        elif 'B_Zone' == max_zone: career_centric = 'Good Performance (B+/B Centric)'
        elif 'C_Zone' == max_zone: career_centric = 'Average Performance (C Centric)'
        else: career_centric = 'Tough Grading (High D/F Rate)'

    significant = sorted([d for d in spi_trend_data if d['student_count'] >= 1], key=lambda x: x['spi'])

    return {
        'career_spi': career_spi, 'consistency_sigma': consistency_sigma,
        'grade_distribution': dict(career_grade_counts), 'spi_trend_data': spi_trend_data,
        'total_students_graded_career': sum(weights), 'total_offerings_count': len(offerings),
        'most_generous_offering': significant[-1] if significant else None,
        'toughest_offering': significant[0] if significant else None,
        'career_centric_grading': career_centric,
        'most_taught_courses': [{'code': c, 'count': n} for c, n in course_offering_counts.most_common(5)]
    }

def generate_career_plot(prof_name: str, career_stats: Dict[str, Any]) -> Optional[bytes]:
    """
    Generate a clean, production-ready 'Career Grade Analysis' plot.
    """
    if not career_stats: return None

    trend_data = career_stats.get('spi_trend_data', [])
    grade_dist = career_stats.get('grade_distribution', {})

    if not trend_data and not grade_dist: return None

    # Global Style
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'axes.edgecolor': '#cccccc',
        'axes.linewidth': 1,
        'grid.color': '#e5e5e5',
        'figure.facecolor': 'white'
    })

    fig = plt.figure(figsize=(12, 10))
    gs = fig.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.45, 
                          top=0.92, bottom=0.08, left=0.08, right=0.96)
    
    fig.suptitle(f'Grade Analysis: {prof_name}', fontsize=17, weight='bold', y=0.97)

    # Subplot 1: SPI Trend
    ax_trend = fig.add_subplot(gs[0])
    if len(trend_data) > 1:
        labels = [f"{d.get('academic_year', '')}\n{d.get('semester', '')}" for d in trend_data]
        spis = [d['spi'] for d in trend_data]
        courses = [d.get('course_code', 'N/A') for d in trend_data]
        student_counts = [d.get('student_count', 0) for d in trend_data]

        unique_courses = sorted(list(dict.fromkeys(courses)))
        cmap = plt.get_cmap('tab10')
        course_color_map = {course: cmap(i % 10) for i, course in enumerate(unique_courses)}

        x = np.arange(len(labels))
        career_spi = career_stats.get('career_spi', 0)
        
        ax_trend.plot(x, spis, color='#d0d0d0', lw=2.5, zorder=1, alpha=0.5)

        max_students = max(student_counts) if student_counts else 1
        for xi, spi_val, course, count in zip(x, spis, courses, student_counts):
            color = course_color_map.get(course, '#999')
            size = 100 + (count / max_students) * 180
            ax_trend.scatter(xi, spi_val, color=color, s=size, edgecolors='white', lw=2, zorder=3)
            
            if career_spi:
                ax_trend.plot([xi, xi], [career_spi, spi_val], color=color, alpha=0.2, lw=3, zorder=2)

        ax_trend.set_xticks(x)
        ax_trend.set_xticklabels(labels, fontsize=9, ha='center', rotation=45)
        ax_trend.set_ylabel('AGP of Offering', fontsize=11, weight='bold')
        ax_trend.set_title('AGP Trend Over Time', fontsize=13, pad=10, loc='left', weight='bold')
        ax_trend.grid(axis='y', linestyle='--', alpha=0.4)
        ax_trend.spines['top'].set_visible(False)
        ax_trend.spines['right'].set_visible(False)

        if career_spi:
            ax_trend.axhline(career_spi, ls='--', lw=2, color='#e74c3c', alpha=0.7, zorder=4)

        # Legend
        handles = [
            plt.Line2D([], [], marker='o', color='w', markerfacecolor=c, 
                       label=course, markersize=8, markeredgecolor='#555')
            for course, c in course_color_map.items()
        ]
        ax_trend.legend(handles=handles, loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)
        
    else:
        ax_trend.text(0.5, 0.5, 'Insufficient Data for Trend Analysis', ha='center', va='center')

    # Subplot 2: Grade Distribution
    ax_bar = fig.add_subplot(gs[1])
    core_order = ['A*', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'E', 'F']
    present_grades = [g for g in core_order if grade_dist.get(g, 0) > 0]
    counts = [grade_dist[g] for g in present_grades]

    if counts:
        grade_colors = {'A*': '#1B5E20', 'A': '#2E7D32', 'B+': '#558B2F', 'B': '#689F38', 'C+': '#FBC02D', 'C': '#F57F17', 'D+': '#E64A19', 'D': '#D32F2F', 'E': '#B71C1C', 'F': '#880E4F'}
        colors = [grade_colors.get(g, '#999') for g in present_grades]
        
        bars = ax_bar.bar(np.arange(len(present_grades)), counts, color=colors, width=0.7)
        ax_bar.set_xticks(np.arange(len(present_grades)))
        ax_bar.set_xticklabels(present_grades, weight='bold')
        ax_bar.spines['top'].set_visible(False)
        ax_bar.spines['right'].set_visible(False)
    
    # Watermark Logic
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        logo_path = os.path.join(project_root, 'scripts', 'telegram_logo.png')
        
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            ax_logo = fig.add_axes([0.845, 0.005, 0.04, 0.04])
            ax_logo.imshow(logo_img)
            ax_logo.axis('off')
            fig.text(0.895, 0.025, 't.me/gradiator_iitk_bot', fontsize=9, color='#555', style='italic')
    except Exception:
        pass

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, facecolor='white', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()