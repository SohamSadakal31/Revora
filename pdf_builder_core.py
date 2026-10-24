import os
import sys
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class RevoraSystemGuide(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(15, 16, 15)

    def normalize_text(self, text):
        if text:
            text = (str(text)
                    .replace('—', '--')
                    .replace('–', '-')
                    .replace('•', '-')
                    .replace('▲', '^')
                    .replace('▼', 'v')
                    .replace('’', "'")
                    .replace('‘', "'")
                    .replace('”', '"')
                    .replace('“', '"')
                    .replace('₹', 'INR ')
                    .replace('±', '+/-')
                    .replace('≈', '~')
                    .replace('≥', '>=')
                    .replace('≤', '<=')
                    .replace('×', 'x')
                    .replace('·', '*'))
        return super().normalize_text(text)

    def header(self):
        if self.page_no() <= 2:
            return
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, 'REVORA: USED CAR VALUATION & MARKET INTELLIGENCE PLATFORM  |  SYSTEM EXPLANATION', 
                  border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(2)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, f'Page {self.page_no()} of {{nb}}  *  Revora Architecture, ML & Implementation Guide', 
                  align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def chapter(self, number, title):
        if self.page_no() > 2:
            self.add_page()
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(30, 58, 138)
        self.cell(0, 8, f"Chapter {number}: {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(37, 99, 235)
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), self.get_x() + 180, self.get_y())
        self.ln(3.5)

    def sec(self, title):
        self.ln(2)
        self.set_font('Helvetica', 'B', 10.5)
        self.set_text_color(15, 23, 42)
        self.cell(0, 6.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.8)

    def subsec(self, title):
        self.ln(1)
        self.set_font('Helvetica', 'B', 9.2)
        self.set_text_color(30, 58, 138)
        self.cell(0, 5.2, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.6)

    def p(self, text):
        self.set_font('Helvetica', '', 8.6)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.6)

    def bullet(self, title, text):
        self.set_font('Helvetica', 'B', 8.6)
        self.set_text_color(30, 58, 138)
        self.cell(4, 4.3, '-', new_x=XPos.RIGHT, new_y=YPos.TOP)
        prefix = f"{title}: " if title else ""
        self.cell(self.get_string_width(prefix) + 1, 4.3, prefix, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font('Helvetica', '', 8.6)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.3, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def code(self, code_text):
        self.set_fill_color(241, 245, 249)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.set_font('Courier', '', 7.2)
        self.set_text_color(15, 23, 42)
        
        lines = code_text.strip().split('\n')
        line_height = 3.5
        total_height = len(lines) * line_height + 3
        
        if self.get_y() + total_height > 275:
            self.add_page()
            
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 180, total_height, style='FD')
        self.set_xy(x + 2, y + 1.5)
        for line in lines:
            self.cell(0, line_height, line[:110], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y + total_height + 2)

    def callout(self, title, content, bg=(240, 247, 255), border=(191, 219, 254), title_color=(30, 58, 138)):
        self.set_fill_color(*bg)
        self.set_draw_color(*border)
        self.set_line_width(0.4)
        
        lines = len(content) // 110 + 1
        h = 12 + lines * 4.0
        if self.get_y() + h > 275:
            self.add_page()
            
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 180, h, style='FD')
        self.set_xy(x + 3, y + 2)
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(*title_color)
        self.cell(0, 4.2, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_xy(x + 3, y + 6.5)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(51, 65, 85)
        self.multi_cell(174, 3.8, content, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y + h + 2.2)

    def table(self, headers, rows, col_widths, align_cols=None):
        self.set_font('Helvetica', 'B', 7.5)
        self.set_fill_color(226, 232, 240)
        self.set_text_color(15, 23, 42)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.2)
        
        est_height = 5.5 + len(rows) * 5.0
        if self.get_y() + est_height > 275:
            self.add_page()
            
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 5.5, h, border=1, fill=True, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.ln(5.5)
        
        self.set_font('Helvetica', '', 7.3)
        fill = False
        for row in rows:
            fill = not fill
            self.set_fill_color(248, 250, 252 if fill else 255)
            self.set_text_color(51, 65, 85)
            for i, val in enumerate(row):
                align = align_cols[i] if align_cols else 'L'
                self.cell(col_widths[i], 4.8, str(val)[:50], border=1, fill=True, align=align,
                          new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.ln(4.8)
        self.ln(2.0)
