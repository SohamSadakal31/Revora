import os
import sys
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class RevoraComprehensiveDoc(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 18, 16)
        self.in_cover = True

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(100, 116, 139) # slate-500
        self.cell(0, 6, 'REVORA: USED CAR VALUATION & MARKET INTELLIGENCE PLATFORM  |  SYSTEM EXPLANATION', 
                  border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(2)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184) # slate-400
        self.cell(0, 5, f'Page {self.page_no()} of {{nb}}  *  Revora Complete Architecture, ML & Implementation Guide', 
                  align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ------------------ TYPOGRAPHY HELPERS ------------------
    def chapter_header(self, number, title):
        self.ln(4)
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(30, 58, 138) # Navy #1e3a8a
        self.cell(0, 8, f"Chapter {number}: {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(37, 99, 235) # Blue
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), self.get_x() + 178, self.get_y())
        self.ln(4)

    def section_header(self, title):
        self.ln(2)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(15, 23, 42) # Slate-900
        self.cell(0, 6.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def sub_section_header(self, title):
        self.ln(1)
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(30, 58, 138)
        self.cell(0, 5.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def p(self, text):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(51, 65, 85) # Slate-700
        self.multi_cell(0, 4.7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def bullet(self, title, text):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(30, 58, 138)
        self.cell(4, 4.6, chr(149), new_x=XPos.RIGHT, new_y=YPos.TOP)
        prefix = f"{title}: " if title else ""
        self.cell(self.get_string_width(prefix) + 1, 4.6, prefix, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.2)

    def code_block(self, code_text):
        self.set_fill_color(241, 245, 249) # Slate-100
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.set_font('Courier', '', 7.5)
        self.set_text_color(15, 23, 42)
        
        # Calculate height
        lines = code_text.strip().split('\n')
        line_height = 3.8
        total_height = len(lines) * line_height + 4
        
        # Check page break
        if self.get_y() + total_height > 275:
            self.add_page()
            
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 178, total_height, style='FD')
        self.set_xy(x + 2, y + 2)
        for line in lines:
            # truncate long line if needed
            self.cell(0, line_height, line[:105], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y + total_height + 2)

    def callout(self, title, content, bg=(240, 247, 255), border=(191, 219, 254), title_color=(30, 58, 138)):
        self.set_fill_color(*bg)
        self.set_draw_color(*border)
        self.set_line_width(0.4)
        
        # rough height calculation
        h = 16 + (len(content) // 120) * 4
        if self.get_y() + h > 275:
            self.add_page()
            
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 178, h, style='FD')
        self.set_xy(x + 3, y + 2)
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(*title_color)
        self.cell(0, 4.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_xy(x + 3, y + 7)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(51, 65, 85)
        self.multi_cell(172, 3.8, content, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y + h + 2.5)

    def table(self, headers, rows, col_widths, align_cols=None):
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(226, 232, 240)
        self.set_text_color(15, 23, 42)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.2)
        
        # Check if table fits, if not break
        est_height = 6.5 + len(rows) * 5.5
        if self.get_y() + est_height > 275:
            self.add_page()
            
        # Header
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6, h, border=1, fill=True, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.ln(6)
        
        # Rows
        self.set_font('Helvetica', '', 7.8)
        fill = False
        for row in rows:
            fill = not fill
            self.set_fill_color(248, 250, 252 if fill else 255)
            self.set_text_color(51, 65, 85)
            for i, val in enumerate(row):
                align = align_cols[i] if align_cols else 'L'
                self.cell(col_widths[i], 5.3, str(val)[:45], border=1, fill=True, align=align,
                          new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.ln(5.3)
        self.ln(2.5)

print("PDF Class defined.")
