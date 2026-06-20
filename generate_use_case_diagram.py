import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(28, 16))
ax.set_xlim(0, 28)
ax.set_ylim(0, 16)
ax.set_facecolor('white')
fig.patch.set_facecolor('white')
ax.axis('off')

# ─────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────
def draw_ellipse(ax, cx, cy, w=3.2, h=0.75, text='', fontsize=9):
    ellipse = mpatches.Ellipse((cx, cy), w, h,
                                edgecolor='#C0392B', facecolor='#FEF9F9',
                                linewidth=1.5, zorder=3)
    ax.add_patch(ellipse)
    ax.text(cx, cy, text, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color='#1A1A1A',
            wrap=True, zorder=4,
            multialignment='center')

def draw_actor(ax, cx, cy, label):
    """Draw a stick-figure actor."""
    # Head
    head = plt.Circle((cx, cy + 0.65), 0.18, color='#2C3E50', zorder=5)
    ax.add_patch(head)
    # Body
    ax.plot([cx, cx], [cy + 0.47, cy - 0.1], color='#2C3E50', lw=2, zorder=5)
    # Arms
    ax.plot([cx - 0.35, cx + 0.35], [cy + 0.2, cy + 0.2], color='#2C3E50', lw=2, zorder=5)
    # Legs
    ax.plot([cx, cx - 0.3], [cy - 0.1, cy - 0.6], color='#2C3E50', lw=2, zorder=5)
    ax.plot([cx, cx + 0.3], [cy - 0.1, cy - 0.6], color='#2C3E50', lw=2, zorder=5)
    ax.text(cx, cy - 0.9, label, ha='center', va='center',
            fontsize=9, fontweight='bold', color='#2C3E50', zorder=5)

def draw_line(ax, x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color='#C0392B', lw=1.2, zorder=2, alpha=0.7)

def draw_system_box(ax, x, y, w, h, title):
    rect = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.1",
                           edgecolor='#7F8C8D', facecolor='#F8F9FA',
                           linewidth=1.5, zorder=1)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h - 0.25, title,
            ha='center', va='center', fontsize=11,
            fontweight='bold', color='#2C3E50', zorder=2)

# ─────────────────────────────────────────────────────────────────
# Main Title
# ─────────────────────────────────────────────────────────────────
ax.text(14, 15.5, 'Smart Ambulance Emergency System – Use Case Diagram',
        ha='center', va='center', fontsize=15, fontweight='bold',
        color='#2C3E50',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#D6EAF8',
                  edgecolor='#2980B9', linewidth=2))

# ─────────────────────────────────────────────────────────────────
# TOP SYSTEM BOX  ──  Patient / User
# ─────────────────────────────────────────────────────────────────
draw_system_box(ax, 2.5, 11.5, 21, 3.2, 'Patient / User System')

# Patient use-cases (top row)
patient_cases = [
    (5.0,  13.1, 'Register / Login'),
    (8.5,  13.1, 'Request Emergency Help'),
    (12.0, 13.1, 'Track Ambulance\nin Real-Time'),
    (15.5, 13.1, 'Update Emergency\nStatus'),
    (19.0, 13.1, 'Update Profile\n& Feedback'),
]

for (cx, cy, lbl) in patient_cases:
    draw_ellipse(ax, cx, cy, w=3.0, h=0.85, text=lbl, fontsize=8.5)

# Patient actor (right)
draw_actor(ax, 24.2, 12.8, 'Patient\n/ User')

# Connect actor to use-cases
for (cx, cy, _) in patient_cases:
    draw_line(ax, 24.2, 12.8, cx + 1.5, cy)

# ─────────────────────────────────────────────────────────────────
# BOTTOM SYSTEM BOX  ──  Hospital Admin / Driver System
# ─────────────────────────────────────────────────────────────────
draw_system_box(ax, 0.5, 0.8, 26.5, 9.8, 'Hospital Admin / Driver System')

# ── Row 1 of admin use-cases ──
admin_row1 = [
    (2.0,  9.2,  'Login to\nDashboard'),
    (4.9,  9.2,  'View Incoming\nRequests'),
    (7.8,  9.2,  'Accept / Reject\nRequests'),
    (10.7, 9.2,  'Update Dispatch\nStatus'),
    (13.6, 9.2,  'Assign Driver\nto Ambulance'),
    (16.5, 9.2,  'Manage\nAmbulance Fleet'),
    (19.4, 9.2,  'Manage\nHospital Fleet'),
    (22.3, 9.2,  'View Hospital\nRegister'),
]

