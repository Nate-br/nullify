#!/usr/bin/env python3
"""
Generate an executive, high-impact PowerPoint presentation for Nullify & EGATE.
Strictly following user requirements:
- EXACT proportional scaling for all logo images (zero distortion)
- REMOVED all other photos (no AI graphics, no extra images)
- Uses ONLY the EGATE logo on the cover page and logo page
- Big, bold, readable text with simple, jargon-free words
- Generous whitespace and luxury RAVN minimalist aesthetic
"""

import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

# ==========================================
# DESIGN SYSTEM TOKENS (RAVN Minimalist Luxury)
# ==========================================
BG_CREAM = RGBColor(0xFB, 0xF8, 0xF3)
BG_CHARCOAL = RGBColor(0x14, 0x11, 0x0D)
BG_DARK_CARD = RGBColor(0x1F, 0x1A, 0x14)
BG_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG_CARD_SUBTLE = RGBColor(0xF5, 0xF1, 0xEA)

TEXT_DARK = RGBColor(0x14, 0x11, 0x0D)
TEXT_MUTED = RGBColor(0x55, 0x50, 0x48)
TEXT_SUBTLE = RGBColor(0x82, 0x7C, 0x73)

TEXT_LIGHT = RGBColor(0xFA, 0xF8, 0xF5)
TEXT_LIGHT_MUTED = RGBColor(0xBF, 0xB9, 0xAF)
TEXT_LIGHT_SUBTLE = RGBColor(0x7D, 0x77, 0x6E)

BORDER_LIGHT = RGBColor(0xE2, 0xDC, 0xD2)
BORDER_DARK = RGBColor(0x32, 0x2B, 0x22)

ACCENT_EMERALD = RGBColor(0x10, 0xB9, 0x81)
ACCENT_EMERALD_DARK = RGBColor(0x05, 0x96, 0x69)
ACCENT_EMERALD_BG = RGBColor(0xEC, 0xFD, 0xF5)

ACCENT_CRIMSON = RGBColor(0xDC, 0x26, 0x26)
ACCENT_CRIMSON_BG = RGBColor(0xFE, 0xF2, 0xF2)

ACCENT_AMBER = RGBColor(0xD9, 0x77, 0x06)
ACCENT_AMBER_BG = RGBColor(0xFF, 0xFB, 0xEB)

ACCENT_BLUE = RGBColor(0x25, 0x63, 0xEB)
ACCENT_BLUE_BG = RGBColor(0xEF, 0xF6, 0xFF)

FONT_DISPLAY = "Georgia"
FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"
FONT_MONO = "Consolas"

# Only the user's provided logo
LOGO_PATH = "/home/nate/Pictures/Screenshots/egate logo.png"
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = "presentation/assets/egate_logo.png"


def set_flat(shape, fill_color, border_color=None, border_width_pt=1):
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(border_width_pt)
    else:
        shape.line.fill.background()


def create_slide(prs, is_dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    set_flat(bg, BG_CHARCOAL if is_dark else BG_CREAM, None)
    return slide


def add_header(slide, kicker, title, is_dark=False):
    tx_k = slide.shapes.add_textbox(Inches(0.9), Inches(0.55), Inches(11.5), Inches(0.35))
    tf_k = tx_k.text_frame
    tf_k.margin_left = tf_k.margin_top = tf_k.margin_right = tf_k.margin_bottom = 0
    pk = tf_k.paragraphs[0]
    pk.text = f"●  {kicker.upper()}"
    pk.font.name = FONT_MONO
    pk.font.size = Pt(11)
    pk.font.bold = True
    pk.font.color.rgb = ACCENT_EMERALD if is_dark else ACCENT_EMERALD_DARK

    tx_t = slide.shapes.add_textbox(Inches(0.9), Inches(0.9), Inches(11.5), Inches(0.75))
    tf_t = tx_t.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
    pt = tf_t.paragraphs[0]
    pt.text = title
    pt.font.name = FONT_DISPLAY
    pt.font.size = Pt(32)
    pt.font.bold = True
    pt.font.color.rgb = TEXT_LIGHT if is_dark else TEXT_DARK


def add_footer(slide, current, total=12, is_dark=False):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(6.85), Inches(11.533), Pt(0.75))
    set_flat(line, BORDER_DARK if is_dark else BORDER_LIGHT, None)

    tx = slide.shapes.add_textbox(Inches(0.9), Inches(6.92), Inches(11.533), Inches(0.35))
    tf = tx.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]

    r1 = p.add_run()
    r1.text = "EGATE  ●  NULLIFY AUTONOMOUS DEFENSE"
    r1.font.name = FONT_MONO
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = TEXT_LIGHT_SUBTLE if is_dark else TEXT_SUBTLE

    r2 = p.add_run()
    r2.text = "                               See it. Trace it. Nullify it.                               "
    r2.font.name = FONT_DISPLAY
    r2.font.italic = True
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_LIGHT_MUTED if is_dark else TEXT_MUTED

    r3 = p.add_run()
    r3.text = f"{current:02d} / {total:02d}"
    r3.font.name = FONT_MONO
    r3.font.size = Pt(9.5)
    r3.font.color.rgb = TEXT_LIGHT_SUBTLE if is_dark else TEXT_SUBTLE


def add_card(slide, left, top, width, height, bg_color=BG_WHITE, border_color=BORDER_LIGHT):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    set_flat(card, bg_color, border_color, border_width_pt=1)
    return card


def add_pill(slide, left, top, width, height, text, bg_color, text_color, border_color=None):
    pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    set_flat(pill, bg_color, border_color, border_width_pt=1)
    tf = pill.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.CENTER
    p.font.name = FONT_MONO
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = text_color
    return pill


def add_image_proportional(slide, img_path, box_left, box_top, box_w, box_h):
    """
    Inserts an image centered inside a bounding box, preserving EXACT aspect ratio.
    Never stretches or distorts the image.
    """
    if not os.path.exists(img_path):
        return None

    im = Image.open(img_path)
    orig_w, orig_h = im.size
    aspect = orig_w / orig_h

    # Fit within box
    target_w = box_w
    target_h = target_w / aspect
    if target_h > box_h:
        target_h = box_h
        target_w = target_h * aspect

    # Center within box
    final_left = box_left + (box_w - target_w) / 2
    final_top = box_top + (box_h - target_h) / 2

    # Add picture with ONLY width specified to guarantee exact aspect ratio
    pic = slide.shapes.add_picture(img_path, Inches(final_left), Inches(final_top), width=Inches(target_w))
    return pic


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text.strip()


