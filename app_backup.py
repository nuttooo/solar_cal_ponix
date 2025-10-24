#!/usr/bin/env python3
"""
Solar Analyzer Web Application
==============================

Web interface for solar and battery system analysis.
Users can upload CSV files and configure parameters through a web UI.
Results are generated as downloadable graphs and PDF reports.
"""

import os
import sys
import io
import base64
import glob
import shutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, redirect, url_for, flash, session
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Configure matplotlib for Thai font support
plt.rcParams["font.family"] = "Tahoma"
plt.rcParams["font.size"] = 10

# Import our solar analyzer
from solar_analyzer_pro import SolarAnalyzerPro

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'static/outputs'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files in development

# Session configuration to prevent timeout during slow data entry
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Extended session lifetime
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Add custom filter for datetime formatting
@app.template_filter('strftime')
def strftime_filter(timestamp, format_string):
    """Convert timestamp to formatted string"""
    if timestamp is None:
        return 'N/A'
    return datetime.fromtimestamp(timestamp).strftime(format_string)

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)


def cleanup_old_files(max_age_hours=24):
    """
    Clean up old files from upload and output directories
    Files older than max_age_hours will be deleted
    More conservative cleanup to avoid deleting files in active sessions
    """
    try:
        current_time = datetime.now()
        # Increased cleanup time to prevent deleting files during slow data entry
        cutoff_time = current_time - timedelta(hours=max_age_hours)
        
        # Get list of currently active session files to avoid deletion
        active_files = set()
        try:
            # This is a simplified approach - in production you might want to track active sessions more carefully
            upload_dir = app.config['UPLOAD_FOLDER']
            if os.path.exists(upload_dir):
                for filename in os.listdir(upload_dir):
                    file_path = os.path.join(upload_dir, filename)
                    if os.path.isfile(file_path):
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        # Only delete files older than 24 hours (more conservative)
                        if file_time < cutoff_time:
                            # Additional check: don't delete files modified in last 2 hours
                            if (current_time - file_time).total_seconds() > 7200:  # 2 hours
                                os.remove(file_path)
                                print(f"Removed old upload file: {filename}")
                            else:
                                active_files.add(filename)
        except Exception as e:
            print(f"Error during upload directory cleanup: {e}")
        
        # Clean up output directory with similar conservative approach
        output_dir = app.config['OUTPUT_FOLDER']
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    # Only delete files older than 24 hours and not modified in last 2 hours
                    if file_time < cutoff_time and (current_time - file_time).total_seconds() > 7200:
                        os.remove(file_path)
                        print(f"Removed old output file: {filename}")
        
        # Clean up temp text images if any exist (more aggressive cleanup for temp files)
        temp_pattern = os.path.join(output_dir, "temp_text_*.png")
        temp_files = glob.glob(temp_pattern)
        for temp_file in temp_files:
            file_time = datetime.fromtimestamp(os.path.getmtime(temp_file))
            if (current_time - file_time).total_seconds() > 3600:  # 1 hour for temp files
                os.remove(temp_file)
                print(f"Removed temp file: {os.path.basename(temp_file)}")
            
    except Exception as e:
        print(f"Error during file cleanup: {e}")


# Run cleanup on startup
cleanup_old_files()


def schedule_cleanup():
    """Schedule cleanup to run periodically"""
    while True:
        # Run cleanup every 6 hours
        time.sleep(6 * 60 * 60)
        cleanup_old_files()


# Start cleanup thread
cleanup_thread = threading.Thread(target=schedule_cleanup, daemon=True)
cleanup_thread.start()


