from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
import os
from flask_sqlalchemy import SQLAlchemy
from import_helper import parse_csv_data # Import helper
from werkzeug.utils import secure_filename
import json
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key') # Session security for Flask-Login

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure instance folder exists
basedir = os.path.abspath(os.path.dirname(__file__))

# Vercel Serverless environment handling (Read-Only FS workaround)
if os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV'):
    instance_path = '/tmp/instance' # Writable on Vercel
else:
    instance_path = os.path.join(basedir, 'instance')

if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Fallback to local SQLite if DATABASE_URL/POSTGRES_URL is not set
db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or ('sqlite:///' + os.path.join(instance_path, 'contracts.db'))
# Sqlalchemy throws errors if postgres string starts with 'postgres://' instead of 'postgresql://'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
DATA_FILE = 'data_contracts.xlsx'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(50))

class Contract(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    nama_perusahaan = db.Column(db.String(255))
    region = db.Column(db.String(100))
    jenis_perjanjian = db.Column(db.String(100))
    no_perjanjian = db.Column(db.String(100))
    status_asli = db.Column(db.String(100))
    tanggal_perjanjian = db.Column(db.Date, nullable=True)
    tanggal_mulai = db.Column(db.Date, nullable=True)
    tanggal_berakhir = db.Column(db.Date, nullable=True)
    status_override = db.Column(db.String(50), nullable=True)
    status_override = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # New Fields from NewContract.tsx
    deal_type = db.Column(db.String(50))
    volume = db.Column(db.String(50)) # Storing as string to keep it simple with unit or separate
    unit = db.Column(db.String(20))
    documents = db.Column(db.Text) # JSON string of filenames
    shipper_initial = db.Column(db.String(50))
    area_initial = db.Column(db.String(50))

    def to_dict(self):
        return {
            'ID': self.id,
            'Nama Perusahaan': self.nama_perusahaan,
            'Region': self.region,
            'Jenis Perjanjian': self.jenis_perjanjian,
            'No Perjanjian': self.no_perjanjian,
            'Status Asli': self.status_asli,
            'Tanggal Perjanjian': self.tanggal_perjanjian,
            'Tanggal Mulai': self.tanggal_mulai,
            'Tanggal Berakhir': self.tanggal_berakhir,
            'Status Override': self.status_override,
            'Notes': self.notes,
            'Deal Type': self.deal_type,
            'Volume': self.volume,
            'Unit': self.unit,
            'Documents': json.loads(self.documents) if self.documents else [],
            'Shipper Init': self.shipper_initial,
            'Area Init': self.area_initial
        }

# New Models for Pricing Map
class Pipeline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(100))
    ruas_pipa = db.Column(db.String(255))
    inch = db.Column(db.String(50)) # Kept as string to handle formatted values or ranges if any
    km = db.Column(db.Float)
    kapasitas_desain = db.Column(db.Float)
    tarif_pipa = db.Column(db.Float)

class Shipper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(100))
    shipper_name = db.Column(db.String(255))
    ruas = db.Column(db.String(255))
    diameter_pipa = db.Column(db.String(50))
    tarif_real = db.Column(db.Float)

