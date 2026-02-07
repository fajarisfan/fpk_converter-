import os
import pandas as pd
from flask import Flask, request, render_template_string, send_file, session, redirect, url_for
import tabula
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'pdf'}

# PIN yang sudah di-hash (default PIN: 1234)
# Untuk mengganti PIN, generate hash baru di: https://www.browserling.com/tools/bcrypt
# Atau gunakan generate_password_hash('PIN_ANDA') dari Werkzeug
DEFAULT_PIN_HASH = generate_password_hash('1234')

# Session timeout dalam detik (30 menit)
SESSION_TIMEOUT = 1800

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    """Memeriksa apakah ekstensi file diizinkan."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_fpk_data(pdf_path, output_csv_path):
    """
    Fungsi pembersihan data FPK untuk format asli PDF
    """
    # 1. Ekstraksi Data dari PDF
    df_list = tabula.read_pdf(
        pdf_path, 
        pages='all', 
        multiple_tables=True, 
        lattice=True, 
        pandas_options={'header': None}
    )

    if not df_list:
        raise ValueError("Tidak ada tabel yang berhasil diekstrak.")

    # Filter dan Gabungkan DataFrames
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    
    if not cleaned_df_list:
        raise ValueError("Tidak ada tabel dengan struktur kolom yang sesuai (min 6 kolom) yang ditemukan.")
        
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()

    # Pembersihan Baris Non-Data
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    
    # Penentuan Nama Kolom
    df_data.columns = [
        'No. Urut',          
        'No.SEP',            
        'Tgl. Verifikasi',   
        'Biaya Riil RS',     
        'Diajukan',    
        'Disetujui'    
    ]

    # --- PEMBERSIHAN KOLOM No.SEP ---
    if 'No.SEP' in df_data.columns:
        df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.strip()
        df_data['No.SEP'] = df_data['No.SEP'].str.replace(r'[^a-zA-Z0-9]', '', regex=True)
        df_data['No.SEP'] = df_data['No.SEP'].str.replace(r'\s+', '', regex=True)
    
    # --- PEMBERSIHAN KOLOM Disetujui ---
    if 'Disetujui' in df_data.columns:
        df_data['Disetujui'] = df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
        df_data['Disetujui'] = df_data['Disetujui'].str.replace(r'\s+', '', regex=True)
        df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'], errors='coerce')
        df_data['Disetujui'] = df_data['Disetujui'].fillna(0).astype(int)
    
    # --- FILTER KOLOM YANG DIBUTUHKAN ---
    df_final = df_data[['No.SEP', 'Disetujui']].copy()
    
    # --- HAPUS BARIS KOSONG ATAU TIDAK VALID ---
    df_final = df_final[df_final['No.SEP'].notna() & (df_final['No.SEP'].str.strip() != '')]
    df_final = df_final[df_final['No.SEP'].str.replace(r'\s+', '', regex=True) != '']
    df_final = df_final[df_final['Disetujui'] > 0]
    df_final = df_final.reset_index(drop=True)
    
    # --- EKSPOR KE CSV ---
    df_final.to_csv(output_csv_path, index=False, header=True, sep=',', encoding='utf-8')
    
    return True

# Login Page Template
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FPK Converter - Login</title>
    
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
            padding: 40px;
            width: 100%;
            max-width: 400px;
            position: relative;
            overflow: hidden;
        }
        
        .login-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 5px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo-icon {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 15px;
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        .form-control {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px 15px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn-login {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            width: 100%;
            transition: all 0.3s;
            margin-top: 10px;
        }
        
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-login:active {
            transform: translateY(0);
        }
        
        .pin-input {
            letter-spacing: 8px;
            font-family: monospace;
            font-size: 24px;
            text-align: center;
        }
        
        .demo-info {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            border-left: 4px solid #667eea;
        }
        
        .demo-info h6 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .alert {
            border-radius: 8px;
            border: none;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .password-toggle {
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: #667eea;
            cursor: pointer;
        }
        
        .form-group {
            position: relative;
        }
        
        .back-link {
            text-align: center;
            margin-top: 20px;
        }
        
        .back-link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        .back-link a:hover {
            text-decoration: underline;
        }
        
        .keypad {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 20px;
        }
        
        .keypad-btn {
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            background: white;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .keypad-btn:hover {
            background: #f8f9fa;
            border-color: #667eea;
        }
        
        .keypad-btn:active {
            transform: scale(0.95);
        }
        
        .keypad-btn.clear {
            grid-column: span 2;
            background: #ff6b6b;
            color: white;
            border-color: #ff6b6b;
        }
        
        .keypad-btn.clear:hover {
            background: #ff5252;
        }
        
        .keypad-btn.enter {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .keypad-btn.enter:hover {
            background: #5a6fd8;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo">
            <div class="logo-icon">
                <i class="fas fa-lock"></i>
            </div>
            <h3>FPK Converter</h3>
            <p class="text-muted">Masukkan PIN untuk mengakses konverter</p>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }}">
                        <div class="d-flex align-items-center">
                            <i class="fas {% if category == 'error' %}fa-exclamation-triangle{% else %}fa-info-circle{% endif %} me-2"></i>
                            <div>{{ message }}</div>
                        </div>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="post" action="{{ url_for('login') }}">
            <div class="mb-3">
                <label for="pin" class="form-label">PIN Akses</label>
                <div class="form-group">
                    <input type="password" 
                           class="form-control pin-input" 
                           id="pin" 
                           name="pin" 
                           maxlength="6"
                           placeholder="••••••"
                           required
                           autocomplete="off">
                    <button type="button" class="password-toggle" id="togglePassword">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
                <div class="form-text">
                    Masukkan 6 digit PIN untuk mengakses konverter
                </div>
            </div>
            
            <!-- Virtual Keypad -->
            <div class="keypad mb-3">
                <button type="button" class="keypad-btn" data-value="1">1</button>
                <button type="button" class="keypad-btn" data-value="2">2</button>
                <button type="button" class="keypad-btn" data-value="3">3</button>
                <button type="button" class="keypad-btn" data-value="4">4</button>
                <button type="button" class="keypad-btn" data-value="5">5</button>
                <button type="button" class="keypad-btn" data-value="6">6</button>
                <button type="button" class="keypad-btn" data-value="7">7</button>
                <button type="button" class="keypad-btn" data-value="8">8</button>
                <button type="button" class="keypad-btn" data-value="9">9</button>
                <button type="button" class="keypad-btn clear" id="clearPin">C</button>
                <button type="button" class="keypad-btn" data-value="0">0</button>
                <button type="button" class="keypad-btn enter" id="enterPin">↵</button>
            </div>
            
            <button type="submit" class="btn-login">
                <i class="fas fa-sign-in-alt me-2"></i> Masuk ke Konverter
            </button>
        </form>
        
        <div class="demo-info">
            <h6><i class="fas fa-info-circle me-2"></i>Info Demo</h6>
            <p class="small mb-2">
                <i class="fas fa-key me-2"></i>
                <strong>PIN Demo:</strong> <code>1234</code>
            </p>
            <p class="small mb-0">
                <i class="fas fa-clock me-2"></i>
                Session akan berakhir dalam 30 menit setelah login
            </p>
        </div>
        
        <div class="back-link">
            <a href="https://isfan.dev">
                <i class="fas fa-arrow-left"></i> Kembali ke Portfolio
            </a>
        </div>
    </div>

    <script>
        // Toggle password visibility
        const togglePassword = document.getElementById('togglePassword');
        const pinInput = document.getElementById('pin');
        
        togglePassword.addEventListener('click', function() {
            const type = pinInput.getAttribute('type') === 'password' ? 'text' : 'password';
            pinInput.setAttribute('type', type);
            this.innerHTML = type === 'password' ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
        });
        
        // Virtual keypad functionality
        const keypadButtons = document.querySelectorAll('.keypad-btn[data-value]');
        const clearButton = document.getElementById('clearPin');
        const enterButton = document.getElementById('enterPin');
        
        // Add number to PIN input
        keypadButtons.forEach(button => {
            button.addEventListener('click', function() {
                const value = this.getAttribute('data-value');
                if (pinInput.value.length < 6) {
                    pinInput.value += value;
                    pinInput.dispatchEvent(new Event('input'));
                }
            });
        });
        
        // Clear PIN input
        clearButton.addEventListener('click', function() {
            pinInput.value = '';
            pinInput.dispatchEvent(new Event('input'));
        });
        
        // Auto-submit on enter button click
        enterButton.addEventListener('click', function() {
            if (pinInput.value.length === 6) {
                document.querySelector('form').submit();
            }
        });
        
        // Auto-focus on PIN input
        pinInput.focus();
        
        // Prevent form submission on enter key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && document.activeElement !== pinInput) {
                e.preventDefault();
            }
        });
        
        // Show input effect
        pinInput.addEventListener('input', function() {
            const value = this.value;
            const stars = '•'.repeat(value.length);
            const spaces = ' '.repeat(6 - value.length);
            this.value = value; // Keep actual value
        });
    </script>
</body>
</html>
"""

