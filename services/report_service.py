from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from datetime import datetime

class ReportService:
    def generate_pdf(self, filename, title, headers, data_rows, summary_text=None, col_alignments=None):
        """
        Generates a professional PDF report with a table.
        headers: List of strings ['Column 1', 'Column 2', ...]
        data_rows: List of Lists [['val1', 'val2'], ...] matching headers.
        col_alignments: List of alignment strings e.g. ['LEFT', 'CENTER', 'RIGHT'] matching headers count.
        """
        try:
            doc = SimpleDocTemplate(
                filename, 
                pagesize=landscape(A4),
                rightMargin=30, leftMargin=30, 
                topMargin=30, bottomMargin=30
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # --- Title ---
            title_style = styles['Title']
            title_style.textColor = colors.HexColor("#2C3E50")
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # --- Metadata ---
            meta_style = styles['Normal']
            date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            elements.append(Paragraph(f"Generado el: {date_str}", meta_style))
            if summary_text:
                elements.append(Paragraph(summary_text, meta_style))
            elements.append(Spacer(1, 1*cm))
            
            # --- Table Data ---
            # Prepend headers
            table_data = [headers] + data_rows
            
            # Define Column Widths (proportional if possible, but SimpleDocTemplate needs fixed usually or auto)
            # Let's try to calculate based on A4 landscape width ~29.7cm - margins
            available_width = landscape(A4)[0] - 60 #~800 pts
            
            # Simple heuristic distribution
            col_count = len(headers)
            if col_count > 0:
                col_width = available_width / col_count
            else:
                col_width = 100
                
            # Create Table
            t = Table(table_data, colWidths=[col_width]*col_count, repeatRows=1)
            
            # --- Table Styling ---
            base_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495E")), # Header BG
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), # Header Text
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'), # Default Global Left
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]
            
            # Apply Custom Alignments per Column
            if col_alignments and len(col_alignments) == col_count:
                for idx, align in enumerate(col_alignments):
                    # Apply to ALL rows in that column
                    base_style.append(('ALIGN', (idx, 0), (idx, -1), align.upper()))
            
            style = TableStyle(base_style)
            t.setStyle(style)
            
            # Row coloring (Zebra)
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    bg_color = colors.HexColor("#F2F3F4")
                    t.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), bg_color)]))
            
            elements.append(t)
            
            # Build
            doc.build(elements)
            return True, f"PDF generado correctamente en: {filename}"
            
        except Exception as e:
            return False, f"Error al generar PDF: {str(e)}"
