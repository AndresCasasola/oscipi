import subprocess
import datetime
import collections
import os
import sys

def get_commit_dates():
    """Extracts commit dates from the local git history."""
    try:
        # Get all commit dates in YYYY-MM-DD format
        cmd = ["git", "log", "--pretty=format:%ad", "--date=short"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.splitlines()
    except Exception as e:
        print(f"Error reading git log: {e}")
        return []

def generate_svg(commit_counts, output_path):
    """Generates a GitHub-style heatmap SVG."""
    # Constants for layout
    SQUARE_SIZE = 10
    GAP = 2
    RADIUS = 2
    HEADER_HEIGHT = 20
    LEFT_MARGIN = 30
    WEEKS = 53
    DAYS_IN_WEEK = 7
    
    # Colors (GitHub theme)
    COLORS = [
        "#ebedf0", # L0
        "#9be9a8", # L1
        "#40c463", # L2
        "#30a14e", # L3
        "#216e39"  # L4
    ]
    
    # Calculate dimensions
    width = LEFT_MARGIN + (WEEKS * (SQUARE_SIZE + GAP))
    height = HEADER_HEIGHT + (DAYS_IN_WEEK * (SQUARE_SIZE + GAP)) + 20 # Extra for legend
    
    # Date range: last 365 days ending on the next Saturday to align grid
    today = datetime.date.today()
    days_to_saturday = (5 - today.weekday()) % 7
    end_date = today + datetime.timedelta(days=days_to_saturday)
    start_date = end_date - datetime.timedelta(weeks=WEEKS, days=0)
    
    # Prepare SVG content
    svg = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '  <style>',
        '    .month-text { font-size: 9px; fill: #767676; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }',
        '    .day-text { font-size: 9px; fill: #767676; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }',
        '  </style>'
    ]
    
    # Month labels
    current_date = start_date
    last_month = -1
    for week in range(WEEKS):
        if current_date.month != last_month:
            x = LEFT_MARGIN + week * (SQUARE_SIZE + GAP)
            month_name = current_date.strftime("%b")
            svg.append(f'  <text x="{x}" y="10" class="month-text">{month_name}</text>')
            last_month = current_date.month
        current_date += datetime.timedelta(weeks=1)
        
    # Day labels (Mon, Wed, Fri)
    svg.append(f'  <text x="0" y="{HEADER_HEIGHT + 1 * (SQUARE_SIZE + GAP) + 8}" class="day-text">Mon</text>')
    svg.append(f'  <text x="0" y="{HEADER_HEIGHT + 3 * (SQUARE_SIZE + GAP) + 8}" class="day-text">Wed</text>')
    svg.append(f'  <text x="0" y="{HEADER_HEIGHT + 5 * (SQUARE_SIZE + GAP) + 8}" class="day-text">Fri</text>')
    
    # Grid
    current_date = start_date
    for week in range(WEEKS):
        for day in range(DAYS_IN_WEEK):
            date_str = current_date.strftime("%Y-%m-%d")
            count = commit_counts.get(date_str, 0)
            
            # Determine color index
            if count == 0:
                color_idx = 0
            elif count < 3:
                color_idx = 1
            elif count < 6:
                color_idx = 2
            elif count < 9:
                color_idx = 3
            else:
                color_idx = 4
            
            x = LEFT_MARGIN + week * (SQUARE_SIZE + GAP)
            y = HEADER_HEIGHT + day * (SQUARE_SIZE + GAP)
            
            color = COLORS[color_idx]
            svg.append(f'  <rect x="{x}" y="{y}" width="{SQUARE_SIZE}" height="{SQUARE_SIZE}" fill="{color}" rx="{RADIUS}" ry="{RADIUS}">')
            svg.append(f'    <title>{date_str}: {count} commits</title>')
            svg.append('  </rect>')
            
            current_date += datetime.timedelta(days=1)
            
    # Legend
    legend_x = width - 100
    legend_y = height - 15
    svg.append(f'  <text x="{legend_x - 30}" y="{legend_y + 8}" class="day-text">Less</text>')
    for i, color in enumerate(COLORS):
        svg.append(f'  <rect x="{legend_x + i * (SQUARE_SIZE + GAP)}" y="{legend_y}" width="{SQUARE_SIZE}" height="{SQUARE_SIZE}" fill="{color}" rx="{RADIUS}" ry="{RADIUS}" />')
    svg.append(f'  <text x="{legend_x + 5 * (SQUARE_SIZE + GAP) + 5}" y="{legend_y + 8}" class="day-text">More</text>')
    
    svg.append('</svg>')
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write("\n".join(svg))
    print(f"Heatmap generated at: {output_path}")

if __name__ == "__main__":
    dates = get_commit_dates()
    counts = collections.Counter(dates)
    
    output = "profile-summary-card-output/repo-heatmap.svg"
    if len(sys.argv) > 1:
        output = sys.argv[1]
        
    generate_svg(counts, output)