class WebSolarAnalyzer:
    """Web-enabled version of the Solar Analyzer Pro"""
    
    def __init__(self):
        self.analyzer = SolarAnalyzerPro()
        self.analyzer.output_dir = app.config['OUTPUT_FOLDER']  # Update output directory
        self.uploaded_file = None
        
    def process_uploaded_file(self, file_path: str) -> bool:
        """Process the uploaded CSV file"""
        return self.analyzer.load_and_parse_data(file_path)
    
    def configure_parameters(self, solar_capacity: float, sun_hours: float, 
                            battery_threshold: float, battery_size: float) -> None:
        """Configure analysis parameters from web form"""
        self.analyzer.solar_capacity_mw = solar_capacity
        self.analyzer.sun_hours = sun_hours
        self.analyzer.battery_threshold_w = battery_threshold
        self.analyzer.battery_size_kwh = battery_size
    
    def run_analysis(self) -> Dict:
        """Run the complete analysis and return results"""
        if self.analyzer.df is None or self.analyzer.df.empty:
            return {"error": "No data loaded"}
        
        self.analyzer.create_solar_generation()
        self.analyzer.calculate_daily_battery_requirements()
        
        # Generate graphs
        self.analyzer.create_daily_graphs_with_battery()
        self.analyzer.create_weekly_summary()
        
        # Return summary data
        if self.analyzer.battery_analysis:
            # Convert numpy arrays to lists for JSON serialization
            daily_data = []
            for day in self.analyzer.battery_analysis:
                day_copy = day.copy()
                # Convert numpy arrays to lists
                for key, value in day_copy.items():
                    if hasattr(value, 'tolist'):
                        day_copy[key] = value.tolist()
                daily_data.append(day_copy)
            
            summary = {
                "total_days": len(self.analyzer.battery_analysis),
                "average_daily_consumption": sum(day["consumption_area"] for day in self.analyzer.battery_analysis) / len(self.analyzer.battery_analysis),
                "average_daily_solar": sum(day["solar_area"] for day in self.analyzer.battery_analysis) / len(self.analyzer.battery_analysis),
                "total_excess_energy": sum(day["total_excess_energy"] for day in self.analyzer.battery_analysis),
                "total_deficit_energy": sum(day["total_deficit_energy"] for day in self.analyzer.battery_analysis),
                "average_battery_size": sum(day["optimal_battery_size"] for day in self.analyzer.battery_analysis) / len(self.analyzer.battery_analysis),
                "total_battery_discharge": sum(day["battery_discharge_16_22_area"] for day in self.analyzer.battery_analysis),
                "daily_data": daily_data
            }
            return summary
        return {"error": "Analysis failed"}