# ==========================================
# SLIDE BUILDERS (12 SLIDES, ZERO EXTRA PHOTOS)
# ==========================================

def build_slide_01_cover(prs):
    """Slide 1: High-Impact Hero Cover with ONLY the EGATE Logo (Exact Proportion)."""
    slide = create_slide(prs, is_dark=True)

    # Ambient border frame
    frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.6), Inches(12.133), Inches(6.3))
    set_flat(frame, BG_CHARCOAL, BORDER_DARK, border_width_pt=1.5)

    # Top Brand Bar: EGATE Logo Card (Exact Proportion)
    card_logo = add_card(slide, 1.1, 1.0, 2.6, 1.1, BG_WHITE, None)
    add_image_proportional(slide, LOGO_PATH, 1.2, 1.05, 2.4, 1.0)

    add_pill(slide, 3.9, 1.35, 2.8, 0.4, "●  EGATE CYBERSECURITY", BG_DARK_CARD, ACCENT_EMERALD, BORDER_DARK)
    add_pill(slide, 6.85, 1.35, 2.4, 0.4, "PROJECT NULLIFY", BG_DARK_CARD, TEXT_LIGHT_MUTED, BORDER_DARK)
    add_pill(slide, 9.4, 1.35, 2.8, 0.4, "READY FOR LIVE DEMO", BG_DARK_CARD, TEXT_LIGHT_MUTED, BORDER_DARK)

    # Massive Headline (Dramatic, Clean, Uncluttered)
    tx = slide.shapes.add_textbox(Inches(1.1), Inches(2.5), Inches(11.0), Inches(2.6))
    tf = tx.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p1 = tf.paragraphs[0]
    p1.text = "See it. Trace it."
    p1.font.name = FONT_DISPLAY
    p1.font.size = Pt(56)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT

    p2 = tf.add_paragraph()
    p2.text = "Nullify it."
    p2.font.name = FONT_DISPLAY
    p2.font.italic = True
    p2.font.size = Pt(56)
    p2.font.bold = True
    p2.font.color.rgb = ACCENT_EMERALD

    p3 = tf.add_paragraph()
    p3.text = "Autonomous AI Threat Defense — From Detection to Immunity in Under 15 Milliseconds."
    p3.font.name = FONT_HEADING
    p3.font.size = Pt(19)
    p3.font.color.rgb = TEXT_LIGHT_MUTED
    p3.space_before = Pt(14)

    # 3 High-Impact Capability Cards
    capabilities = [
        ("[ 01 // SPEED ]", "Sub-15ms Native C Engine", "C11 core analyzes binaries faster than a blink of an eye."),
        ("[ 02 // COGNITION ]", "6 Collaborative AI Agents", "Specialized agents team up to inspect, explain, and defend."),
        ("[ 03 // DEFENSE ]", "Instant Auto-YARA Immunity", "Writes instant defense rules to protect your whole network.")
    ]
    for i, (bcode, btitle, bdesc) in enumerate(capabilities):
        c_left = 1.1 + i * 3.8
        add_card(slide, c_left, 5.1, 3.6, 1.35, BG_DARK_CARD, BORDER_DARK)

        tx_c = slide.shapes.add_textbox(Inches(c_left + 0.25), Inches(5.2), Inches(3.1), Inches(1.15))
        tfc = tx_c.text_frame
        tfc.word_wrap = True
        tfc.margin_left = tfc.margin_top = tfc.margin_right = tfc.margin_bottom = 0

        p_ct = tfc.paragraphs[0]
        p_ct.text = f"{bcode}  {btitle}"
        p_ct.font.name = FONT_HEADING
        p_ct.font.size = Pt(14.5)
        p_ct.font.bold = True
        p_ct.font.color.rgb = TEXT_LIGHT

        p_cd = tfc.add_paragraph()
        p_cd.text = bdesc
        p_cd.font.name = FONT_BODY
        p_cd.font.size = Pt(12)
        p_cd.font.color.rgb = TEXT_LIGHT_MUTED
        p_cd.space_before = Pt(3)

    add_footer(slide, 1, 12, is_dark=True)
    set_notes(slide, """
Good morning, judges. Today we present NULLIFY, developed in partnership with EGATE Cybersecurity.
Our mission is simple: 'See it. Trace it. Nullify it.'
In modern cybersecurity, speed is everything. By the time a traditional security tool opens a file and spins up a sandbox, the damage is already done.
Nullify combines the raw speed of native C code with six autonomous AI agents. It catches zero-day malware and writes ready-to-use defense rules in under 15 milliseconds.
Let's start by introducing the vision behind EGATE and Nullify.
""")


def build_slide_02_logo_page(prs):
    """Slide 2: Dedicated Brand Identity & Logo Page (Exact Proportion)."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "BRAND IDENTITY", "EGATE & Nullify: Built for Sovereign Security", is_dark=False)

    # Left: Showcase Card with EGATE Logo (Centered, 100% Proportional)
    card_logo = add_card(slide, 0.9, 1.8, 4.8, 4.85, BG_WHITE, BORDER_LIGHT)
    add_image_proportional(slide, LOGO_PATH, 1.2, 2.1, 4.2, 3.2)

    # Caption below logo
    tx_lc = slide.shapes.add_textbox(Inches(1.2), Inches(5.65), Inches(4.2), Inches(0.8))
    tflc = tx_lc.text_frame
    tflc.margin_left = tflc.margin_top = tflc.margin_right = tflc.margin_bottom = 0
    plc = tflc.paragraphs[0]
    plc.text = "EGATE CYBERSECURITY GATEWAY"
    plc.alignment = PP_ALIGN.CENTER
    plc.font.name = FONT_MONO
    plc.font.size = Pt(11)
    plc.font.bold = True
    plc.font.color.rgb = ACCENT_EMERALD_DARK

    plc_sub = tflc.add_paragraph()
    plc_sub.text = "Next-Generation Autonomous Threat Defense"
    plc_sub.alignment = PP_ALIGN.CENTER
    plc_sub.font.name = FONT_BODY
    plc_sub.font.size = Pt(10.5)
    plc_sub.font.color.rgb = TEXT_MUTED

    # Right: The Story & Technological Meaning
    card_story = add_card(slide, 6.0, 1.8, 6.433, 4.85, BG_WHITE, BORDER_LIGHT)
    tx_s = slide.shapes.add_textbox(Inches(6.35), Inches(2.1), Inches(5.75), Inches(4.3))
    tfs = tx_s.text_frame
    tfs.word_wrap = True
    tfs.margin_left = tfs.margin_top = tfs.margin_right = tfs.margin_bottom = 0

    pillars = [
        ("THE GATEWAY: EGATE", "The zero-trust gatekeeper standing at the network perimeter. Every executable, script, and document must pass through the EGATE before execution is permitted."),
        ("THE ENGINE: NULLIFY", "The autonomous algorithmic brain. Built to reduce threat dwell time, attacker lateral movement, and incident triage latency to absolute zero (Nullify)."),
        ("THE VISUAL SYMBOLOGY", "Emerald Green represents active immunity and verified execution health. Obsidian Charcoal represents air-gapped sovereign privacy. Clean geometry represents mathematical certainty across 2,381 feature dimensions.")
    ]

    for idx, (ptitle, pbody) in enumerate(pillars):
        p_t = tfs.paragraphs[0] if idx == 0 else tfs.add_paragraph()
        p_t.text = f"[ {idx+1:02d} ]  {ptitle}"
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(15.5)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        if idx > 0:
            p_t.space_before = Pt(18)

        p_b = tfs.add_paragraph()
        p_b.text = pbody
        p_b.font.name = FONT_BODY
        p_b.font.size = Pt(13)
        p_b.font.color.rgb = TEXT_MUTED
        p_b.space_before = Pt(4)

    add_footer(slide, 2, 12, is_dark=False)
    set_notes(slide, """