# --- Helpers ---
def init_db():
    with app.app_context():
        db.create_all()
        
        # --- Import Default Admin ---
        if User.query.filter_by(username='admin').first() is None:
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('password'),
                role='company_user'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created.")
        
        # --- Import Contracts ---
        if Contract.query.count() == 0:
            print("Contracts table empty. Importing from Excel/CSV...")
            initial_data = []
            
            # 1. Try Excel
            if os.path.exists(DATA_FILE):
                try:
                    df = pd.read_excel(DATA_FILE)
                    initial_data = df.to_dict('records')
                except Exception as e:
                    print(f"Error reading Excel: {e}")
            
            # 2. Try CSV if Excel failed or didn't exist
            if not initial_data:
                csv_path = os.path.join(os.path.dirname(__file__), "..", "Copy of MONITORING PERJANJIAN KOMERSIAL FUNGSI COMMERCIAL CAPACITY - Database.csv")
                if os.path.exists(csv_path):
                    print("Importing initial data from CSV...")
                    initial_data = parse_csv_data(csv_path)

            # Insert data
            for row in initial_data:
                # Parse dates
                def parse_date(d):
                    if pd.isna(d) or d == '-': return None
                    try:
                        return pd.to_datetime(d).date()
                    except:
                        return None
                
                new_contract = Contract(
                    id = str(row.get('ID', '')),
                    nama_perusahaan = row.get('Nama Perusahaan'),
                    region = row.get('Region'),
                    jenis_perjanjian = row.get('Jenis Perjanjian'),
                    no_perjanjian = row.get('No Perjanjian'),
                    status_asli = row.get('Status Asli'),
                    tanggal_perjanjian = parse_date(row.get('Tanggal Perjanjian')),
                    tanggal_mulai = parse_date(row.get('Tanggal Mulai')),
                    tanggal_berakhir = parse_date(row.get('Tanggal Berakhir')),
                    status_override = row.get('Status Override'),
                    notes = row.get('Notes')
                )
                db.session.add(new_contract)
            
            try:
                db.session.commit()
                print(f"Imported {len(initial_data)} contracts to SQLite.")
            except Exception as e:
                print(f"Error saving to DB: {e}")
                db.session.rollback()

        # --- Import Pipelines & Shippers from Combined File ---
        # We check both, if either is empty we re-import to be safe or just check one.
        if Pipeline.query.count() == 0 or Shipper.query.count() == 0:
            print("Pipelines/Shippers table empty. Importing from Combined File...")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(base_dir) 
            combined_path = os.path.join(parent_dir, 'Gabungan_Shipper_Ruas_Tarif (1).xlsx')
            
            if os.path.exists(combined_path):
                try:
                    df = pd.read_excel(combined_path, sheet_name='Gabungan')
                    # Columns expected: 
                    # ['Area', 'Shipper', 'Ruas', 'Dia. Pipa (inch)', 'Tarif Real \n(US$/MSCF)', 
                    #  'No', 'Ruas Pipa', 'Inch', 'Km', 'Kapasitas Desain (MMSCFD)', 'Tarif Pipa\n(USD/MSCF)', 'tarif_gap']
                    
                    # Normalize columns: replace newlines with space, then collapse multiple spaces to single space
                    df.columns = [' '.join(c.replace('\n', ' ').split()) for c in df.columns]

                    # Helper to safe float
                    def safe_float(val):
                        if pd.isna(val) or val == '-': return None
                        try:
                            return float(val)
                        except:
                            return None

                    # 1. Process Pipelines (Deduplicate by 'No')
                    seen_pipeline_nos = set()
                    
                    for _, row in df.iterrows():
                        pipeline_no = row.get('No')
                        
                        # Skip if we've seen this pipeline ID already or if it's invalid
                        if pd.isna(pipeline_no) or pipeline_no in seen_pipeline_nos:
                            continue
                            
                        # Mark as seen
                        seen_pipeline_nos.add(pipeline_no)
                        
                        # Extract Pipeline Data
                        area = row.get('Area')
                        if pd.isna(area): continue

                        p = Pipeline(
                            id=int(pipeline_no) if isinstance(pipeline_no, (int, float)) else None, # preserve ID if safe
                            area=area,
                            ruas_pipa=row.get('Ruas Pipa'),
                            inch=str(row.get('Inch')),
                            km=safe_float(row.get('Km')),
                            kapasitas_desain=safe_float(row.get('Kapasitas Desain (MMSCFD)')),
                            tarif_pipa=safe_float(row.get('Tarif Pipa (USD/MSCF)'))
                        )
                        db.session.add(p)
                    
                    print(f"Pipelines staged (Unique: {len(seen_pipeline_nos)}).")

                    # 2. Process Shippers (Import All)
                    for _, row in df.iterrows():
                        area = row.get('Area')
                        shipper_name = row.get('Shipper')
                        
                        # Skip if critical info missing
                        if pd.isna(area) or pd.isna(shipper_name): continue
                        
                        s = Shipper(
                            area=area,
                            shipper_name=shipper_name,
                            ruas=row.get('Ruas'),
                            diameter_pipa=str(row.get('Dia. Pipa (inch)')),
                            tarif_real=safe_float(row.get('Tarif Real (US$/MSCF)'))
                        )
                        db.session.add(s)
                        
                    db.session.commit()
                    print("Pipelines & Shippers imported from Combined File.")
                    
                except Exception as e:
                    print(f"Error importing combined data: {e}")
                    db.session.rollback()