# ── Row 2 of admin use-cases ──
admin_row2 = [
    (2.0,  7.2,  'View Hospital\nDetails'),
    (4.9,  7.2,  'Mark Ambulance\nAvailable'),
    (7.8,  7.2,  'Approve &\nComplete Report'),
    (10.7, 7.2,  'Manage\nVehicles'),
    (13.6, 7.2,  'View System\nInsights'),
    (16.5, 7.2,  'View Patient\nHistory'),
    (19.4, 7.2,  'Send Email /\nSMS Alerts'),
    (22.3, 7.2,  'View Traffic &\nRoute Data'),
]

# ── Row 3 – Driver use-cases ──
driver_row = [
    (5.5,  5.2,  'Driver Login\n& Dashboard'),
    (9.0,  5.2,  'View Assigned\nDispatch'),
    (12.5, 5.2,  'Update Route\n& Location'),
    (16.0, 5.2,  'Mark Trip\nCompleted'),
    (19.5, 5.2,  'View Patient\nDetails'),
]

all_rows = [admin_row1, admin_row2, driver_row]
for row in all_rows:
    for (cx, cy, lbl) in row:
        draw_ellipse(ax, cx, cy, w=2.8, h=0.85, text=lbl, fontsize=8)

# ── Admin Actor (left) ──
draw_actor(ax, 1.0, 8.2, 'Hospital\nAdmin')

# Connect admin actor to row1
for (cx, cy, _) in admin_row1:
    draw_line(ax, 1.0, 8.2, cx - 1.4, cy)

# Connect admin actor to row2
for (cx, cy, _) in admin_row2:
    draw_line(ax, 1.0, 8.2, cx - 1.4, cy)

# ── Driver Actor (left) ──
draw_actor(ax, 1.8, 5.2, 'Driver')

for (cx, cy, _) in driver_row:
    draw_line(ax, 1.8, 5.2, cx - 1.4, cy)

# ─────────────────────────────────────────────────────────────────
# Legend
# ─────────────────────────────────────────────────────────────────
legend_x, legend_y = 20.5, 4.5
rect_leg = FancyBboxPatch((legend_x - 0.2, legend_y - 1.4), 6.8, 2.2,
                           boxstyle="round,pad=0.15",
                           edgecolor='#7F8C8D', facecolor='#FDFEFE',
                           linewidth=1.2, zorder=6)
ax.add_patch(rect_leg)
ax.text(legend_x + 3.1, legend_y + 0.6, 'Legend',
        ha='center', fontsize=10, fontweight='bold', color='#2C3E50', zorder=7)

# Ellipse sample
e_leg = mpatches.Ellipse((legend_x + 0.6, legend_y + 0.05), 1.0, 0.45,
                           edgecolor='#C0392B', facecolor='#FEF9F9', lw=1.5, zorder=7)
ax.add_patch(e_leg)
ax.text(legend_x + 0.6, legend_y + 0.05, 'Use Case', ha='center', va='center',
        fontsize=7.5, color='#1A1A1A', zorder=8)
ax.text(legend_x + 1.8, legend_y + 0.05, '= Use Case', ha='left', va='center',
        fontsize=8.5, color='#2C3E50', zorder=7)

# Stick figure sample (simplified)
ax.plot([legend_x + 0.55, legend_x + 0.55], [legend_y - 0.35, legend_y - 0.9],
        color='#2C3E50', lw=2, zorder=7)
ax.add_patch(plt.Circle((legend_x + 0.55, legend_y - 0.25), 0.12,
                          color='#2C3E50', zorder=7))
ax.text(legend_x + 1.8, legend_y - 0.55, '= Actor', ha='left', va='center',
        fontsize=8.5, color='#2C3E50', zorder=7)

# Relationship line sample
ax.plot([legend_x + 0.1, legend_x + 1.1], [legend_y - 1.0, legend_y - 1.0],
        color='#C0392B', lw=1.5, zorder=7)
ax.text(legend_x + 1.8, legend_y - 1.0, '= Relationship', ha='left', va='center',
        fontsize=8.5, color='#2C3E50', zorder=7)

# ─────────────────────────────────────────────────────────────────
# Row / section labels
# ─────────────────────────────────────────────────────────────────
ax.text(0.6, 9.7, 'Admin\nUse Cases', ha='center', fontsize=8,
        color='#5D6D7E', style='italic')
ax.text(0.6, 5.9, 'Driver\nUse Cases', ha='center', fontsize=8,
        color='#5D6D7E', style='italic')

plt.tight_layout(pad=0.3)

out_path = r'c:\Users\zohai\OneDrive\Desktop\smart ambulance\use_case_diagram.png'
plt.savefig(out_path, dpi=180, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print(f'Saved → {out_path}')
plt.close()
