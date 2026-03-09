"""
ProtocolScout Flask Web Application
Main application file
"""
import os
import json
import base64
import boto3
import tempfile
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from botocore.exceptions import ClientError
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')
DOCUMENTS_BUCKET = os.environ.get('DOCUMENTS_BUCKET', 'protocolscout-documents-prod-2026')

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

# DynamoDB tables
audit_table = dynamodb.Table('protocol_audit')
results_table = dynamodb.Table('compliance_results')
users_table = dynamodb.Table('users')

# User Model
class User(UserMixin):
    def __init__(self, email, name, institution, user_id=None):
        self.email = email
        self.name = name
        self.institution = institution
        self.id = user_id or email  # Use email as unique identifier
    
    @staticmethod
    def get(email):
        """Get user from DynamoDB"""
        try:
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                item = response['Item']
                return User(
                    email=item['email'],
                    name=item['name'],
                    institution=item['institution'],
                    user_id=item['email']
                )
            return None
        except Exception as e:
            print(f"Error fetching user: {str(e)}")
            return None
    
    @staticmethod
    def create(email, name, institution, password):
        """Create new user in DynamoDB"""
        try:
            # Hash password
            password_hash = generate_password_hash(password)
            
            # Store in DynamoDB
            users_table.put_item(
                Item={
                    'email': email,
                    'name': name,
                    'institution': institution,
                    'password_hash': password_hash,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            
            return User(email=email, name=name, institution=institution, user_id=email)
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return None
    
    @staticmethod
    def verify_password(email, password):
        """Verify user password"""
        try:
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                stored_hash = response['Item'].get('password_hash')
                return check_password_hash(stored_hash, password)
            return False
        except Exception as e:
            print(f"Error verifying password: {str(e)}")
            return False

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.get(user_id)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return render_template('login.html')
        
        # Verify credentials
        if User.verify_password(email, password):
            user = User.get(email)
            if user:
                login_user(user)
                flash(f'Welcome back, {user.name}!', 'success')
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        
        flash('Invalid email or password.', 'danger')
        return render_template('login.html')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        institution = request.form.get('institution')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([email, name, institution, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        if User.get(email):
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html')
        
        # Create user
        user = User.create(email, name, institution, password)
        if user:
            login_user(user)
            flash(f'Welcome to ProtocolScout, {name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload protocol page"""
    if request.method == 'GET':
        return render_template('upload.html')
    
    try:
        # Check if file is present
        if 'protocol_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['protocol_file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Read file content
        file_content = file.read()
        
        # Get metadata from form and current user
        user_id = current_user.email
        institution = current_user.institution
        protocol_title = request.form.get('protocol_title', file.filename)
        
        # Encode file to base64
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Invoke upload handler Lambda
        response = lambda_client.invoke(
            FunctionName='protocolscout-upload-handler',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'body': json.dumps({
                    'file': file_base64,
                    'metadata': {
                        'user_id': user_id,
                        'institution': institution,
                        'protocol_title': protocol_title,
                        'filename': secure_filename(file.filename)
                    }
                })
            })
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response_payload['statusCode'] == 200:
            result = json.loads(response_payload['body'])
            
            # Store in session
            session['last_protocol_id'] = result['protocol_id']
            
            return jsonify({
                'success': True,
                'protocol_id': result['protocol_id'],
                'message': result['message'],
                'estimated_completion': result.get('estimated_completion', '5 minutes')
            })
        else:
            error_body = json.loads(response_payload['body'])
            return jsonify({'error': error_body.get('message', 'Upload failed')}), 500
    
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<protocol_id>')
def check_status(protocol_id):
    """Check protocol processing status"""
    try:
        # Invoke status checker Lambda
        response = lambda_client.invoke(
            FunctionName='protocolscout-status-checker',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'protocol_id': protocol_id
            })
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response_payload['statusCode'] == 200:
            result = json.loads(response_payload['body'])
            return jsonify(result)
        else:
            return jsonify({'error': 'Status check failed'}), 500
    
    except Exception as e:
        print(f"Status check error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/results/<protocol_id>')
@login_required
def view_results(protocol_id):
    """View compliance results page"""
    return render_template('results.html', protocol_id=protocol_id)

@app.route('/api/results/<protocol_id>')
def get_results(protocol_id):
    """Get compliance results via API"""
    print(f"\n{'='*70}")
    print(f"API REQUEST: /api/results/{protocol_id}")
    print(f"{'='*70}")
    
    try:
        # First, try to get the JSON report from S3 (most reliable)
        try:
            report_key = f"reports/{protocol_id}/compliance_report.json"
            print(f"[1] Attempting to fetch from S3...")
            print(f"    Bucket: {DOCUMENTS_BUCKET}")
            print(f"    Key: {report_key}")
            
            response = s3_client.get_object(
                Bucket=DOCUMENTS_BUCKET,
                Key=report_key
            )
            
            report_data = json.loads(response['Body'].read())
            print(f"[2] ✅ Successfully loaded report from S3")
            print(f"[3] Report keys: {list(report_data.keys())}")
            
            # Parse the report data - handle the actual structure
            result_data = {
                'protocol_id': protocol_id,
                'violations': [],
                'compliance_score': 0,
                'total_rules_checked': 0,
                'critical_violations': 0,
                'high_violations': 0,
                'medium_violations': 0,
                'low_violations': 0
            }
            
            # Extract compliance score from full_assessment
            if 'full_assessment' in report_data:
                assessment = report_data['full_assessment']
                if 'compliance_score' in assessment:
                    result_data['compliance_score'] = int(assessment['compliance_score'])
                if 'total_rules_evaluated' in assessment:
                    result_data['total_rules_checked'] = int(assessment['total_rules_evaluated'])
            
            # Also check report_metadata
            if 'report_metadata' in report_data:
                metadata = report_data['report_metadata']
                if 'compliance_score' in metadata:
                    result_data['compliance_score'] = int(metadata['compliance_score'])
            
            print(f"[4] Compliance Score: {result_data['compliance_score']}")
            print(f"[5] Total Rules: {result_data['total_rules_checked']}")
            
            # Parse violations from detailed_gaps OR full_assessment.gaps
            gaps = []
            if 'detailed_gaps' in report_data:
                gaps = report_data['detailed_gaps']
            elif 'full_assessment' in report_data and 'gaps' in report_data['full_assessment']:
                gaps = report_data['full_assessment']['gaps']
            
            print(f"[6] Found {len(gaps)} gaps in report")
            
            # If no total_rules_checked, estimate from gaps
            if result_data['total_rules_checked'] == 0 and len(gaps) > 0:
                result_data['total_rules_checked'] = 50  # Default estimate
            
            for gap in gaps:
                # Extract severity
                severity = str(gap.get('severity', 'medium')).lower()
                
                # Extract other fields - handle both formats
                rule_id = gap.get('rule_id', 'Unknown')
                category = gap.get('category', 'general')
                rule_text = gap.get('rule_text', gap.get('description', ''))
                gap_description = gap.get('gap_description', gap.get('description', ''))
                recommendation = gap.get('recommendation', '')
                regulatory_citation = gap.get('regulatory_citation', '')
                
                # Combine rule text with citation if available
                if regulatory_citation and not rule_text:
                    rule_text = f"Regulatory requirement: {regulatory_citation}"
                
                result_data['violations'].append({
                    'rule_id': rule_id,
                    'severity': severity,
                    'category': category,
                    'rule_text': rule_text,
                    'violation_details': gap_description,
                    'recommendation': recommendation
                })
                
                # Count by severity
                if severity == 'critical':
                    result_data['critical_violations'] += 1
                elif severity == 'high':
                    result_data['high_violations'] += 1
                elif severity == 'medium':
                    result_data['medium_violations'] += 1
                elif severity == 'low':
                    result_data['low_violations'] += 1
            
            print(f"[7] Violations by severity:")
            print(f"    Critical: {result_data['critical_violations']}")
            print(f"    High: {result_data['high_violations']}")
            print(f"    Medium: {result_data['medium_violations']}")
            print(f"    Low: {result_data['low_violations']}")
            print(f"[8] ✅ Returning data to frontend")
            print(f"{'='*70}\n")
            
            return jsonify(result_data)
            
        except s3_client.exceptions.NoSuchKey:
            print(f"[ERROR] ❌ Report not found in S3: {report_key}")
            # Fall back to DynamoDB query
            pass
        except Exception as e:
            print(f"[ERROR] ❌ S3 fetch failed: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fall back to DynamoDB query
            pass
        
        # Fallback: Query compliance results from DynamoDB
        print(f"Trying DynamoDB query for protocol: {protocol_id}")
        
        # Try direct scan with filter (more reliable than GSI)
        response = results_table.scan(
            FilterExpression='protocol_id = :pid',
            ExpressionAttributeValues={':pid': protocol_id}
        )
        
        items = response.get('Items', [])
        
        if not items:
            return jsonify({
                'error': 'No results found',
                'message': 'The compliance analysis is still in progress. Please wait a few moments and refresh.',
                'protocol_id': protocol_id
            }), 404
        
        # Organize results from DynamoDB
        result_data = {
            'protocol_id': protocol_id,
            'violations': [],
            'compliance_score': 0,
            'total_rules_checked': 0,
            'critical_violations': 0,
            'high_violations': 0,
            'medium_violations': 0,
            'low_violations': 0
        }
        
        for item in items:
            if item.get('violation_type'):
                result_data['violations'].append({
                    'rule_id': item.get('rule_id'),
                    'severity': item.get('severity'),
                    'category': item.get('category'),
                    'rule_text': item.get('rule_text'),
                    'violation_details': item.get('violation_details'),
                    'recommendation': item.get('recommendation')
                })
                
                # Count by severity
                severity = item.get('severity', 'low')
                result_data[f'{severity}_violations'] += 1
            
            # Get overall score
            if 'compliance_score' in item:
                result_data['compliance_score'] = item['compliance_score']
            if 'total_rules_checked' in item:
                result_data['total_rules_checked'] = item['total_rules_checked']
        
        return jsonify(result_data)
    
    except Exception as e:
        print(f"Results fetch error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    except Exception as e:
        print(f"Results fetch error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<protocol_id>/<format>')
def download_report(protocol_id, format):
    """Download compliance report"""
    try:
        # For PDF, generate it from JSON data
        if format == 'pdf':
            return generate_pdf_report(protocol_id)
        
        # For JSON and TXT, download from S3
        report_key = f"reports/{protocol_id}/compliance_report.{format}"
        
        print(f"Downloading report: s3://{DOCUMENTS_BUCKET}/{report_key}")
        
        # Download from S3
        response = s3_client.get_object(
            Bucket=DOCUMENTS_BUCKET,
            Key=report_key
        )
        
        # Use Windows-compatible temp directory
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"{protocol_id}_report.{format}")
        
        with open(temp_file, 'wb') as f:
            f.write(response['Body'].read())
        
        print(f"Report downloaded successfully to: {temp_file}")
        
        return send_file(
            temp_file,
            as_attachment=True,
            download_name=f"compliance_report_{protocol_id}.{format}"
        )
    
    except s3_client.exceptions.NoSuchKey:
        print(f"Report not found: {report_key}")
        return jsonify({
            'error': 'Report not ready yet',
            'message': 'The compliance report is still being generated. Please try again in a few moments.',
            'protocol_id': protocol_id,
            'expected_path': f"reports/{protocol_id}/compliance_report.{format}"
        }), 404
    
    except Exception as e:
        print(f"Download error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Download failed',
            'message': str(e)
        }), 500

def generate_pdf_report(protocol_id):
    """Generate PDF report from JSON data"""
    try:
        # Fetch JSON report from S3
        report_key = f"reports/{protocol_id}/compliance_report.json"
        response = s3_client.get_object(
            Bucket=DOCUMENTS_BUCKET,
            Key=report_key
        )
        
        report_data = json.loads(response['Body'].read())
        
        # Create PDF in temp directory
        temp_dir = tempfile.gettempdir()
        pdf_file = os.path.join(temp_dir, f"{protocol_id}_report.pdf")
        
        # Create PDF document
        doc = SimpleDocTemplate(pdf_file, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        # Container for PDF elements
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=6
        )
        
        normal_style = styles['Normal']
        
        # Title
        story.append(Paragraph("ProtocolScout Compliance Report", title_style))
        story.append(Spacer(1, 12))
        
        # Metadata
        metadata = report_data.get('report_metadata', {})
        protocol_id_text = metadata.get('protocol_id', protocol_id)
        generated_at = metadata.get('generated_at', 'N/A')
        
        metadata_data = [
            ['Protocol ID:', protocol_id_text],
            ['Generated:', generated_at],
            ['System:', 'ProtocolScout AI (AWS Bedrock Claude 3.5 Sonnet)']
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 20))
        
        # Compliance Score
        full_assessment = report_data.get('full_assessment', {})
        compliance_score = full_assessment.get('compliance_score', 0)
        status = full_assessment.get('status', 'UNKNOWN')
        
        story.append(Paragraph("Compliance Score", heading_style))
        
        score_data = [
            ['Score:', f"{compliance_score}/100"],
            ['Status:', status]
        ]
        
        score_table = Table(score_data, colWidths=[2*inch, 4*inch])
        score_color = colors.HexColor('#27ae60') if compliance_score >= 80 else \
                      colors.HexColor('#f39c12') if compliance_score >= 60 else \
                      colors.HexColor('#e74c3c')
        
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (1, 0), (1, 0), score_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
        ]))
        
        story.append(score_table)
        story.append(Spacer(1, 20))
        
        # Executive Summary
        executive_summary = report_data.get('executive_summary', {})
        summary_text = executive_summary.get('summary', 'No summary available.')
        
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 20))
        
        # Gap Breakdown
        gap_breakdown = executive_summary.get('gap_breakdown', {})
        if gap_breakdown:
            story.append(Paragraph("Gap Breakdown", heading_style))
            
            breakdown_data = [['Severity', 'Count']]
            for severity, count in gap_breakdown.items():
                breakdown_data.append([severity.capitalize(), str(count)])
            
            breakdown_table = Table(breakdown_data, colWidths=[3*inch, 3*inch])
            breakdown_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
            ]))
            
            story.append(breakdown_table)
            story.append(Spacer(1, 20))
        
        # Detailed Gaps
        gaps = report_data.get('detailed_gaps', [])
        if gaps:
            story.append(Paragraph("Detailed Compliance Gaps", heading_style))
            story.append(Spacer(1, 12))
            
            # Group by severity
            critical_gaps = [g for g in gaps if g.get('severity', '').lower() == 'critical']
            high_gaps = [g for g in gaps if g.get('severity', '').lower() == 'high']
            medium_gaps = [g for g in gaps if g.get('severity', '').lower() == 'medium']
            low_gaps = [g for g in gaps if g.get('severity', '').lower() == 'low']
            
            # Critical Gaps
            if critical_gaps:
                story.append(Paragraph("Critical Issues", subheading_style))
                for idx, gap in enumerate(critical_gaps, 1):
                    story.append(Paragraph(f"<b>[{idx}] {gap.get('rule_id', 'N/A')}</b>", normal_style))
                    story.append(Paragraph(f"<b>Category:</b> {gap.get('category', 'N/A')}", normal_style))
                    story.append(Paragraph(f"<b>Regulation:</b> {gap.get('regulatory_citation', 'N/A')}", normal_style))
                    story.append(Paragraph(f"<b>Gap:</b> {gap.get('gap_description', 'N/A')}", normal_style))
                    story.append(Paragraph(f"<b>Fix:</b> {gap.get('recommendation', 'N/A')}", normal_style))
                    story.append(Spacer(1, 12))
            
            # High Priority Gaps
            if high_gaps:
                story.append(Paragraph("High Priority Issues", subheading_style))
                for idx, gap in enumerate(high_gaps, 1):
                    story.append(Paragraph(f"<b>[{idx}] {gap.get('rule_id', 'N/A')}</b>", normal_style))
                    story.append(Paragraph(f"<b>Category:</b> {gap.get('category', 'N/A')}", normal_style))
                    story.append(Paragraph(f"<b>Regulation:</b> {gap.get('regulatory_citation', 'N/A')}", normal_style))
                    story.append(Paragraph(f"<b>Gap:</b> {gap.get('gap_description', 'N/A')}", normal_style))
                    story.append(Paragraph(f"<b>Fix:</b> {gap.get('recommendation', 'N/A')}", normal_style))
                    story.append(Spacer(1, 12))
        
        # Recommendations
        recommendations = report_data.get('recommendations', [])
        if recommendations:
            story.append(PageBreak())
            story.append(Paragraph("Recommendations", heading_style))
            for idx, rec in enumerate(recommendations, 1):
                if isinstance(rec, dict):
                    rec_text = rec.get('recommendation', str(rec))
                else:
                    rec_text = str(rec)
                story.append(Paragraph(f"{idx}. {rec_text}", normal_style))
                story.append(Spacer(1, 8))
        
        # Regulatory References
        regulatory_refs = report_data.get('regulatory_references', [])
        if regulatory_refs:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Regulatory References", heading_style))
            for ref in regulatory_refs:
                if isinstance(ref, dict):
                    ref_text = f"{ref.get('name', 'N/A')} - {ref.get('description', '')}"
                else:
                    ref_text = str(ref)
                story.append(Paragraph(f"• {ref_text}", normal_style))
                story.append(Spacer(1, 6))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7f8c8d'),
            alignment=TA_CENTER
        )
        story.append(Paragraph("Generated by ProtocolScout AI Compliance System", footer_style))
        story.append(Paragraph("Powered by Amazon Bedrock (Claude 3.5 Sonnet) | AWS India Region", footer_style))
        
        # Build PDF
        doc.build(story)
        
        print(f"PDF generated successfully: {pdf_file}")
        
        return send_file(
            pdf_file,
            as_attachment=True,
            download_name=f"compliance_report_{protocol_id}.pdf"
        )
    
    except Exception as e:
        print(f"PDF generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'PDF generation failed',
            'message': str(e)
        }), 500

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing all protocols"""
    user_id = current_user.email
    return render_template('dashboard.html', user_id=user_id)

@app.route('/api/protocols/<user_id>')
def get_user_protocols(user_id):
    """Get all protocols for a user"""
    try:
        # Use scan with filter since the index might not exist
        response = audit_table.scan(
            FilterExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id},
            Limit=50
        )
        
        protocols = response.get('Items', [])
        
        # Check actual status by verifying if reports exist in S3
        for protocol in protocols:
            protocol_id = protocol.get('protocol_id')
            current_status = protocol.get('status', 'unknown')
            
            # If status is "processing", check if reports actually exist
            if current_status == 'processing' and protocol_id:
                try:
                    # Check if JSON report exists in S3
                    report_key = f"reports/{protocol_id}/compliance_report.json"
                    s3_client.head_object(Bucket=DOCUMENTS_BUCKET, Key=report_key)
                    # Report exists, update status to completed
                    protocol['status'] = 'completed'
                except s3_client.exceptions.ClientError:
                    # Report doesn't exist yet, keep as processing
                    pass
        
        # Sort by timestamp (most recent first) if timestamp exists
        if protocols and 'timestamp' in protocols[0]:
            protocols.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return jsonify({
            'protocols': protocols,
            'count': len(protocols)
        })
    
    except Exception as e:
        print(f"Protocol fetch error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)