On this slide, we introduce our brand identity: EGATE and Nullify.
The EGATE logo represents the secure perimeter gateway. In a zero-trust organization, no binary runs until the gateway inspects it.
Nullify is the autonomous algorithmic engine inside the gateway. It exists to reduce threat dwell time to zero.
Our design uses emerald green for active health and obsidian charcoal for air-gapped privacy.
Now let's examine the acute problem modern security teams face.
""")


def build_slide_03_problem(prs):
    """Slide 3: The Problem (Simple Words, Professional Badges)."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "THE PROBLEM", "Traditional Antivirus Can't Keep Up", is_dark=False)

    cards = [
        (
            "[ CHALLENGE 01 ]",
            "New Malware is Invisible",
            "Traditional antivirus checks for known hashes. But attackers constantly change their code, so signature blacklists fail on day one.",
            "450,000+ new attacks every day",
            ACCENT_CRIMSON,
            ACCENT_CRIMSON_BG
        ),
        (
            "[ CHALLENGE 02 ]",
            "Sandboxes are Too Slow",
            "Testing a file in a virtual machine takes 5 to 15 minutes. Firewalls and email filters cannot put live traffic on hold that long.",
            "15-minute delay is dangerous",
            ACCENT_AMBER,
            ACCENT_AMBER_BG
        ),
        (
            "[ CHALLENGE 03 ]",
            "Security Tools Crash",
            "Most open-source security tools are written in Python. When thousands of files hit at once, they lag, freeze, and run out of memory.",
            "Python runtime memory bottlenecks",
            ACCENT_BLUE,
            ACCENT_BLUE_BG
        )
    ]

    for i, (badge_text, title, desc, tag, acc, acc_bg) in enumerate(cards):
        left = 0.9 + i * 3.95
        add_card(slide, left, 1.8, 3.7, 4.0, BG_WHITE, BORDER_LIGHT)

        add_pill(slide, left + 0.3, 2.05, 2.2, 0.35, badge_text, acc_bg, acc)

        tx_b = slide.shapes.add_textbox(Inches(left + 0.3), Inches(2.55), Inches(3.1), Inches(2.4))
        tfb = tx_b.text_frame
        tfb.word_wrap = True
        tfb.margin_left = tfb.margin_top = tfb.margin_right = tfb.margin_bottom = 0

        pt = tfb.paragraphs[0]
        pt.text = title
        pt.font.name = FONT_HEADING
        pt.font.size = Pt(18)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_DARK

        pd = tfb.add_paragraph()
        pd.text = desc
        pd.font.name = FONT_BODY
        pd.font.size = Pt(13.5)
        pd.font.color.rgb = TEXT_MUTED
        pd.space_before = Pt(8)

        add_pill(slide, left + 0.3, 5.2, 3.1, 0.38, tag, acc_bg, acc)

    add_card(slide, 0.9, 6.0, 11.533, 0.65, BG_CARD_SUBTLE, BORDER_LIGHT)
    tx_t = slide.shapes.add_textbox(Inches(1.15), Inches(6.12), Inches(11.0), Inches(0.4))
    tft = tx_t.text_frame
    tft.margin_left = tft.margin_top = tft.margin_right = tft.margin_bottom = 0
    p = tft.paragraphs[0]
    r1 = p.add_run()
    r1.text = "THE REALITY: "
    r1.font.name = FONT_MONO
    r1.font.bold = True
    r1.font.size = Pt(12)
    r1.font.color.rgb = ACCENT_CRIMSON

    r2 = p.add_run()
    r2.text = "Organizations are forced to choose between fast but blind antivirus, or slow 15-minute sandboxes."
    r2.font.name = FONT_HEADING
    r2.font.size = Pt(13.5)
    r2.font.color.rgb = TEXT_DARK

    add_footer(slide, 3, 12, is_dark=False)
    set_notes(slide, """
Every security team faces three huge problems today:
1. New malware is invisible: 450,000 variants a day make static hashes obsolete.
2. Sandboxes take 15 minutes to run a single test. Real-time traffic can't wait that long.
3. Most modern tools use Python, which locks up and crashes under heavy traffic.
Nullify changes this completely.
""")