# Main Converter Template (Sama seperti sebelumnya, tapi dengan logout button)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FPK PDF to CSV Converter</title>
    
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem 0;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            border-radius: 15px;
            padding: 0.5rem 1rem;
        }
        
        .navbar-brand {
            font-weight: bold;
            color: #667eea !important;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .user-icon {
            width: 35px;
            height: 35px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .logout-btn {
            background: #ff6b6b;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: all 0.3s;
        }
        
        .logout-btn:hover {
            background: #ff5252;
            transform: translateY(-2px);
        }
        
        .card {
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            border: none;
        }
        
        .card-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px 15px 0 0 !important;
            padding: 1.5rem;
        }
        
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 10px;
            padding: 3rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: rgba(102, 126, 234, 0.05);
        }
        
        .upload-area:hover {
            background: rgba(102, 126, 234, 0.1);
            border-color: #764ba2;
        }
        
        .btn-convert {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .btn-convert:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-download {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 8px;
            font-weight: 600;
        }
        
        .preview-table {
            font-size: 0.85rem;
        }
        
        .preview-table th {
            background: #667eea;
            color: white;
            position: sticky;
            top: 0;
        }
        
        .format-info {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            border-left: 4px solid #667eea;
        }
        
        .format-info code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
        }
        
        .session-timer {
            position: fixed;
            top: 100px;
            right: 20px;
            background: white;
            border-radius: 10px;
            padding: 10px 15px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 1000;
            animation: slideInRight 0.5s ease-out;
        }
        
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .timer-circle {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: conic-gradient(#667eea 0% 100%, #e0e0e0 100% 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg">
        <div class="container-fluid">
            <a class="navbar-brand" href="#">
                <i class="fas fa-file-contract me-2"></i>FPK Converter v2.0
            </a>
            
            <div class="d-flex align-items-center">
                <div class="user-info me-3">
                    <div class="user-icon">
                        <i class="fas fa-user"></i>
                    </div>
                    <div>
                        <div class="small fw-bold">Demo User</div>
                        <div class="small text-muted">FPK Converter</div>
                    </div>
                </div>
                <a href="{{ url_for('logout') }}" class="logout-btn">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
    </nav>

    <!-- Session Timer -->
    <div class="session-timer" id="sessionTimer">
        <div class="timer-circle" id="timerCircle">30:00</div>
        <div>
            <div class="small fw-bold">Session Timer</div>
            <div class="small text-muted" id="timerText">Auto logout dalam: <span id="timeRemaining">30:00</span></div>
        </div>
    </div>

    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header text-center">
                        <h4 class="mb-2"><i class="fas fa-file-contract me-2"></i>FPK PDF to CSV Converter</h4>
                        <p class="mb-0">Konversi file PDF FPK ke format CSV dengan header asli</p>
                    </div>
                    
                    <div class="card-body">
                        <form method="post" enctype="multipart/form-data" id="uploadForm">
                            <!-- Upload Area -->
                            <div class="mb-4">
                                <div class="upload-area" id="dropZone">
                                    <input type="file" name="file" id="fileInput" class="d-none" accept=".pdf">
                                    <i class="fas fa-cloud-upload-alt fa-3x text-primary mb-3"></i>
                                    <h5 id="fileLabel">Pilih atau Tarik File PDF FPK</h5>
                                    <p class="text-muted small mb-2">Format yang didukung: PDF FPK standar</p>
                                    <div class="file-info" id="fileInfo" style="display: none;">
                                        <div class="d-flex justify-content-between align-items-center bg-white p-2 rounded">
                                            <div>
                                                <i class="fas fa-file-pdf text-danger me-2"></i>
                                                <span id="fileName">filename.pdf</span>
                                            </div>
                                            <span class="badge bg-primary" id="fileSize">0 MB</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Format Info -->
                            <div class="format-info mb-4">
                                <h6><i class="fas fa-info-circle me-2"></i>Format Output CSV:</h6>
                                <div class="bg-dark text-light p-2 rounded">
                                    <code>No.SEP,Disetujui</code><br>
                                    <code>1028R0010825V007480,5810400</code><br>
                                    <code>1028R0010825V007875,17002900</code><br>
                                    <code>1028R0010825V007887,10572300</code>
                                </div>
                                <p class="mt-2 mb-0 small text-muted">
                                    <i class="fas fa-check-circle text-success me-1"></i>
                                    Header: <strong>No.SEP</strong> dan <strong>Disetujui</strong> (sesuai format PDF)
                                </p>
                            </div>
                            
                            <!-- Convert Button -->
                            <div class="d-grid mb-3">
                                <button type="submit" class="btn-convert" id="convertBtn">
                                    <i class="fas fa-magic me-2"></i> Konversi ke CSV
                                </button>
                            </div>
                        </form>
                        
                        <!-- Preview Section -->
                        {% if preview_data %}
                        <div class="mb-4">
                            <h6><i class="fas fa-eye me-2"></i>Preview Hasil ({{ preview_count }} data)</h6>
                            <div class="table-responsive" style="max-height: 300px;">
                                <table class="table table-sm preview-table">
                                    <thead>
                                        <tr>
                                            <th>No.SEP</th>
                                            <th>Disetujui</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for row in preview_data %}
                                        <tr>
                                            <td>{{ row.no_sep }}</td>
                                            <td>{{ row.di_setujui }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            {% if preview_count > 10 %}
                            <div class="text-center mt-2">
                                <small class="text-muted">... dan {{ preview_count - 10 }} data lainnya</small>
                            </div>
                            {% endif %}
                        </div>
                        {% endif %}
                        
                        <!-- Messages -->
                        {% if message %}
                        <div class="alert {% if 'Berhasil' in message %}alert-success{% else %}alert-danger{% endif %} mt-3">
                            <div class="d-flex align-items-center">
                                <i class="fas {% if 'Berhasil' in message %}fa-check-circle{% else %}fa-exclamation-triangle{% endif %} me-3"></i>
                                <div>
                                    <p class="mb-0">{{ message }}</p>
                                    {% if 'Berhasil' in message %}
                                    <small class="d-block mt-1">
                                        <i class="fas fa-info-circle me-1"></i>
                                        Header: <code>No.SEP,Disetujui</code>
                                    </small>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        {% endif %}
                        
                        <!-- Download Section -->
                        {% if download_link %}
                        <div class="alert alert-success mt-3">
                            <div class="row align-items-center">
                                <div class="col-md-8">
                                    <h6 class="mb-1">✅ CSV Siap Diunduh!</h6>
                                    <p class="mb-0 small">
                                        Format: <code>No.SEP,Disetujui</code><br>
                                        Total data: {{ preview_count }} baris
                                    </p>
                                </div>
                                <div class="col-md-4 text-md-end">
                                    <a href="{{ download_link }}" class="btn-download">
                                        <i class="fas fa-download me-2"></i> Download CSV
                                    </a>
                                </div>
                            </div>
                        </div>
                        {% endif %}
                    </div>
                    
                    <div class="card-footer text-center text-muted">
                        <small>
                            <i class="fas fa-lock me-1"></i> Session ID: {{ session_id }} • 
                            <i class="fas fa-clock me-1"></i> Auto-logout dalam: <span id="footerTimer">30:00</span>
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript -->
    <script>
        // Session Timer
        let sessionTime = {{ session_time }};
        const timerElement = document.getElementById('timeRemaining');
        const timerCircle = document.getElementById('timerCircle');
        const footerTimer = document.getElementById('footerTimer');
        
        function updateTimer() {
            const minutes = Math.floor(sessionTime / 60);
            const seconds = sessionTime % 60;
            const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            timerElement.textContent = timeString;
            footerTimer.textContent = timeString;
            timerCircle.textContent = timeString;
            
            // Update circle progress
            const percentage = (sessionTime / {{ session_timeout }}) * 100;
            timerCircle.style.background = `conic-gradient(#667eea 0% ${percentage}%, #e0e0e0 ${percentage}% 100%)`;
            
            // Change color when time is low
            if (sessionTime <= 300) { // 5 minutes
                timerCircle.style.background = `conic-gradient(#ff6b6b 0% ${percentage}%, #e0e0e0 ${percentage}% 100%)`;
                timerCircle.style.color = '#ff6b6b';
            }
            
            if (sessionTime <= 0) {
                alert('Session telah berakhir. Silakan login kembali.');
                window.location.href = "{{ url_for('login') }}";
            } else {
                sessionTime--;
                setTimeout(updateTimer, 1000);
            }
        }
        
        // Start timer
        updateTimer();
        
        // File Upload Functionality
        const fileInput = document.getElementById('fileInput');
        const dropZone = document.getElementById('dropZone');
        const fileLabel = document.getElementById('fileLabel');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const convertBtn = document.getElementById('convertBtn');
        
        // Drag and Drop functionality
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.borderColor = '#43e97b';
                dropZone.style.background = 'rgba(67, 233, 123, 0.1)';
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.borderColor = '#667eea';
                dropZone.style.background = 'rgba(102, 126, 234, 0.05)';
            }, false);
        });
        
        // Handle dropped files
        dropZone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                updateFileInfo(files[0]);
            }
        }
        
        // Click to select file
        dropZone.addEventListener('click', () => {
            fileInput.click();
        });
        
        // File input change
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                updateFileInfo(fileInput.files[0]);
            }
        });
        
        // Update file info display
        function updateFileInfo(file) {
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.style.display = 'block';
            fileLabel.textContent = 'File Siap Diproses';
        }
        
        // Format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // Form submission
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            if (!fileInput.files.length) {
                e.preventDefault();
                alert('Silakan pilih file PDF terlebih dahulu!');
                return;
            }
            
            convertBtn.disabled = true;
            convertBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Memproses...';
        });
        
        // Auto logout warning
        window.addEventListener('beforeunload', function() {
            // Show warning if session is still active
            if (sessionTime > 0) {
                return 'Session Anda masih aktif. Yakin ingin meninggalkan halaman?';
            }
        });
        
        // Session activity reset
        let activityTimeout;
        function resetActivityTimer() {
            clearTimeout(activityTimeout);
            activityTimeout = setTimeout(function() {
                fetch("{{ url_for('keep_alive') }}")
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            console.log('Session refreshed');
                        }
                    });
            }, 60000); // Ping server setiap 1 menit
        }
        
        // Reset timer on user activity
        document.addEventListener('mousemove', resetActivityTimer);
        document.addEventListener('keypress', resetActivityTimer);
        
        // Initial reset
        resetActivityTimer();
    </script>