def load_data():
    with app.app_context():
        contracts = Contract.query.all()
        # Convert to dictionary format expected by templates (compatible with previous pd.to_dict('records'))
        data = []
        for c in contracts:
            # We need to return datetime objects for calculations, similar to pandas timestamp
            row = c.to_dict()
            # Ensure dates are datetime objects for the calculation logic
            if row['Tanggal Berakhir']:
                row['Tanggal Berakhir'] = datetime.combine(row['Tanggal Berakhir'], datetime.min.time())
            else:
                row['Tanggal Berakhir'] = None # or None/NaT handling
            data.append(row)
        return data

def save_data(new_record):
    with app.app_context():
        # Parse dates for DB
        def parse_date(d):
            if not d or d == '-': return None
            try:
                return pd.to_datetime(d).date()
            except:
                return None

        # Check if exists (update) or new
        contract = Contract.query.get(new_record['ID'])
        if not contract:
            contract = Contract(id=new_record['ID'])
            
        contract.nama_perusahaan = new_record.get('Nama Perusahaan')
        contract.region = new_record.get('Region')
        contract.jenis_perjanjian = new_record.get('Jenis Perjanjian') # Might be missing in input form
        contract.no_perjanjian = new_record.get('No Perjanjian') # Might be missing
        contract.status_asli = new_record.get('Status Asli') # Might be missing
        contract.tanggal_perjanjian = parse_date(new_record.get('Tanggal Perjanjian'))
        contract.tanggal_mulai = parse_date(new_record.get('Tanggal Mulai'))
        contract.tanggal_berakhir = parse_date(new_record.get('Tanggal Berakhir'))
        contract.status_override = new_record.get('Status Override')
        contract.status_override = new_record.get('Status Override')
        contract.notes = new_record.get('Notes')
        
        # New fields
        contract.deal_type = new_record.get('Deal Type')
        contract.volume = new_record.get('Volume')
        contract.unit = new_record.get('Unit')
        
        if new_record.get('Documents'):
             # If documents is list, dump to json
             contract.documents = json.dumps(new_record.get('Documents'))
        elif not contract.documents:
             contract.documents = "[]"
        
        db.session.add(contract)
        db.session.commit()

def calculate_status(row):
    # If there is a manual override usage
    if pd.notna(row.get('Status Override')) and row.get('Status Override') in ['done', 'pending', 'urgent', 'expired', 'safe']:
        return row['Status Override']

    # Date calc
    today = datetime.now()
    end_date = row.get('Tanggal Berakhir')
    
    if end_date is None or pd.isna(end_date):
        return 'unknown'
        
    days_left = (end_date - today).days
    
    if days_left < 0:
        return 'expired'
    elif days_left <= 30:
        return 'urgent'
    else:
        return 'safe' # or active

# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/')
def index():
    raw_data = load_data()
    total = len(raw_data)
    
    # Simple logic to count stats for Home Page cards
    urgent = 0
    active = 0
    
    for row in raw_data:
        status = calculate_status(row)
        # Match Dashboard Logic:
        # Butuh Follow Up = urgent, expired, pending
        if status in ['urgent', 'expired', 'pending']:
            urgent += 1
        # Kontrak Aktif = safe, done
        elif status in ['safe', 'done']:
            active += 1
            
    return render_template('index.html', total=total, urgent=urgent, active=active)

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        raw_data = load_data()
        processed_data = []
        
        for row in raw_data:
            status = calculate_status(row)
            
            # Format date for display
            end_date_display = '-'
            if row.get('Tanggal Berakhir'):
                end_date_display = row['Tanggal Berakhir'].strftime('%Y-%m-%d')

            processed_data.append({
                'id': row.get('ID', '-'),
                'name': row.get('Nama Perusahaan', '-'),
                'region': row.get('Region', '-'),
                'jenis': row.get('Jenis Perjanjian', '-'),
                'no_perjanjian': row.get('No Perjanjian', '-'),
                'status_asli': row.get('Status Asli', '-'),
                'tgl_perjanjian': str(row.get('Tanggal Perjanjian', '-')),
                'start_date': str(row.get('Tanggal Mulai', '-')),
                'end_date': str(row.get('Tanggal Berakhir', '-')),
                'contract_end': end_date_display,
                'status': status,
                'status_override': row.get('Status Override', ''),
                'shipper_init': row.get('Shipper Init', '-'),
                'area_init': row.get('Area Init', '-'),
                'documents': row.get('Documents', [])
            })
            
        return render_template('dashboard.html', customers=processed_data)
    except Exception as e:
        import traceback
        return f"Error: {str(e)} <br> <pre>{traceback.format_exc()}</pre>"