def build_slide_04_solution(prs):
    """Slide 4: The Solution (Large Text & Big Numbers)."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "THE SOLUTION", "Nullify: Real-Time Autonomous Defense", is_dark=False)

    add_card(slide, 0.9, 1.8, 6.8, 4.85, BG_WHITE, BORDER_LIGHT)
    tx_l = slide.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(6.2), Inches(4.3))
    tfl = tx_l.text_frame
    tfl.word_wrap = True
    tfl.margin_left = tfl.margin_top = tfl.margin_right = tfl.margin_bottom = 0

    sol_items = [
        ("[ 01 // SPEED ]", "Sub-Millisecond Native C Triage", "We rewrote heavy file inspection in pure C. It analyzes binaries in under 15 milliseconds — fast enough for live network firewalls."),
        ("[ 02 // COGNITION ]", "6 Specialized Autonomous Agents", "Instead of a single clumsy chatbot, six focused agents handle file headers, code patterns, behavioral logs, and threat reasoning."),
        ("[ 03 // ACTION ]", "Instant Auto-Defense & YARA", "Nullify doesn't just alert you. It automatically writes an enterprise YARA rule so you can block the threat across your entire network.")
    ]

    for i, (pbadge, stitle, sdesc) in enumerate(sol_items):
        p_t = tfl.paragraphs[0] if i == 0 else tfl.add_paragraph()
        p_t.text = f"{pbadge}  {stitle}"
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(17)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        if i > 0:
            p_t.space_before = Pt(18)

        p_d = tfl.add_paragraph()
        p_d.text = sdesc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(13.5)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_before = Pt(4)

    stats = [
        ("< 15 ms", "FULL TRIAGE SPEED", "Analysis completed in milliseconds", ACCENT_EMERALD_DARK),
        ("500x", "FASTER IN C", "Native C engine vs standard Python", ACCENT_BLUE),
        ("100%", "LOCAL & PRIVATE", "Zero telemetry leaves your network", ACCENT_AMBER)
    ]
    for j, (snum, slbl, sdesc, scolor) in enumerate(stats):
        top_pos = 1.8 + j * 1.68
        add_card(slide, 7.95, top_pos, 4.48, 1.5, BG_WHITE, BORDER_LIGHT)

        tx_s = slide.shapes.add_textbox(Inches(8.2), Inches(top_pos + 0.15), Inches(4.0), Inches(1.2))
        tfs = tx_s.text_frame
        tfs.word_wrap = True
        tfs.margin_left = tfs.margin_top = tfs.margin_right = tfs.margin_bottom = 0

        p1 = tfs.paragraphs[0]
        p1.text = snum
        p1.font.name = FONT_DISPLAY
        p1.font.size = Pt(36)
        p1.font.bold = True
        p1.font.color.rgb = scolor

        p2 = tfs.add_paragraph()
        p2.text = f"{slbl}  •  {sdesc}"
        p2.font.name = FONT_HEADING
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        p2.space_before = Pt(2)

    add_footer(slide, 4, 12, is_dark=False)
    set_notes(slide, """
Here is how Nullify works:
1. It is fast: We moved the heavy lifting to pure C. It analyzes files in under 15 milliseconds.
2. It is accurate: Six focused AI agents collaborate to trace the file's behavior.
3. It takes action: It writes ready-to-deploy defense rules immediately.
No waiting 15 minutes for a sandbox. No leaking sensitive files to cloud APIs.
""")


def build_slide_05_agents(prs):
    """Slide 5: The 6 AI Agents (Clean 2-Stage Flow, Generous Space, Zero Extra Photos)."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "ARCHITECTURE", "How the 6 AI Agents Work Together", is_dark=False)

    # Left Card: Stage 1 Fast C Inspection
    add_card(slide, 0.9, 1.8, 5.6, 4.85, BG_WHITE, BORDER_LIGHT)
    add_pill(slide, 1.2, 2.05, 3.2, 0.38, "[ STAGE 1: NATIVE C SPEED ]", ACCENT_EMERALD_BG, ACCENT_EMERALD_DARK)

    tx_s1 = slide.shapes.add_textbox(Inches(1.2), Inches(2.6), Inches(5.0), Inches(3.8))
    tf1 = tx_s1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0

    s1_items = [
        ("Agent 1: Triage Agent", "Checks magic bytes, verifies PE/ELF headers, and streams MD5, SHA-1, and SHA-256 hashes in a single pass in under 1 millisecond."),
        ("Agent 2: Static Analysis Agent", "Traverses Windows PE Import Directory directly in memory. Detects dangerous APIs (memory injection, keylogging) and backdoor registry keys in 0.1ms.")
    ]
    for idx, (atitle, adesc) in enumerate(s1_items):
        p_t = tf1.paragraphs[0] if idx == 0 else tf1.add_paragraph()
        p_t.text = atitle
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(17)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        if idx > 0:
            p_t.space_before = Pt(22)

        p_d = tf1.add_paragraph()
        p_d.text = adesc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(14)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_before = Pt(6)

    # Right Card: Stage 2 Deep AI Intelligence
    add_card(slide, 6.83, 1.8, 5.6, 4.85, BG_WHITE, BORDER_LIGHT)
    add_pill(slide, 7.13, 2.05, 3.4, 0.38, "[ STAGE 2: AI COGNITION & DEFENSE ]", ACCENT_BLUE_BG, ACCENT_BLUE)

    tx_s2 = slide.shapes.add_textbox(Inches(7.13), Inches(2.6), Inches(5.0), Inches(3.8))
    tf2 = tx_s2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0

    s2_items = [
        ("Agent 3: Behavioral Agent", "Traces process execution trees and correlates Windows Sysmon logs."),
        ("Agent 4: Classification Agent", "Scores 2,381 features using an ML model trained on 1.1 million binaries."),
        ("Agent 5: Reasoning Agent", "Explains *why* the file is malicious in plain English for security analysts."),
        ("Agent 6: Defense Agent", "Automatically writes a clean, syntax-validated YARA rule to block it.")
    ]
    for jdx, (btitle, bdesc) in enumerate(s2_items):
        p_bt = tf2.paragraphs[0] if jdx == 0 else tf2.add_paragraph()
        p_bt.text = btitle
        p_bt.font.name = FONT_HEADING
        p_bt.font.size = Pt(15.5)
        p_bt.font.bold = True
        p_bt.font.color.rgb = TEXT_DARK
        if jdx > 0:
            p_bt.space_before = Pt(10)

        p_bd = tf2.add_paragraph()
        p_bd.text = bdesc
        p_bd.font.name = FONT_BODY
        p_bd.font.size = Pt(13)
        p_bd.font.color.rgb = TEXT_MUTED
        p_bd.space_before = Pt(3)

    add_footer(slide, 5, 12, is_dark=False)
    set_notes(slide, """
Notice how our agents are structured:
Stage 1 handles raw speed: Triage and Static Analysis run in native C code. They take less than a millisecond to dissect headers, hashes, and imports.
Stage 2 handles intelligence: Behavioral analysis, 2,381-feature machine learning, human-readable reasoning, and automatic YARA rule generation.
Each agent does one job perfectly.
""")


