from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import KeepTogether
import io

# Color palette
DARK_BG     = colors.HexColor('#0f172a')
BLUE        = colors.HexColor('#3b82f6')
CYAN        = colors.HexColor('#06b6d4')
GREEN       = colors.HexColor('#10b981')
YELLOW      = colors.HexColor('#f59e0b')
RED         = colors.HexColor('#ef4444')
LIGHT_TEXT  = colors.HexColor('#f1f5f9')
MUTED_TEXT  = colors.HexColor('#64748b')
CARD_BG     = colors.HexColor('#1e293b')
BORDER      = colors.HexColor('#334155')

def _style(name, **kwargs):
    defaults = dict(fontName='Helvetica', fontSize=10,
                    textColor=LIGHT_TEXT, leading=14)
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)

def generate_pdf(report: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    story = []
    W = 18*cm  # usable width

    # ── HEADER ──────────────────────────────────────────────────────
    header_data = [[
        Paragraph('<font size="28" color="#3b82f6"><b>VEDA</b></font>', _style('h')),
        Paragraph('<font size="9" color="#64748b">Venture Evaluation &amp; Due Diligence Agent<br/>Powered by Vertex AI · Gemini 2.5 Flash</font>',
                  _style('hr', alignment=TA_RIGHT)),
    ]]
    header_t = Table(header_data, colWidths=[9*cm, 9*cm])
    header_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BG),
        ('PADDING',    (0,0), (-1,-1), 12),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(header_t)
    story.append(Spacer(1, 0.4*cm))

    # ── COMPANY INFO BANNER ──────────────────────────────────────────
    company = report.get('company_name', 'Unknown')
    industry = report.get('industry', '—').upper()
    code_s = report.get('code_audit', {})
    reg_s  = report.get('regulatory', {})
    mkt_s  = report.get('market_forecast', {})
    exec_s = report.get('executive_summary', {})

    repo_url = (report.get('github_repo_url')
                or code_s.get('raw_github_data', {}).get('repo_url', '—'))
    overall  = report.get('overall_risk_score', '—')
    rec      = exec_s.get('recommendation', '—')

    rec_color = '#10b981' if 'PROCEED' in rec and 'CONDITION' not in rec else \
                '#f59e0b' if 'CONDITION' in rec else '#ef4444'

    info_data = [[
        Paragraph(f'<font size="18" color="#f1f5f9"><b>{company}</b></font><br/>'
                  f'<font size="9" color="#64748b">{industry} &nbsp;·&nbsp; {repo_url}</font>',
                  _style('ci')),
        Paragraph(f'<font size="9" color="#64748b">RECOMMENDATION</font><br/>'
                  f'<font size="11" color="{rec_color}"><b>{rec}</b></font>',
                  _style('cr', alignment=TA_RIGHT)),
    ]]
    info_t = Table(info_data, colWidths=[11*cm, 7*cm])
    info_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CARD_BG),
        ('PADDING',    (0,0), (-1,-1), 14),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW',  (0,0), (-1,-1), 2, BLUE),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 0.5*cm))

    # ── SCORE CARDS ──────────────────────────────────────────────────
    def score_color(v):
        try:
            v = float(v)
            return '#10b981' if v >= 70 else '#f59e0b' if v >= 40 else '#ef4444'
        except:
            return '#64748b'

    tech  = code_s.get('tech_debt_score', '—')
    comp  = reg_s.get('compliance_score', '—')
    mfit  = mkt_s.get('market_fit_score', '—')

    scores = [
        ('TECH DEBT', tech, 'Code quality & maintainability'),
        ('COMPLIANCE', comp, 'Regulatory adherence'),
        ('MARKET FIT', mfit, 'Growth potential'),
        ('OVERALL RISK', overall, 'Composite score'),
    ]

    score_cells = []
    for label, val, sub in scores:
        sc = str(val)
        color = score_color(val)
        cell = Paragraph(
            f'<font size="8" color="#64748b">{label}</font><br/>'
            f'<font size="26" color="{color}"><b>{sc}</b></font><br/>'
            f'<font size="7" color="#475569">{sub}</font>',
            _style('sc', alignment=TA_CENTER)
        )
        score_cells.append(cell)

    score_t = Table([score_cells], colWidths=[W/4]*4)
    score_t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), CARD_BG),
        ('PADDING',     (0,0), (-1,-1), 14),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('LINEAFTER',   (0,0), (2,-1), 0.5, BORDER),
    ]))
    story.append(score_t)
    story.append(Spacer(1, 0.5*cm))

    # ── EXECUTIVE SUMMARY ────────────────────────────────────────────
    story.append(Paragraph(
        '<font size="11" color="#94a3b8"><b>EXECUTIVE SUMMARY</b></font>',
        _style('sec')
    ))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=8))

    verdict = (exec_s.get('executive_summary')
               or exec_s.get('one_line_verdict', '—'))
    story.append(Paragraph(str(verdict),
        _style('body', fontSize=10, textColor=colors.HexColor('#cbd5e1'), leading=16)))
    story.append(Spacer(1, 0.3*cm))

    one_line = exec_s.get('one_line_verdict', '')
    if one_line:
        story.append(Paragraph(f'<i><font color="#64748b">{one_line}</font></i>',
            _style('ol', fontSize=9)))
    story.append(Spacer(1, 0.5*cm))

    # ── KEY STRENGTHS & CONCERNS ─────────────────────────────────────
    strengths = exec_s.get('key_strengths', [])
    concerns  = exec_s.get('key_concerns', [])

    if strengths or concerns:
        left_items  = ''.join(f'<br/>• {s}' for s in strengths[:4])
        right_items = ''.join(f'<br/>• {c}' for c in concerns[:4])

        two_col = [[
            Paragraph(f'<font size="9" color="#10b981"><b>KEY STRENGTHS</b></font>{left_items}',
                      _style('kl', fontSize=9, textColor=colors.HexColor('#a7f3d0'), leading=14)),
            Paragraph(f'<font size="9" color="#ef4444"><b>KEY CONCERNS</b></font>{right_items}',
                      _style('kr', fontSize=9, textColor=colors.HexColor('#fca5a5'), leading=14)),
        ]]
        two_t = Table(two_col, colWidths=[W/2, W/2])
        two_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#0a1f16')),
            ('BACKGROUND', (1,0), (1,-1), colors.HexColor('#1f0a0a')),
            ('PADDING',    (0,0), (-1,-1), 12),
            ('VALIGN',     (0,0), (-1,-1), 'TOP'),
            ('LINEAFTER',  (0,0), (0,-1), 0.5, BORDER),
        ]))
        story.append(two_t)
        story.append(Spacer(1, 0.5*cm))

    # ── 3-YEAR FORECAST ──────────────────────────────────────────────
    scenarios = mkt_s.get('scenarios', {})
    if scenarios:
        story.append(Paragraph(
            '<font size="11" color="#94a3b8"><b>3-YEAR GROWTH FORECAST</b></font>',
            _style('sec')
        ))
        story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=8))

        fc_header = [
            Paragraph('<b>SCENARIO</b>', _style('fh', fontSize=9, alignment=TA_CENTER)),
            Paragraph('<b>PROBABILITY</b>', _style('fh', fontSize=9, alignment=TA_CENTER)),
            Paragraph('<b>YEAR 3 ARR</b>', _style('fh', fontSize=9, alignment=TA_CENTER)),
            Paragraph('<b>HEADCOUNT</b>', _style('fh', fontSize=9, alignment=TA_CENTER)),
            Paragraph('<b>KEY DRIVER</b>', _style('fh', fontSize=9, alignment=TA_CENTER)),
        ]
        fc_rows = [fc_header]
        colors_map = {'bear': '#ef4444', 'base': '#f59e0b', 'bull': '#10b981'}

        for s in ['bear', 'base', 'bull']:
            sc = scenarios.get(s, {})
            c = colors_map[s]
            fc_rows.append([
                Paragraph(f'<font color="{c}"><b>{s.upper()}</b></font>',
                          _style(f'f{s}', fontSize=10, alignment=TA_CENTER)),
                Paragraph(sc.get('probability', '—'),
                          _style('fp', fontSize=9, alignment=TA_CENTER,
                                 textColor=MUTED_TEXT)),
                Paragraph(f'<font color="{c}"><b>INR {sc.get("year3_arr_inr_lakhs", 0)}L</b></font>',
                          _style('fa', fontSize=10, alignment=TA_CENTER)),
                Paragraph(str(sc.get('year3_headcount', '—')),
                          _style('fhc', fontSize=9, alignment=TA_CENTER,
                                 textColor=MUTED_TEXT)),
                Paragraph(str(sc.get('key_driver') or sc.get('key_risk', '—'))[:60],
                          _style('fd', fontSize=8, textColor=MUTED_TEXT)),
            ])

        fc_t = Table(fc_rows, colWidths=[2.5*cm, 2.5*cm, 3*cm, 2.5*cm, 7.5*cm])
        fc_t.setStyle(TableStyle([
            ('BACKGROUND',     (0,0), (-1,0),  colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR',      (0,0), (-1,0),  LIGHT_TEXT),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
             [CARD_BG, colors.HexColor('#0f172a')]),
            ('GRID',           (0,0), (-1,-1), 0.3, BORDER),
            ('PADDING',        (0,0), (-1,-1), 10),
            ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(fc_t)
        story.append(Spacer(1, 0.5*cm))

    # ── CONDITIONS FOR DEAL ──────────────────────────────────────────
    conditions = exec_s.get('conditions_for_deal', [])
    if conditions:
        story.append(Paragraph(
            '<font size="11" color="#94a3b8"><b>CONDITIONS FOR DEAL CLOSURE</b></font>',
            _style('sec')
        ))
        story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=8))
        for i, cond in enumerate(conditions[:5], 1):
            story.append(Paragraph(
                f'<font color="#f59e0b"><b>{i}.</b></font> <font color="#cbd5e1">{cond}</font>',
                _style(f'c{i}', fontSize=9, leading=14)
            ))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.3*cm))

    # ── FOOTER ───────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        '<font size="8" color="#334155">Generated by VEDA — Venture Evaluation &amp; Due Diligence Agent &nbsp;·&nbsp; '
        'Powered by Vertex AI &amp; Gemini 2.5 Flash &nbsp;·&nbsp; Confidential</font>',
        _style('ft', alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()