@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and validation"""
    if 'file' not in request.files:
        flash('ไม่พบไฟล์ที่อัปโหลด', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('กรุณาเลือกไฟล์', 'error')
        return redirect(url_for('index'))
    
    if file and file.filename.endswith('.csv'):
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"energy_data_{timestamp}.csv"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Make session permanent to prevent timeout during slow data entry
        session.permanent = True
        
        # Store file path in session with additional metadata
        session['uploaded_file'] = file_path
        session['filename'] = file.filename
        session['upload_time'] = datetime.now().isoformat()
        session['file_size'] = os.path.getsize(file_path)
        
        flash('อัปโหลดไฟล์สำเร็จ!', 'success')
        return redirect(url_for('configure'))
    else:
        flash('กรุณาอัปโหลดไฟล์ CSV เท่านั้น', 'error')
        return redirect(url_for('index'))


@app.route('/configure')
def configure():
    """Configuration page for analysis parameters"""
    if 'uploaded_file' not in session:
        flash('กรุณาอัปโหลดไฟล์ก่อน', 'error')
        return redirect(url_for('index'))
    
    # Validate that the uploaded file still exists
    file_path = session.get('uploaded_file')
    if not os.path.exists(file_path):
        flash('ไฟล์ที่อัปโหลดหมดอายุ กรุณาอัปโหลดไฟล์ใหม่', 'error')
        # Clear invalid session data
        session.pop('uploaded_file', None)
        session.pop('filename', None)
        session.pop('upload_time', None)
        session.pop('file_size', None)
        return redirect(url_for('index'))
    
    return render_template('configure.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Run analysis with provided parameters"""
    if 'uploaded_file' not in session:
        flash('กรุณาอัปโหลดไฟล์ก่อน', 'error')
        return redirect(url_for('index'))
    
    # Validate that the uploaded file still exists before processing
    file_path = session.get('uploaded_file')
    if not os.path.exists(file_path):
        flash('ไฟล์ที่อัปโหลดหมดอายุ กรุณาอัปโหลดไฟล์ใหม่', 'error')
        # Clear invalid session data
        session.pop('uploaded_file', None)
        session.pop('filename', None)
        session.pop('upload_time', None)
        session.pop('file_size', None)
        return redirect(url_for('index'))
    
    # Get form parameters
    try:
        solar_capacity = float(request.form.get('solar_capacity', 3.0))
        sun_hours = float(request.form.get('sun_hours', 4.0))
        battery_threshold = float(request.form.get('battery_threshold', 1500.0))
        battery_size = float(request.form.get('battery_size', 0.0))
        
        # Validate parameters
        if solar_capacity <= 0 or sun_hours <= 0 or battery_threshold < 0 or battery_size < 0:
            raise ValueError("พารามิเตอร์ต้องมีค่ามากกว่าหรือเท่ากับ 0")
        
        # Initialize analyzer
        web_analyzer = WebSolarAnalyzer()
        
        # Load and process file
        file_loaded = web_analyzer.process_uploaded_file(session['uploaded_file'])
        if not file_loaded:
            flash('ไม่สามารถโหลดไฟล์ได้ กรุณาตรวจสอบรูปแบบข้อมูล', 'error')
            return redirect(url_for('configure'))
        
        # Configure parameters
        web_analyzer.configure_parameters(solar_capacity, sun_hours, battery_threshold, battery_size)
        
        # Run analysis
        try:
            results = web_analyzer.run_analysis()
            
            if 'error' in results:
                flash(f'การวิเคราะห์ล้มเหลว: {results["error"]}', 'error')
                return redirect(url_for('configure'))
        except Exception as e:
            flash(f'ข้อผิดพลาดในการวิเคราะห์: {str(e)}', 'error')
            return redirect(url_for('configure'))
        
        # Store only summary data in session (not daily_data which is too large)
        session_results = results.copy()
        if 'daily_data' in session_results:
            # Remove daily_data from session to avoid cookie size limit
            session_results.pop('daily_data', None)
        
        session['analysis_results'] = session_results
        session['analysis_params'] = {
            'solar_capacity': solar_capacity,
            'sun_hours': sun_hours,
            'battery_threshold': battery_threshold,
            'battery_size': battery_size
        }
        
        return redirect(url_for('results'))
        
    except (ValueError, TypeError) as e:
        flash(f'ข้อมูลพารามิเตอร์ไม่ถูกต้อง: {str(e)}', 'error')
        return redirect(url_for('configure'))


@app.route('/results')
def results():
    """Display analysis results"""
    if 'analysis_results' not in session:
        flash('ไม่มีผลการวิเคราะห์ กรุณาทำการวิเคราะห์ก่อน', 'error')
        return redirect(url_for('configure'))
    
    results = session['analysis_results']
    params = session['analysis_params']
    
    # Re-run analysis to get daily data (since it's too large for session)
    if 'uploaded_file' in session:
        try:
            web_analyzer = WebSolarAnalyzer()
            
            # Load and process file
            file_loaded = web_analyzer.process_uploaded_file(session['uploaded_file'])
            if file_loaded:
                # Configure parameters
                web_analyzer.configure_parameters(
                    params['solar_capacity'],
                    params['sun_hours'],
                    params['battery_threshold'],
                    params['battery_size']
                )
                
                # Run analysis to get daily data
                web_analyzer.analyzer.create_solar_generation()
                web_analyzer.analyzer.calculate_daily_battery_requirements()
                
                # Add daily data to results
                if web_analyzer.analyzer.battery_analysis:
                    results['daily_data'] = web_analyzer.analyzer.battery_analysis
        except Exception as e:
            print(f"Error re-running analysis for daily data: {e}")
    
    # Get list of generated images
    output_files = []
    output_dir = app.config['OUTPUT_FOLDER']
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.png'):
                file_path = os.path.join(output_dir, filename)
                # Get file modification time
                mtime = os.path.getmtime(file_path)
                output_files.append({
                    'filename': filename,
                    'path': file_path,
                    'url': url_for('static', filename=f'outputs/{filename}'),
                    'mtime': mtime
                })
    
    # Sort by modification time (newest first)
    output_files.sort(key=lambda x: x['mtime'], reverse=True)
    
    return render_template('results.html', results=results, params=params, images=output_files)