def build_slide_06_c_engine(prs):
    """Slide 6: Why It's Fast: The Native C Engine."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "PERFORMANCE BREAKTHROUGH", "The Secret to Our Speed: Native C Code", is_dark=False)

    comparisons = [
        (
            "[ ENGINE // 01 ]",
            "PE Import Parsing",
            "Python: 50.0 ms  →  C: 0.1 ms",
            "500x Faster",
            "Reads executable import tables directly in memory without slow Python libraries.",
            ACCENT_EMERALD_DARK
        ),
        (
            "[ ENGINE // 02 ]",
            "Pattern Scanner",
            "Python: 15.4 ms  →  C: 0.8 ms",
            "18x Faster",
            "Finds hidden registry keys, download cradles, and backdoor strings in a single pass.",
            ACCENT_BLUE
        ),
        (
            "[ ENGINE // 03 ]",
            "File Multi-Hashing",
            "Python: 8.9 ms  →  C: 1.1 ms",
            "8x Faster",
            "Streams 64KB blocks, updating MD5, SHA-1, and SHA-256 at the exact same time.",
            ACCENT_AMBER
        )
    ]

    for i, (badge_text, title, times, speedup, desc, color) in enumerate(comparisons):
        left = 0.9 + i * 3.95
        add_card(slide, left, 1.8, 3.7, 4.0, BG_WHITE, BORDER_LIGHT)

        add_pill(slide, left + 0.3, 2.0, 2.0, 0.32, badge_text, BG_CARD_SUBTLE, color)

        tx = slide.shapes.add_textbox(Inches(left + 0.3), Inches(2.4), Inches(3.1), Inches(3.2))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_sp = tf.paragraphs[0]
        p_sp.text = speedup
        p_sp.font.name = FONT_DISPLAY
        p_sp.font.size = Pt(38)
        p_sp.font.bold = True
        p_sp.font.color.rgb = color

        p_t = tf.add_paragraph()
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(18)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_t.space_before = Pt(4)

        p_time = tf.add_paragraph()
        p_time.text = times
        p_time.font.name = FONT_MONO
        p_time.font.size = Pt(11)
        p_time.font.bold = True
        p_time.font.color.rgb = color
        p_time.space_before = Pt(6)

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(13)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_before = Pt(8)

    add_card(slide, 0.9, 6.0, 11.533, 0.65, BG_CARD_SUBTLE, BORDER_LIGHT)
    tx_b = slide.shapes.add_textbox(Inches(1.15), Inches(6.12), Inches(11.0), Inches(0.4))
    tfb = tx_b.text_frame
    tfb.margin_left = tfb.margin_top = tfb.margin_right = tfb.margin_bottom = 0
    pb = tfb.paragraphs[0]
    r1 = pb.add_run()
    r1.text = "ZERO EXTERNAL DEPENDENCIES: "
    r1.font.name = FONT_MONO
    r1.font.bold = True
    r1.font.size = Pt(12)
    r1.font.color.rgb = ACCENT_EMERALD_DARK

    r2 = pb.add_run()
    r2.text = "Pure C11 (-O3) with built-in RFC 3174 SHA-1 and MD5. No OpenSSL link errors, plus automatic Python fallback."
    r2.font.name = FONT_HEADING
    r2.font.size = Pt(13)
    r2.font.color.rgb = TEXT_DARK

    add_footer(slide, 6, 12, is_dark=False)
    set_notes(slide, """
Why is Nullify so fast? Because we identified the slowest parts of Python security tools and rewrote them in native C.
- Parsing Windows PE imports used to take 50 milliseconds. In C, it takes 0.1 milliseconds. That is over 500x faster.
- Pattern scanning is 18x faster.
- Concurrent file hashing is 8x faster.
And we built it with zero external C dependencies — no OpenSSL link issues, no memory leaks.
""")


def build_slide_07_ml(prs):
    """Slide 7: Machine Learning (Simple Words, High Confidence)."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "MACHINE LEARNING", "Trained on 1.1 Million Real Binaries", is_dark=False)

    cards = [
        (
            "[ FEATURE SPACE ]",
            "2,381 Features Analyzed",
            "Nullify analyzes 2,381 unique characteristics of each file: byte randomness (entropy), printable strings, section sizes, and header anomalies.",
            ACCENT_EMERALD_DARK
        ),
        (
            "[ VALIDATION ]",
            "99.9% Proven Accuracy",
            "Trained on 1.1 million verified benign and malicious files from the EMBER benchmark. Gradient-boosted trees classify threats without hallucinating.",
            ACCENT_BLUE
        ),
        (
            "[ SMART GUARD ]",
            "Zero False Alarms on Linux",
            "Most antivirus tools trigger false alarms on Linux files because they try to force Windows rules. Nullify detects file types accurately so safe code isn't flagged.",
            ACCENT_AMBER
        )
    ]

    for i, (badge_text, title, desc, color) in enumerate(cards):
        left = 0.9 + i * 3.95
        add_card(slide, left, 1.8, 3.7, 4.85, BG_WHITE, BORDER_LIGHT)

        add_pill(slide, left + 0.3, 2.1, 2.2, 0.35, badge_text, BG_CARD_SUBTLE, color)

        tx = slide.shapes.add_textbox(Inches(left + 0.3), Inches(2.65), Inches(3.1), Inches(3.8))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(20)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(14)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_before = Pt(14)

    add_footer(slide, 7, 12, is_dark=False)
    set_notes(slide, """
A lot of security AI projects use large language models that make uncalibrated guesses.
Nullify uses proven gradient-boosted trees trained on 1.1 million files from the EMBER benchmark.
We look at 2,381 structural features. And we engineered a specific Linux guard so non-Windows binaries never trigger false positives.
""")


