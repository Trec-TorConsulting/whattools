"""PDF export generator with embedded charts using ReportLab."""

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

from services.analytics.exporters.charts import (
    generate_trend_chart,
    generate_category_chart,
    generate_top_items_chart,
)


class PdfExporter:
    """Generates professional PDF reports with embedded charts."""

    def export(self, data: dict[str, Any], report_type: str, period: str, file_path: str) -> None:
        """Export analytics data as a PDF file."""
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=20,
            spaceAfter=6,
            textColor=colors.HexColor("#1a237e"),
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#283593"),
        )
        normal_style = styles["Normal"]

        elements = []

        # Header
        now = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
        elements.append(Paragraph("WhatTools Analytics Report", title_style))
        elements.append(Paragraph(f"Period: {period} &bull; Generated: {now}", normal_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Summary section
        if "summary" in data:
            elements.extend(self._build_summary_section(data["summary"], section_style, normal_style))

        # Categories section
        if "categories" in data:
            elements.extend(self._build_categories_section(data["categories"], section_style))

        # Shows section
        if "shows" in data:
            elements.extend(self._build_shows_section(data["shows"], section_style))

        # Trends section (with chart)
        if "trends" in data:
            elements.extend(self._build_trends_section(data["trends"], section_style))

        # Top items section (with chart)
        if "top_items" in data:
            elements.extend(self._build_top_items_section(data["top_items"], section_style))

        doc.build(elements)

    def _build_summary_section(
        self, summary: dict[str, Any], section_style: ParagraphStyle, normal_style: ParagraphStyle
    ) -> list:
        """Build the summary stats section."""
        elements = []
        elements.append(Paragraph("Revenue Summary", section_style))

        table_data = [
            ["Metric", "Value"],
            ["Orders", str(summary.get("order_count", 0))],
            ["Total Revenue", f"${summary.get('total_revenue', 0):,.2f}"],
            ["Cost of Goods", f"${summary.get('total_cogs', 0):,.2f}"],
            ["Platform Fees", f"${summary.get('total_fees', 0):,.2f}"],
            ["Shipping Costs", f"${summary.get('total_shipping', 0):,.2f}"],
            ["Gross Profit", f"${summary.get('gross_profit', 0):,.2f}"],
            ["Net Profit", f"${summary.get('net_profit', 0):,.2f}"],
            ["Margin %", f"{summary.get('margin_percent', 0):.1f}%"],
            ["Avg Order Value", f"${summary.get('average_order_value', 0):,.2f}"],
            ["Sell-Through Rate", f"{summary.get('sell_through_rate', 0):.1f}%"],
        ]

        table = Table(table_data, colWidths=[3 * inch, 3 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#283593")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        return elements

    def _build_categories_section(self, categories: list[dict[str, Any]], section_style: ParagraphStyle) -> list:
        """Build the category performance section with chart."""
        elements = []
        elements.append(Paragraph("Category Performance", section_style))

        if categories:
            # Chart
            chart_bytes = generate_category_chart(categories)
            chart_img = Image(io.BytesIO(chart_bytes), width=6.5 * inch, height=2.6 * inch)
            elements.append(chart_img)
            elements.append(Spacer(1, 0.15 * inch))

            # Table
            table_data = [["Category", "Revenue", "Profit", "Items Sold", "Sell-Through"]]
            for cat in categories[:15]:
                table_data.append([
                    cat["category_name"],
                    f"${cat['revenue']:,.2f}",
                    f"${cat['profit']:,.2f}",
                    str(cat["item_count"]),
                    f"{cat['sell_through_rate']:.1f}%",
                ])

            table = Table(table_data, colWidths=[2.2 * inch, 1.3 * inch, 1.3 * inch, 1 * inch, 1.2 * inch])
            table.setStyle(self._standard_table_style())
            elements.append(table)

        elements.append(Spacer(1, 0.3 * inch))
        return elements

    def _build_shows_section(self, shows: list[dict[str, Any]], section_style: ParagraphStyle) -> list:
        """Build the show performance section."""
        elements = []
        elements.append(Paragraph("Show Performance", section_style))

        if shows:
            table_data = [["Show", "Date", "Orders", "Revenue", "Profit", "Duration"]]
            for show in shows[:20]:
                date = show.get("date", "")[:10]
                dur = show.get("duration_minutes")
                dur_str = f"{dur:.0f} min" if dur else "—"
                table_data.append([
                    show["show_title"][:30],
                    date,
                    str(show["order_count"]),
                    f"${show['revenue']:,.2f}",
                    f"${show['profit']:,.2f}",
                    dur_str,
                ])

            table = Table(table_data, colWidths=[1.8 * inch, 1 * inch, 0.7 * inch, 1.2 * inch, 1.2 * inch, 1.1 * inch])
            table.setStyle(self._standard_table_style())
            elements.append(table)

        elements.append(Spacer(1, 0.3 * inch))
        return elements

    def _build_trends_section(self, trends: list[dict[str, Any]], section_style: ParagraphStyle) -> list:
        """Build the trends section with chart."""
        elements = []
        elements.append(Paragraph("Revenue & Profit Trends", section_style))

        chart_bytes = generate_trend_chart(trends)
        chart_img = Image(io.BytesIO(chart_bytes), width=6.5 * inch, height=2.6 * inch)
        elements.append(chart_img)
        elements.append(Spacer(1, 0.3 * inch))
        return elements

    def _build_top_items_section(self, top_items: list[dict[str, Any]], section_style: ParagraphStyle) -> list:
        """Build the top items section with chart."""
        elements = []
        elements.append(Paragraph("Top Performing Items", section_style))

        if top_items:
            # Chart
            chart_bytes = generate_top_items_chart(top_items)
            chart_img = Image(io.BytesIO(chart_bytes), width=6.5 * inch, height=2.6 * inch)
            elements.append(chart_img)
            elements.append(Spacer(1, 0.15 * inch))

            # Table
            table_data = [["Item", "Category", "Qty Sold", "Revenue", "Profit", "Margin"]]
            for item in top_items[:15]:
                table_data.append([
                    item["item_name"][:25],
                    (item.get("category") or "—")[:15],
                    str(item["quantity_sold"]),
                    f"${item['revenue']:,.2f}",
                    f"${item['profit']:,.2f}",
                    f"{item['margin_percent']:.1f}%",
                ])

            table = Table(table_data, colWidths=[1.6 * inch, 1 * inch, 0.7 * inch, 1.2 * inch, 1.2 * inch, 0.8 * inch])
            table.setStyle(self._standard_table_style())
            elements.append(table)

        elements.append(Spacer(1, 0.3 * inch))
        return elements

    @staticmethod
    def _standard_table_style() -> TableStyle:
        """Return reusable table styling."""
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#283593")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