</body>
</html>
"""

@app.before_request
def check_session():
    """Middleware untuk memeriksa session sebelum setiap request"""
    if request.endpoint in ['login', 'static']:
        return
    
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Check session timeout
    if 'last_activity' in session:
        time_since_last_activity = pd.Timestamp.now().timestamp() - session['last_activity']
        if time_since_last_activity > SESSION_TIMEOUT:
            session.clear()
            return redirect(url_for('login'))
    
    # Update last activity time
    session['last_activity'] = pd.Timestamp.now().timestamp()

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Halaman login dengan PIN"""
    if 'logged_in' in session:
        return redirect(url_for('upload_file'))
    
    if request.method == 'POST':
        pin = request.form.get('pin', '')
        
        # Check PIN (default: 1234)
        if check_password_hash(DEFAULT_PIN_HASH, pin):
            session['logged_in'] = True
            session['user'] = 'demo_user'
            session['session_id'] = secrets.token_hex(8)
            session['last_activity'] = pd.Timestamp.now().timestamp()
            session.permanent = True
            
            return redirect(url_for('upload_file'))
        else:
            flash('PIN salah. Coba lagi.', 'error')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))

@app.route('/keep_alive')
def keep_alive():
    """Endpoint untuk menjaga session tetap hidup"""
    if 'logged_in' in session:
        session['last_activity'] = pd.Timestamp.now().timestamp()
        return {'success': True, 'message': 'Session refreshed'}
    return {'success': False, 'message': 'Not logged in'}

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Halaman utama converter (hanya bisa diakses setelah login)"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    message = None
    download_link = None
    preview_data = None
    preview_count = 0
    
    if request.method == 'POST':
        if 'file' not in request.files:
            message = "Error: File tidak ditemukan."
        else:
            file = request.files['file']
            if file.filename == '':
                message = "Pilih file terlebih dahulu."
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(pdf_path)
                
                base_name = os.path.splitext(filename)[0]
                csv_filename = f"FPK_{base_name}_{session['session_id']}.csv"
                csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)

                try:
                    clean_fpk_data(pdf_path, csv_path)
                    
                    # Baca file CSV untuk preview
                    df_preview = pd.read_csv(csv_path, dtype={'No.SEP': str, 'Disetujui': str})
                    preview_count = len(df_preview)
                    
                    # Format data untuk preview
                    preview_data = []
                    for _, row in df_preview.head(10).iterrows():
                        preview_data.append({
                            'no_sep': row['No.SEP'],
                            'di_setujui': f"{int(row['Disetujui']):,}".replace(',', '.') if row['Disetujui'].isdigit() else row['Disetujui']
                        })
                    
                    # Hapus file PDF setelah berhasil dikonversi
                    os.remove(pdf_path)
                    
                    message = f"Konversi Berhasil! {preview_count} data diekstrak."
                    download_link = f"/download/{csv_filename}"
                    
                except Exception as e:
                    # Hapus file PDF jika gagal
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    
                    # Hapus file CSV jika gagal
                    if os.path.exists(csv_path):
                        os.remove(csv_path)
                    
                    error_message = str(e).replace('\'', '')
                    print(f"Konversi Gagal: {error_message}")
                    message = f"Gagal Konversi Data FPK: {error_message}"
            else:
                message = "Format file harus PDF."
    
    # Calculate remaining session time
    if 'last_activity' in session:
        remaining_time = SESSION_TIMEOUT - (pd.Timestamp.now().timestamp() - session['last_activity'])
        remaining_time = max(0, int(remaining_time))
    else:
        remaining_time = SESSION_TIMEOUT
    
    return render_template_string(
        HTML_TEMPLATE, 
        message=message, 
        download_link=download_link,
        preview_data=preview_data,
        preview_count=preview_count,
        session_id=session.get('session_id', 'N/A'),
        session_time=remaining_time,
        session_timeout=SESSION_TIMEOUT
    )

@app.route('/download/<filename>')
def download_file(filename):
    """Rute untuk mengunduh file yang sudah dikonversi."""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Verify session ID in filename
    session_id = session.get('session_id', '')
    if session_id and session_id in filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            # Update session activity
            session['last_activity'] = pd.Timestamp.now().timestamp()
            
            # Send file and schedule deletion after download
            response = send_file(file_path, as_attachment=True)
            
            # Schedule file deletion after 5 minutes
            import threading
            from time import sleep
            
            def delete_file(path):
                sleep(300)  # 5 minutes
                if os.path.exists(path):
                    os.remove(path)
                    print(f"Deleted: {path}")
            
            threading.Thread(target=delete_file, args=(file_path,)).start()
            
            return response
    
    return "Error: File tidak ditemukan atau akses ditolak.", 404

if __name__ == '__main__':
    # Generate new secret key on startup
    print("=" * 50)
    print("FPK PDF Converter dengan Sistem Login")
    print("=" * 50)
    print(f"Login URL: http://localhost:5001/login")
    print(f"Default PIN: 1234")
    print(f"Session Timeout: {SESSION_TIMEOUT//60} menit")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)