@app.route('/insights')
@login_required
def insights():
    raw_data = load_data()

    # Calculate Stats for Insights (Restored)
    stats = {
        'urgent': 0,
        'pending': 0,
        'done': 0,
        'total': len(raw_data),
        'by_region': {}
    }
    
    for row in raw_data:
        status = calculate_status(row)
        
        # If manual status override exists, use it
        manual_status = row.get('Status Override')
        if pd.notna(manual_status) and manual_status in ['urgent', 'pending', 'done']:
            stats[manual_status] += 1
        else:
            # Auto-calc fallback
            if status == 'urgent':
                stats['urgent'] += 1
            elif status == 'expired': 
                stats['urgent'] += 1 # Expired needs attention
            else:
                stats['done'] += 1 # Safe/Active
        
        # Region Count
        region = row.get('Region', 'Unknown')
        if pd.isna(region): region = 'Unknown'
        stats['by_region'][region] = stats['by_region'].get(region, 0) + 1
    
    # Calculate Stats for Insights
    # --- VISUALIZATION LOGIC ---
    charts_json = {}
    area_health = []
    try:
        # File Paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(base_dir)
        gabungan_path = os.path.join(parent_dir, 'Gabungan_Shipper_Ruas_Tarif (1).xlsx')
        monitoring_path = os.path.join(parent_dir, 'Copy of MONITORING PERJANJIAN KOMERSIAL FUNGSI COMMERCIAL CAPACITY - Database.csv')

        # 1. Load Data
        df_gabungan = pd.DataFrame()
        if os.path.exists(gabungan_path):
             df_gabungan = pd.read_excel(gabungan_path, sheet_name='Gabungan')
        
        df_monitor = pd.DataFrame()
        if os.path.exists(monitoring_path):
             try:
                 df_monitor = pd.read_csv(monitoring_path, sep=';')
                 if len(df_monitor.columns) < 2: 
                     df_monitor = pd.read_csv(monitoring_path)
             except:
                 df_monitor = pd.read_csv(monitoring_path)

        # 2. VIZ 1: Tariff Gap Analysis (Simplified)
        if not df_gabungan.empty:
            df_gabungan.columns = [str(c).strip().replace('\n', ' ') for c in df_gabungan.columns]
            col_real = next((c for c in df_gabungan.columns if 'Real' in c), None)
            col_ref = next((c for c in df_gabungan.columns if 'Pipa' in c and 'USD' in c), None)
            
            if col_real and col_ref:
                df_gabungan['tarif_gap'] = df_gabungan[col_real] - df_gabungan[col_ref]
                df_viz1 = df_gabungan.sort_values('tarif_gap', ascending=True)
                
                # Limit to Top 5 Neg and Top 5 Pos to reduce clutter
                head = df_viz1.head(5)
                tail = df_viz1.tail(5)
                df_viz1 = pd.concat([head, tail])
                
                # simplified color labels
                df_viz1['Color'] = df_viz1['tarif_gap'].apply(lambda x: 'Underpriced' if x < 0 else 'Premium')
                
                # Softer colors
                colors = {'Underpriced': '#E57373', 'Premium': '#4DB6AC'} 
                
                fig1 = px.bar(df_viz1,
                              y='Shipper',
                              x='tarif_gap',
                              color='Color',
                              orientation='h',
                              color_discrete_map=colors,
                              hover_data=['Ruas', 'Area'])
                
                fig1.update_layout(
                    title=dict(text='Tariff Gap Overview (Top Deviations)', font=dict(size=14)),
                    xaxis_title='Gap (USD)',
                    yaxis_title=None,
                    template="plotly_white",
                    margin=dict(l=20, r=20, t=50, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                charts_json['tariff_gap'] = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)

        # 3. VIZ 2: Contract Health (Focus Area)
        # PRIORITIZE DB DATA (raw_data) so user updates are reflected
        df_timeline = pd.DataFrame()
        
        # Primary: Database (raw_data)
        if len(raw_data) > 0:
             df_db = pd.DataFrame(raw_data)
             # Ensure required columns exist
             if 'Tanggal Mulai' in df_db.columns:
                 df_db['Start'] = pd.to_datetime(df_db['Tanggal Mulai'])
                 df_db['End'] = pd.to_datetime(df_db['Tanggal Berakhir'])
                 df_db['Name'] = df_db['Nama Perusahaan']
                 df_timeline = df_db.dropna(subset=['Start', 'End']).copy()

        # Fallback: Monitor CSV (static file)
        elif not df_monitor.empty and 'Start' in df_monitor.columns and 'End' in df_monitor.columns:
             df_monitor['Start'] = pd.to_datetime(df_monitor['Start'], errors='coerce')
             df_monitor['End'] = pd.to_datetime(df_monitor['End'], errors='coerce')
             df_timeline = df_monitor.dropna(subset=['Start', 'End', 'SHIPPER']).copy()
             df_timeline['Name'] = df_timeline['SHIPPER']
        
        if not df_timeline.empty:
             today = pd.Timestamp.now()
             df_timeline['Days_Left'] = (df_timeline['End'] - today).dt.days
             
             # Calculate Status (Respecting Overrides)
             def get_row_status(row):
                 # 1. Manual Override
                 if 'Status Override' in row and pd.notna(row['Status Override']):
                     val = row['Status Override'].lower()
                     if val == 'done': return 'Safe' # Map 'done' to 'Safe' color
                     if val == 'urgent': return 'Critical (<6 Mo)'
                     if val == 'expired': return 'Expired'
                 
                 # 2. Date-based Fallback
                 d = row['Days_Left']
                 if d < 0: return 'Expired'
                 if d < 180: return 'Critical (<6 Mo)'
                 return 'Active'

             df_timeline['Status'] = df_timeline.apply(get_row_status, axis=1)
             
             # FILTER: Show only Expired, Critical, and active ones expiring in next 2 years
             # To avoid showing 10-year safe contracts taking up space
             mask_urgent = df_timeline['Status'].isin(['Expired', 'Critical (<6 Mo)'])
             mask_upcoming = (df_timeline['Days_Left'] < 730) & (df_timeline['Days_Left'] >= 0)
             
             df_viz2 = df_timeline[mask_urgent | mask_upcoming].sort_values('End')
             
             # If too few, add some safe ones for context
             if len(df_viz2) < 5:
                  safe_ones = df_timeline[~mask_urgent & ~mask_upcoming].head(5)
                  df_viz2 = pd.concat([df_viz2, safe_ones]).sort_values('End')
                  
             # Hard limit rows
             if len(df_viz2) > 20:
                 df_viz2 = df_viz2.head(20)

             if not df_viz2.empty:
                 color_map = {'Expired': '#333333', 'Critical (<6 Mo)': '#E53935', 'Active': '#1976D2'}
                 
                 fig2 = px.timeline(df_viz2,
                                   x_start="Start",
                                   x_end="End",
                                   y="Name",
                                   color="Status",
                                   color_discrete_map=color_map)
                 
                 fig2.update_yaxes(autorange="reversed")
                 fig2.update_layout(
                    title=dict(text='Contract Monitoring (Approaching End Date)', font=dict(size=14)),
                    template="plotly_white",
                    margin=dict(l=20, r=20, t=50, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                 )
                 charts_json['contract_health'] = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)


        # 4. VIZ 3: Infrastructure Flow (Clean Low-Density)
        if not df_gabungan.empty:
            if 'Area' in df_gabungan.columns and 'Shipper' in df_gabungan.columns and 'Ruas' in df_gabungan.columns:
                df_sankey = df_gabungan.groupby(['Area', 'Shipper', 'Ruas']).size().reset_index(name='Count')
                
                # Relaxed limit to ensure all Areas (including KAL) are shown
                if len(df_sankey) > 100:
                     df_sankey = df_sankey.head(100)
                
                all_nodes = list(df_sankey['Area'].unique()) + list(df_sankey['Shipper'].unique()) + list(df_sankey['Ruas'].unique())
                all_nodes = list(dict.fromkeys(all_nodes)) 
                node_map = {node: i for i, node in enumerate(all_nodes)}
                
                sources = []
                targets = []
                values = []
                
                # Flow 1
                for _, row in df_sankey.iterrows():
                    sources.append(node_map[row['Area']])
                    targets.append(node_map[row['Shipper']])
                    values.append(1)
                # Flow 2
                for _, row in df_sankey.iterrows():
                    sources.append(node_map[row['Shipper']])
                    targets.append(node_map[row['Ruas']])
                    values.append(1)
                    
                fig3 = go.Figure(data=[go.Sankey(
                    node = dict(
                      pad = 20,
                      thickness = 10,
                      line = dict(color = "white", width = 0.5),
                      label = [n[:15] + '...' if len(n)>15 else n for n in all_nodes], # Truncate long names
                      color = "#90CAF9"
                    ),
                    link = dict(
                      source = sources,
                      target = targets,
                      value = values,
                      color = "#E3F2FD" # Very light blue for flow
                  ))])
                
                fig3.update_layout(
                    title=dict(text='Key Infrastructure Flows', font=dict(size=14)),
                    margin=dict(l=10, r=10, t=40, b=10),
                    font=dict(size=10)
                )
                charts_json['sankey'] = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)

        # 5. NEW VISUALIZATIONS: Area Health & Volume Thermometer

        revenue_path = os.path.join(base_dir, 'Revenue_Gas_Pipeline_v2.xlsx') # In root folder
        if os.path.exists(revenue_path):
            df_rev = pd.read_excel(revenue_path, sheet_name='Summary per Area')
            df_rev = df_rev[df_rev['Area'] != 'GRAND TOTAL']
            for _, row in df_rev.iterrows():
                area = row.get('Area')
                if pd.isna(area): continue
                
                shippers = int(row.get('Jumlah Shipper', 0))
                target_vol = float(row.get('Total Target Volume (MMSCFD)', 0))
                real_vol = float(row.get('Total Realisasi Volume (MMSCFD)', 0))
                target_rev = float(row.get('Total Revenue Target (USD)', 0))
                real_rev = float(row.get('Total Revenue Realisasi (USD)', 0))

                gap_rev_pct = ((real_rev - target_rev) / target_rev) * 100 if target_rev > 0 else 0
                vol_pct = (real_vol / target_vol) * 100 if target_vol > 0 else 0
                
                volume_status = 'good' if vol_pct >= 100 else 'bad'
                
                area_health.append({
                    'area': area,
                    'shippers': shippers,
                    'revenue_gap': gap_rev_pct,
                    'is_surplus': gap_rev_pct >= 0,
                    'target_vol': target_vol,
                    'real_vol': real_vol,
                    'target_rev': target_rev,
                    'real_rev': real_rev,
                    'vol_pct': vol_pct,
                    'volume_status': volume_status
                })

    except Exception as e:
        print(f"Error creating visualization: {e}")

    return render_template('insights.html', stats=stats, charts=charts_json, area_health=area_health)