def build_slide_08_defense(prs):
    """Slide 8: Active Defense & YARA (Clear Impact)."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "ACTIVE DEFENSE", "From Threat Detection to Immunity in Seconds", is_dark=False)

    add_card(slide, 0.9, 1.8, 5.6, 4.85, BG_WHITE, BORDER_LIGHT)
    add_pill(slide, 1.2, 2.05, 3.4, 0.35, "[ AUTOMATED IMMUNITY ]", ACCENT_CRIMSON_BG, ACCENT_CRIMSON)

    tx_l = slide.shapes.add_textbox(Inches(1.2), Inches(2.55), Inches(5.0), Inches(3.9))
    tfl = tx_l.text_frame
    tfl.word_wrap = True
    tfl.margin_left = tfl.margin_top = tfl.margin_right = tfl.margin_bottom = 0

    p_title = tfl.paragraphs[0]
    p_title.text = "Tells You What Happened & Blocks It Everywhere"
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(20)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_DARK

    bullets = [
        ("Explains the Threat Clearly", "Identifies the exact techniques the attacker used (e.g. injecting code into processes or setting up secret auto-run keys)."),
        ("Maps to MITRE ATT&CK", "Industry-standard tagging (T1055, T1547) so security teams understand the risk instantly."),
        ("Writes the Defense Rule", "Generates a complete, ready-to-use YARA rule that your firewalls, EDR, and mail filters can apply right away.")
    ]
    for btitle, bdesc in bullets:
        pb_t = tfl.add_paragraph()
        pb_t.text = f"• {btitle}:"
        pb_t.font.name = FONT_HEADING
        pb_t.font.size = Pt(15)
        pb_t.font.bold = True
        pb_t.font.color.rgb = TEXT_DARK
        pb_t.space_before = Pt(12)

        pb_d = tfl.add_paragraph()
        pb_d.text = bdesc
        pb_d.font.name = FONT_BODY
        pb_d.font.size = Pt(13)
        pb_d.font.color.rgb = TEXT_MUTED
        pb_d.space_before = Pt(2)

    add_card(slide, 6.83, 1.8, 5.6, 4.85, BG_CHARCOAL, BORDER_DARK)
    tx_r = slide.shapes.add_textbox(Inches(7.13), Inches(2.1), Inches(5.0), Inches(4.3))
    tfr = tx_r.text_frame
    tfr.word_wrap = True
    tfr.margin_left = tfr.margin_top = tfr.margin_right = tfr.margin_bottom = 0

    p_rt = tfr.paragraphs[0]
    p_rt.text = "AUTO-GENERATED YARA DEFENSE RULE"
    p_rt.font.name = FONT_MONO
    p_rt.font.size = Pt(11)
    p_rt.font.bold = True
    p_rt.font.color.rgb = ACCENT_EMERALD

    yara_code = """rule Nullify_AutoDefense_Trojan {
    meta:
        description = "Auto-generated by Nullify"
        threat      = "Trojan / Backdoor"
        confidence  = "98.4%"
    strings:
        $run_key = "CurrentVersion\\\\Run" nocase
        $ps_exec = "powershell -enc" nocase
        $inject  = "VirtualAllocEx"
    condition:
        uint16(0) == 0x5A4D and
        filesize < 5MB and
        (2 of ($*))
}"""
    py = tfr.add_paragraph()
    py.text = yara_code
    py.font.name = FONT_MONO
    py.font.size = Pt(12)
    py.font.color.rgb = TEXT_LIGHT_MUTED
    py.space_before = Pt(12)

    p_sub = tfr.add_paragraph()
    p_sub.text = "✓ Ready to push to CrowdStrike, SentinelOne, or Windows Defender."
    p_sub.font.name = FONT_HEADING
    p_sub.font.size = Pt(12.5)
    p_sub.font.bold = True
    p_sub.font.color.rgb = ACCENT_EMERALD
    p_sub.space_before = Pt(16)

    add_footer(slide, 8, 12, is_dark=False)
    set_notes(slide, """
Telling an analyst 'this file is bad' is only half the job.
Nullify explains why: it maps the threat to MITRE ATT&CK tactics.
And then it writes the actual YARA rule shown on screen.
You can copy this rule and deploy it to your firewalls and endpoints in seconds.
""")


def build_slide_09_comparison(prs):
    """Slide 9: Benchmarks & Comparison Showdown."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "BENCHMARKS", "How Nullify Compares to the Rest", is_dark=False)

    benchmarks = [
        ("13.2 ms", "FULL TRIAGE TIME", "Complete static inspection & hashing", ACCENT_EMERALD_DARK),
        ("75 files / sec", "SINGLE-CORE THROUGHPUT", "Millions of files processed daily", ACCENT_BLUE),
        ("62 / 62", "AUTOMATED TESTS PASSING", "100% test suite reliability", ACCENT_AMBER)
    ]
    for i, (bnum, blbl, bsub, bcolor) in enumerate(benchmarks):
        left = 0.9 + i * 3.95
        add_card(slide, left, 1.8, 3.7, 1.6, BG_WHITE, BORDER_LIGHT)

        tx = slide.shapes.add_textbox(Inches(left + 0.25), Inches(1.95), Inches(3.2), Inches(1.3))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p1 = tf.paragraphs[0]
        p1.text = bnum
        p1.font.name = FONT_DISPLAY
        p1.font.size = Pt(36)
        p1.font.bold = True
        p1.font.color.rgb = bcolor

        p2 = tf.add_paragraph()
        p2.text = blbl
        p2.font.name = FONT_HEADING
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = bsub
        p3.font.name = FONT_BODY
        p3.font.size = Pt(11)
        p3.font.color.rgb = TEXT_MUTED

    add_card(slide, 0.9, 3.65, 11.533, 3.0, BG_WHITE, BORDER_LIGHT)
    tx_t = slide.shapes.add_textbox(Inches(1.2), Inches(3.85), Inches(11.0), Inches(2.6))
    tft = tx_t.text_frame
    tft.word_wrap = True
    tft.margin_left = tft.margin_top = tft.margin_right = tft.margin_bottom = 0

    p_kt = tft.paragraphs[0]
    p_kt.text = "SPEED & CAPABILITY SHOWDOWN"
    p_kt.font.name = FONT_MONO
    p_kt.font.size = Pt(11)
    p_kt.font.bold = True
    p_kt.font.color.rgb = ACCENT_EMERALD_DARK

    rows = [
        ("Nullify (Our System)", "13.2 ms", "Catches Zero-Days", "Auto-Writes YARA Rules", True),
        ("Traditional Antivirus", "5.0 ms", "Blind to New Malware", "No YARA Rules", False),
        ("Cloud Sandboxes (Cuckoo)", "15 Minutes", "Too Slow for Edge Routers", "Raw Log Dumps Only", False),
        ("Standard Python Tools", "85.0 ms", "High Memory / Crashes", "Manual Scripting Required", False)
    ]

    for tool, speed, detection, action, is_hl in rows:
        p_row = tft.add_paragraph()
        p_row.text = f"{tool:<28} | {speed:<14} | {detection:<26} | {action}"
        p_row.font.name = FONT_MONO
        p_row.font.size = Pt(13)
        p_row.font.bold = is_hl
        p_row.font.color.rgb = ACCENT_EMERALD_DARK if is_hl else TEXT_MUTED
        p_row.space_before = Pt(10)

    add_footer(slide, 9, 12, is_dark=False)
    set_notes(slide, """
Look at the numbers on screen:
A cloud sandbox takes 15 minutes.
Standard Python tools take 85 milliseconds and crash under load.
Traditional antivirus is fast, but blind to new malware.
Nullify gives you the best of both: 13.2 millisecond speed, zero-day machine learning, and automated YARA rules.
""")