@app.route('/download/<filename>')
def download_file(filename):
    """Download generated files"""
    output_dir = app.config['OUTPUT_FOLDER']
    file_path = os.path.join(output_dir, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('ไม่พบไฟล์ที่ร้องขอ', 'error')
        return redirect(url_for('results'))


@app.route('/generate_pdf')
def generate_pdf():
    """Generate PDF report"""
    if 'analysis_results' not in session:
        flash('ไม่มีผลการวิเคราะห์ กรุณาทำการวิเคราะห์ก่อน', 'error')
        return redirect(url_for('results'))
    
    results = session['analysis_results']
    params = session['analysis_params']
    
    # Create PDF
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"solar_analysis_report_{timestamp}.pdf"
    pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
    
    # Import required modules for PDF generation
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    from reportlab.platypus import Image as ReportLabImage
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    
    # Create custom document with better margins
    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                           leftMargin=0.75*inch, rightMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    
    # Create custom styles for professional report
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderColor=colors.darkblue,
        borderPadding=5
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        fontName='Helvetica',
        leading=14
    )
    
    story = []
    
    # Create header with logo and title
    header_table_data = []
    
    # Add logo to header if available
    logo_path = os.path.join('public', 'logo-ponix.png')
    if os.path.exists(logo_path):
        try:
            logo = ReportLabImage(logo_path, width=1.5*inch, height=0.75*inch)
            header_table_data.append([logo, Paragraph("Solar System Analysis Report", title_style)])
        except:
            header_table_data.append(["", Paragraph("Solar System Analysis Report", title_style)])
    else:
        header_table_data.append(["", Paragraph("Solar System Analysis Report", title_style)])
    
    # Add date and report ID to header
    report_date = datetime.now().strftime("%B %d, %Y")
    report_id = f"SOL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    header_table_data.append([Paragraph(f"Date: {report_date}", normal_style),
                            Paragraph(f"Report ID: {report_id}", normal_style)])
    
    header_table = Table(header_table_data, colWidths=[2*inch, 4*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # Add horizontal line
    story.append(Spacer(1, 6))
    story.append(Table([['']], colWidths=[7.5*inch]).setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue)
    ])))
    story.append(Spacer(1, 20))
    
    # Executive Summary Section
    story.append(Paragraph("Executive Summary", heading_style))
    
    # Create summary data as table with professional styling
    summary_data = [
        ['Metric', 'Value'],
        ['Analysis Period', f"{results['total_days']} days"],
        ['Average Daily Load', f"{results['average_daily_consumption']:.1f} kWh"],
        ['Average Daily Solar Generation', f"{results['average_daily_solar']:.1f} kWh"],
        ['Total Excess Energy', f"{results['total_excess_energy']:.1f} kWh"],
        ['Total Deficit Energy', f"{results['total_deficit_energy']:.1f} kWh"],
        ['Recommended Battery Size', f"{results['average_battery_size']:.1f} kWh"],
        ['Evening Battery Usage', f"{results['total_battery_discharge']:.1f} kWh"]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # System Parameters Section
    story.append(Paragraph("System Parameters", heading_style))
    battery_size_text = 'Auto Calculate' if params['battery_size'] == 0 else f"{params['battery_size']:.1f} kWh"
    
    # Create parameter data as table
    param_data = [
        ['Parameter', 'Value'],
        ['Solar Capacity', f"{params['solar_capacity']:.1f} MWp"],
        ['Sun Hours', f"{params['sun_hours']:.1f} hrs/day"],
        ['Battery Threshold', f"{params['battery_threshold']:.0f} W"],
        ['Battery Size', battery_size_text]
    ]
    
    param_table = Table(param_data, colWidths=[3*inch, 2*inch])
    param_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    
    story.append(param_table)
    story.append(Spacer(1, 20))
    
    # Add Analysis Graphs Section
    story.append(Paragraph("Analysis Graphs", heading_style))
    story.append(Spacer(1, 12))
    
    # Add horizontal line before graphs
    story.append(Table([['']], colWidths=[7.5*inch]).setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue)
    ])))
    story.append(Spacer(1, 12))
    
    output_dir = app.config['OUTPUT_FOLDER']
    if os.path.exists(output_dir):
        # Add weekly summary first with caption
        weekly_files = [f for f in os.listdir(output_dir) if 'weekly_summary' in f and f.endswith('.png')]
        if weekly_files:
            story.append(Paragraph("Weekly Summary", subheading_style))
            for filename in sorted(weekly_files):
                file_path = os.path.join(output_dir, filename)
                try:
                    # Add image to PDF with proper sizing and centering
                    img = ReportLabImage(file_path, width=6.5*inch, height=4*inch)
                    img.hAlign = 'CENTER'
                    story.append(img)
                    story.append(Spacer(1, 6))
                    
                    # Add caption
                    caption_text = filename.replace('_', ' ').replace('.png', '').title()
                    story.append(Paragraph(caption_text, normal_style))
                    story.append(Spacer(1, 12))
                except:
                    # Skip image if it can't be processed
                    pass
        
        # Add daily analysis graphs with better organization
        daily_files = [f for f in os.listdir(output_dir) if 'daily_analysis' in f and f.endswith('.png')]
        if daily_files:
            story.append(PageBreak())
            story.append(Paragraph("Daily Analysis Details", subheading_style))
            story.append(Spacer(1, 12))
            
            # Group daily graphs (2 per page for better layout)
            for i in range(0, len(daily_files), 2):
                if i > 0:  # Add page break for subsequent pages
                    story.append(PageBreak())
                
                # Add 1 or 2 graphs per page
                for j in range(i, min(i + 2, len(daily_files))):
                    filename = daily_files[j]
                    file_path = os.path.join(output_dir, filename)
                    try:
                        # Extract date from filename for better caption
                        date_part = filename.replace('solar_daily_analysis_', '').replace('.png', '')
                        caption_text = f"Daily Analysis - {date_part}"
                        
                        # Add subheading for each graph
                        story.append(Paragraph(caption_text, normal_style))
                        story.append(Spacer(1, 6))
                        
                        # Add image with proper sizing
                        img = ReportLabImage(file_path, width=6*inch, height=3.5*inch)
                        img.hAlign = 'CENTER'
                        story.append(img)
                        
                        if j < min(i + 2, len(daily_files)) - 1:  # Add spacing between graphs on same page
                            story.append(Spacer(1, 20))
                    except:
                        # Skip image if it can't be processed
                        pass
    
    # Build PDF
    doc.build(story)
    
    # Return PDF for download
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)


@app.route('/static/images/<filename>')
def serve_static_images(filename):
    """Serve static image files with proper headers"""
    return send_from_directory('static/images', filename)


@app.route('/static/outputs/<filename>')
def serve_static_outputs(filename):
    """Serve static output files with proper headers"""
    return send_from_directory('static/outputs', filename)


@app.route('/keep-alive', methods=['POST'])
def keep_alive():
    """Keep session alive during slow data entry or analysis"""
    # Just return success to keep session active
    return jsonify({'status': 'alive', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)