@app.route('/update_status/<id>', methods=['POST'])
@login_required
def update_status(id):
    data = request.json
    new_status = data.get('status')
    
    contract = Contract.query.get(id)
    if contract:
        contract.status_override = new_status
        db.session.commit()
        return {'success': True}
    return {'success': False}, 404

@app.route('/delete_contract/<id>', methods=['POST'])
@login_required
def delete_contract(id):
    contract = Contract.query.get(id)
    if contract:
        db.session.delete(contract)
        db.session.commit()
        return {'success': True}
    return {'success': False}, 404

@app.route('/input', methods=['GET', 'POST'])
@login_required
def input_data():
    if request.method == 'GET':
        # Fetch existing partners for the dropdown
        existing_data = load_data()
        # Get unique partner names, sorted
        partners = sorted(list(set([row.get('Nama Perusahaan') for row in existing_data if row.get('Nama Perusahaan')])))
        return render_template('input.html', partners=partners)

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            new_id = request.form.get('id')
            if Contract.query.get(new_id):
                return "Error: ID already exists!"
            
            # Handle File Uploads
            uploaded_files = request.files.getlist('documents')
            filenames = []
            
            upload_folder = os.path.join(instance_path, 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            for file in uploaded_files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    # Unique filename to prevent overwrite
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"{timestamp}_{filename}"
                    file.save(os.path.join(upload_folder, filename))
                    filenames.append(filename)

            new_contract = Contract(
                id=new_id,
                nama_perusahaan=request.form.get('nama_perusahaan'),
                region=request.form.get('region'),
                jenis_perjanjian=request.form.get('jenis_perjanjian'),
                no_perjanjian=request.form.get('no_perjanjian'),
                status_asli='Active', # Default
                tanggal_perjanjian=datetime.strptime(request.form.get('tanggal_perjanjian'), '%Y-%m-%d').date() if request.form.get('tanggal_perjanjian') else None,
                tanggal_mulai=datetime.strptime(request.form.get('tanggal_mulai'), '%Y-%m-%d').date() if request.form.get('tanggal_mulai') else None,
                tanggal_berakhir=datetime.strptime(request.form.get('tanggal_berakhir'), '%Y-%m-%d').date() if request.form.get('tanggal_berakhir') else None,
                notes=request.form.get('notes'),
                deal_type=request.form.get('deal_type'),
                volume=request.form.get('volume'),
                unit=request.form.get('unit'),
                documents=json.dumps(filenames),
                shipper_initial=request.form.get('shipper_initial'),
                area_initial=request.form.get('area_initial')
            )
            db.session.add(new_contract)
            db.session.commit()
            return redirect(url_for('dashboard'))

    return render_template('input.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    upload_folder = os.path.join(instance_path, 'uploads')
    return send_from_directory(upload_folder, filename)

@app.route('/pricing-map')
def pricing_map():
    pipelines, shippers = load_pricing_data()
    if not current_user.is_authenticated:
        shippers = {}
    return render_template('pricing_map.html', pipelines=pipelines, shippers=shippers)

# --- Pricing Data Helper ---
def load_pricing_data():
    with app.app_context():
        # Load Pipelines from DB (GAS)
        pipelines_data = {}
        pipelines = Pipeline.query.all()
        for p in pipelines:
            area = p.area
            if area not in pipelines_data: pipelines_data[area] = []
            
            pipelines_data[area].append({
                'no': p.id,
                'ruas': p.ruas_pipa,
                'inch': p.inch,
                'km': p.km,
                'capacity': p.kapasitas_desain,
                'tariff': p.tarif_pipa,
                'realization': 0, # Default for gas without realisasi
                'utilization': 0
            })

        # Load Shippers from DB (GAS)
        shippers_data = {}
        shippers = Shipper.query.all()
        for s in shippers:
            area = s.area
            if area not in shippers_data: shippers_data[area] = []
            
            shippers_data[area].append({
                'shipper': s.shipper_name,
                'ruas': s.ruas,
                'dia': s.diameter_pipa,
                'tariff_real': s.tarif_real
            })

        # --- Integrate MINYAK CSV Data ---
        try:
            def to_float(val):
                if pd.isna(val): return 0.0
                try:
                    return float(str(val).replace(',', '.'))
                except:
                    return 0.0

            # Realisasi Minyak
            df_real_minyak = pd.read_csv('Data Volume & Realisasi minyak.csv', sep=';', encoding='latin1')
            area_realization = {}
            for _, row in df_real_minyak.iterrows():
                area = row.get('Area')
                if pd.isna(area): continue
                area_realization[area] = area_realization.get(area, 0) + to_float(row.get('Realisasi (MMSCFD)'))

            # Pipa Minyak
            df_pipa_minyak = pd.read_csv('Data Ruas Pipa dan Tarif MINYAK.csv', sep=';', encoding='latin1')
            for _, row in df_pipa_minyak.iterrows():
                area = row.get('Area')
                if pd.isna(area) or area == 'TOTAL': continue
                if area not in pipelines_data: pipelines_data[area] = []
                
                cap = to_float(row.get('Kapasitas Desain (BOPD)'))
                real = area_realization.get(area, 0)
                util = round((real / cap * 100), 2) if cap > 0 else 0
                
                pipelines_data[area].append({
                    'no': str(row.get('Ruas Pipa')),
                    'ruas': str(row.get('Ruas Pipa')),
                    'inch': str(row.get('Inch')),
                    'km': to_float(row.get('Km')),
                    'capacity': cap,
                    'tariff': to_float(row.get('Tarif Pipa\n(USD/BBL)')),
                    'realization': real,
                    'utilization': util
                })
        except Exception as e:
            print("Error parsing minyak CSV:", e)

        return pipelines_data, shippers_data


@app.route('/reset-csv')
@login_required
def reset_csv():
    # Force re-import from CSV/Excel
    # Drop all tables and re-init
    with app.app_context():
        db.drop_all()
        init_db()
    return redirect(url_for('dashboard'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    if not os.path.exists("contracts.db"):
        init_db()
    else:
        # Also ensure tables exist even if file exists (partial run?)
        with app.app_context():
            db.create_all()
            
    app.run(debug=True, port=5001)