def build_slide_10_ux(prs):
    """Slide 10: User Experience (Web & CLI)."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "USER EXPERIENCE", "Two Intuitive Ways to Use Nullify", is_dark=False)

    add_card(slide, 0.9, 1.8, 5.6, 4.85, BG_WHITE, BORDER_LIGHT)
    add_pill(slide, 1.2, 2.05, 3.2, 0.35, "[ WEB INTERFACE ]", ACCENT_EMERALD_BG, ACCENT_EMERALD_DARK)

    tx_w = slide.shapes.add_textbox(Inches(1.2), Inches(2.55), Inches(5.0), Inches(3.9))
    tfw = tx_w.text_frame
    tfw.word_wrap = True
    tfw.margin_left = tfw.margin_top = tfw.margin_right = tfw.margin_bottom = 0

    pw_t = tfw.paragraphs[0]
    pw_t.text = "Luxury Web Dashboard (localhost:8000)"
    pw_t.font.name = FONT_HEADING
    pw_t.font.size = Pt(20)
    pw_t.font.bold = True
    pw_t.font.color.rgb = TEXT_DARK

    w_features = [
        ("Drag-and-Drop Scanning", "Drop any file to see real-time analysis in milliseconds."),
        ("Live Confidence Radar", "See risk percentage and threat family classification clearly."),
        ("Built-in Demo Samples", "One-click buttons to test safe trojans, ransomware, and benign files."),
        ("1-Click YARA Copy", "Instantly copy auto-generated rules to your clipboard.")
    ]
    for wtitle, wdesc in w_features:
        p_item = tfw.add_paragraph()
        p_item.text = f"• {wtitle}: {wdesc}"
        p_item.font.name = FONT_BODY
        p_item.font.size = Pt(13.5)
        p_item.font.color.rgb = TEXT_MUTED
        p_item.space_before = Pt(10)

    add_card(slide, 6.83, 1.8, 5.6, 4.85, BG_CHARCOAL, BORDER_DARK)
    tx_c = slide.shapes.add_textbox(Inches(7.13), Inches(2.1), Inches(5.0), Inches(4.3))
    tfc = tx_c.text_frame
    tfc.word_wrap = True
    tfc.margin_left = tfc.margin_top = tfc.margin_right = tfc.margin_bottom = 0

    pc_k = tfc.paragraphs[0]
    pc_k.text = "[ TERMINAL INTERFACE ]"
    pc_k.font.name = FONT_MONO
    pc_k.font.size = Pt(11)
    pc_k.font.bold = True
    pc_k.font.color.rgb = ACCENT_EMERALD

    pc_t = tfc.add_paragraph()
    pc_t.text = "Single-Command CLI ($ nullify)"
    pc_t.font.name = FONT_HEADING
    pc_t.font.size = Pt(20)
    pc_t.font.bold = True
    pc_t.font.color.rgb = TEXT_LIGHT
    pc_t.space_before = Pt(6)

    cli_text = """$ nullify
========================================
   See it. Trace it. Nullify it.
========================================
[1] Quick Scan
[2] Deep Detonation
[3] Behavioral Log
[4] Batch Scan Folder
[5] Launch Web Console
[0] Exit

Select option: 1
> Scanning suspicious_binary.exe ...
> VERDICT: MALICIOUS (98.4% Confidence)
> Parsed in 0.1ms • YARA Rule Created!"""

    pc_code = tfc.add_paragraph()
    pc_code.text = cli_text
    pc_code.font.name = FONT_MONO
    pc_code.font.size = Pt(11)
    pc_code.font.color.rgb = TEXT_LIGHT_MUTED
    pc_code.space_before = Pt(12)

    add_footer(slide, 10, 12, is_dark=False)
    set_notes(slide, """
We built Nullify with two clean interfaces:
On the left: A modern web console running at localhost:8000. Drag and drop any file, see live confidence scores, and copy YARA rules.
On the right: A single-command terminal interface. Just type 'nullify' with no confusing arguments, and an interactive menu guides you through scanning.
""")


def build_slide_11_privacy(prs):
    """Slide 11: 100% Private & Air-Gapped."""
    slide = create_slide(prs, is_dark=False)
    add_header(slide, "SECURITY & PRIVACY", "Your Data Never Leaves Your Network", is_dark=False)

    pillars = [
        (
            "[ PRIVACY ]",
            "100% Local Execution",
            "Zero Cloud Telemetry Leakage",
            "Hospitals, defense contractors, and banks cannot upload confidential files to public cloud APIs. Nullify runs 100% on your hardware. Not a single byte is sent over the internet.",
            ACCENT_EMERALD_DARK
        ),
        (
            "[ INTEGRATION ]",
            "SIEM & SOAR Ready",
            "Production REST API Built In",
            "Built with FastAPI and OpenAPI. Exposes clean REST endpoints so your security operations team can integrate it with Splunk, Microsoft Sentinel, or Cortex XSOAR in minutes.",
            ACCENT_BLUE
        ),
        (
            "[ DEPLOYMENT ]",
            "Air-Gapped & Offline",
            "Docker & Containerized Core",
            "Ships as a lightweight Docker container or standalone binary. Operates seamlessly inside secure, offline, air-gapped data centers with zero external dependencies.",
            ACCENT_AMBER
        )
    ]

    for i, (badge_text, title, sub, desc, color) in enumerate(pillars):
        left = 0.9 + i * 3.95
        add_card(slide, left, 1.8, 3.7, 4.85, BG_WHITE, BORDER_LIGHT)

        add_pill(slide, left + 0.3, 2.1, 2.2, 0.35, badge_text, BG_CARD_SUBTLE, color)

        tx = slide.shapes.add_textbox(Inches(left + 0.3), Inches(2.65), Inches(3.1), Inches(3.8))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(19)
        p_t.font.bold = True
        p_t.font.color.rgb = color

        p_s = tf.add_paragraph()
        p_s.text = sub
        p_s.font.name = FONT_HEADING
        p_s.font.size = Pt(14)
        p_s.font.bold = True
        p_s.font.color.rgb = TEXT_DARK
        p_s.space_before = Pt(6)

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(13.5)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_before = Pt(12)

    add_footer(slide, 11, 12, is_dark=False)
    set_notes(slide, """
In enterprise security, data privacy is non-negotiable.
When companies send files to VirusTotal or cloud sandboxes, proprietary source code and intellectual property leak out.
Nullify runs 100% on-premise. It works in air-gapped environments with zero internet access, and connects easily to Splunk or Microsoft Sentinel via our REST API.
""")


def build_slide_12_ending(prs):
    """Slide 12: High-Impact Action-Oriented Ending with EGATE Logo (Exact Proportion)."""
    slide = create_slide(prs, is_dark=True)

    frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.6), Inches(12.133), Inches(6.3))
    set_flat(frame, BG_CHARCOAL, BORDER_DARK, border_width_pt=1.5)

    # Top Brand Bar with EGATE Logo (Exact Proportion)
    card_logo = add_card(slide, 1.1, 1.0, 2.6, 1.1, BG_WHITE, None)
    add_image_proportional(slide, LOGO_PATH, 1.2, 1.05, 2.4, 1.0)

    add_pill(slide, 3.9, 1.35, 2.8, 0.4, "●  READY FOR LIVE DEMO", BG_DARK_CARD, ACCENT_EMERALD, BORDER_DARK)
    add_pill(slide, 6.85, 1.35, 2.4, 0.4, "EGATE & NULLIFY", BG_DARK_CARD, TEXT_LIGHT_MUTED, BORDER_DARK)

    # Big Dramatic Title
    tx = slide.shapes.add_textbox(Inches(1.1), Inches(2.35), Inches(11.0), Inches(1.8))
    tf = tx.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p1 = tf.paragraphs[0]
    p1.text = "Let's Run a Live Test."
    p1.font.name = FONT_DISPLAY
    p1.font.size = Pt(54)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT

    p2 = tf.add_paragraph()
    p2.text = "Pick any file. Watch Nullify inspect, classify, and neutralize it in milliseconds."
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(20)
    p2.font.color.rgb = TEXT_LIGHT_MUTED
    p2.space_before = Pt(10)

    # 3 Big Confidence Milestones
    milestones = [
        ("[ 01 // PRODUCTION ]", "Fully Functional Now", "Web console, CLI, and C-engine are compiled and running live right now."),
        ("[ 02 // QUALITY ]", "62 / 62 Tests Green", "Comprehensive automated test suite guarantees zero regressions."),
        ("[ 03 // OPEN CODE ]", "Verified on GitHub", "Clean, documented, production-ready codebase ready for inspection.")
    ]
    for i, (mcode, mtitle, mdesc) in enumerate(milestones):
        c_left = 1.1 + i * 3.8
        add_card(slide, c_left, 4.3, 3.6, 1.45, BG_DARK_CARD, BORDER_DARK)

        tx_m = slide.shapes.add_textbox(Inches(c_left + 0.25), Inches(4.45), Inches(3.1), Inches(1.15))
        tfm = tx_m.text_frame
        tfm.word_wrap = True
        tfm.margin_left = tfm.margin_top = tfm.margin_right = tfm.margin_bottom = 0

        pm_c = tfm.paragraphs[0]
        pm_c.text = mcode
        pm_c.font.name = FONT_MONO
        pm_c.font.size = Pt(9.5)
        pm_c.font.bold = True
        pm_c.font.color.rgb = ACCENT_EMERALD

        pm_t = tfm.add_paragraph()
        pm_t.text = mtitle
        pm_t.font.name = FONT_HEADING
        pm_t.font.size = Pt(15.5)
        pm_t.font.bold = True
        pm_t.font.color.rgb = TEXT_LIGHT
        pm_t.space_before = Pt(2)

        pm_d = tfm.add_paragraph()
        pm_d.text = mdesc
        pm_d.font.name = FONT_BODY
        pm_d.font.size = Pt(12)
        pm_d.font.color.rgb = TEXT_LIGHT_MUTED
        pm_d.space_before = Pt(4)

    # Bottom Live Demo Banner
    add_card(slide, 1.1, 5.9, 11.133, 0.75, BG_DARK_CARD, BORDER_DARK)
    tx_c = slide.shapes.add_textbox(Inches(1.3), Inches(6.05), Inches(10.7), Inches(0.5))
    tfc = tx_c.text_frame
    tfc.margin_left = tfc.margin_top = tfc.margin_right = tfc.margin_bottom = 0
    pc = tfc.paragraphs[0]

    rc1 = pc.add_run()
    rc1.text = "TRY IT LIVE: "
    rc1.font.name = FONT_MONO
    rc1.font.bold = True
    rc1.font.size = Pt(12)
    rc1.font.color.rgb = ACCENT_EMERALD

    rc2 = pc.add_run()
    rc2.text = "Terminal: $ nullify   |   Web: http://localhost:8000   |   GitHub: Nate-br/nullify"
    rc2.font.name = FONT_MONO
    rc2.font.size = Pt(12)
    rc2.font.color.rgb = TEXT_LIGHT

    add_footer(slide, 12, 12, is_dark=True)
    set_notes(slide, """
In conclusion: Nullify is not a mock-up or a slide concept. It is a live, working, tested system.
We invite the judges right now to give us any sample — a trojan, ransomware, or a safe binary — and watch Nullify classify it and generate defense rules live on screen.
Thank you, and we welcome your questions!
""")


def main():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    print("Building 12-slide executive deck with ONLY EGATE logo (exact proportions, zero extra photos)...")
    build_slide_01_cover(prs)
    build_slide_02_logo_page(prs)
    build_slide_03_problem(prs)
    build_slide_04_solution(prs)
    build_slide_05_agents(prs)
    build_slide_06_c_engine(prs)
    build_slide_07_ml(prs)
    build_slide_08_defense(prs)
    build_slide_09_comparison(prs)
    build_slide_10_ux(prs)
    build_slide_11_privacy(prs)
    build_slide_12_ending(prs)

    output = "nullify_presentation.pptx"
    prs.save(output)
    print(f"Presentation saved successfully to: {output}")


if __name__ == "__main__":
    main()
