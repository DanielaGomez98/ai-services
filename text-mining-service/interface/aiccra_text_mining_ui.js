class AICCRATextMiningUI {
    constructor() {
        this.apiBaseUrl = 'https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws';
        // this.apiBaseUrl = 'http://localhost:8000';
        this.bucket = 'ai-services-ibd';
        this.projectType = 'AICCRA';
        this.folderPath = 'aiccra/text-mining/files/test/';
        this.lastResult = null;
        this.searchTimeout = null;
        
        this.defaultPlaceholderPrompt = null;
        
        this.init();
    }

    init() {
        this.createHTML();
        this.bindEvents();
    }

    createHTML() {
        document.body.innerHTML = `
            <div class="app">
                <!-- Header -->
                <header class="header">
                    <div class="container">
                        <div class="logo">
                            <span class="logo-icon">🧠</span>
                            <h1>AICCRA Text Mining</h1>
                        </div>
                        <div class="subtitle">Extract insights from your documents using AI</div>
                    </div>
                </header>

                <!-- Main Content -->
                <main class="main">
                    <div class="container">
                        <!-- AI Warning Banner -->
                        <div class="ai-warning">
                            <div class="warning-icon">⚠️</div>
                            <div class="warning-text">
                                This service uses AI to analyze documents. Results should be validated before use in decision-making.
                            </div>
                        </div>

                        <!-- Settings Card -->
                        <div class="card settings-card">
                            <div class="card-header">
                                <span class="icon">⚙️</span>
                                <h3>Configuration</h3>
                            </div>
                            <div class="card-body">
                                <div class="input-group">
                                    <label for="userEmail">Email Address</label>
                                    <input type="email" id="userEmail" placeholder="your@email.com" />
                                </div>
                                <div class="input-group">
                                    <label for="customPrompt">Analysis Prompt Configuration</label>
                                    
                                    <!-- Prompt Mode Selector -->
                                    <div class="prompt-mode-selector">
                                        <div class="radio-tabs" style="margin-bottom: 1rem;">
                                            <input type="radio" name="promptMode" value="default" id="default-prompt-tab" checked>
                                            <label for="default-prompt-tab" class="tab-button">
                                                <span class="tab-icon">🔧</span>
                                                Default Prompt
                                            </label>
                                            
                                            <input type="radio" name="promptMode" value="custom" id="custom-prompt-tab">
                                            <label for="custom-prompt-tab" class="tab-button">
                                                <span class="tab-icon">✏️</span>
                                                Custom Prompt
                                            </label>
                                        </div>
                                    </div>

                                    <!-- Default Prompt Info -->
                                    <div id="defaultPromptSection" class="prompt-section">
                                        <div class="input-hint">
                                            📝 Using the standard AICCRA prompt for document analysis. This prompt is optimized for extracting climate adaptation and agriculture-related information.
                                        </div>
                                    </div>

                                    <!-- Custom Prompt Section -->
                                    <div id="customPromptSection" class="prompt-section" style="display: none;">
                                        <div class="custom-prompt-controls">
                                            <button type="button" id="loadPlaceholderBtn" class="btn-secondary" style="width: auto; margin-bottom: 1rem;">
                                                <span class="btn-icon">�</span>
                                                Load Template
                                            </button>
                                            <button type="button" id="downloadPromptBtn" class="btn-secondary" style="width: auto; margin-bottom: 1rem; margin-left: 0.5rem;">
                                                <span class="btn-icon">�</span>
                                                Download Prompt
                                            </button>
                                        </div>
                                        
                                        <textarea id="customPrompt" rows="12" placeholder="Enter your custom prompt here or click 'Load Template' to start with the default AICCRA prompt..."></textarea>
                                        
                                        <div class="input-hint">
                                            🎯 <strong>Tips:</strong><br/>
                                            • Click "Load Template" to start with the default AICCRA prompt<br/>
                                            • Edit the prompt to customize how the AI analyzes your document<br/>
                                            • Click "Download Prompt" to save your customized prompt as a .txt file
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Document Source Card -->
                        <div class="card">
                            <div class="card-header">
                                <span class="icon">📄</span>
                                <h3>Document Source</h3>
                            </div>
                            <div class="card-body">
                                <div class="radio-tabs">
                                    <input type="radio" name="mode" value="upload" id="upload-tab" checked>
                                    <label for="upload-tab" class="tab-button">
                                        <span class="tab-icon">⬆️</span>
                                        Upload File
                                    </label>
                                    
                                    <input type="radio" name="mode" value="s3" id="s3-tab">
                                    <label for="s3-tab" class="tab-button">
                                        <span class="tab-icon">☁️</span>
                                        From S3
                                    </label>
                                </div>

                                <!-- Upload Section -->
                                <div id="uploadSection" class="tab-content">
                                    <div class="file-upload-area" id="fileUploadArea">
                                        <div class="upload-icon">📁</div>
                                        <div class="upload-text">
                                            <p>Drag & drop your file here</p>
                                            <p class="upload-subtext">or click to browse</p>
                                        </div>
                                        <input type="file" id="fileInput" accept=".pdf,.docx,.txt,.xlsx,.xls,.pptx" />
                                    </div>
                                    <div class="file-types">
                                        Supported: PDF, DOCX, TXT, XLSX, XLS, PPTX
                                    </div>
                                    <div id="uploadInfo" class="upload-info" style="display:none;"></div>
                                </div>

                                <!-- S3 Section -->
                                <div id="s3Section" class="tab-content" style="display:none;">
                                    <div class="input-group">
                                        <label for="additionalPrefix">Additional Path (optional)</label>
                                        <input type="text" id="additionalPrefix" placeholder="subfolder/" />
                                        <div class="input-hint" id="searchInfo"></div>
                                    </div>
                                    
                                    <div class="s3-controls">
                                        <button id="refreshBtn" class="btn-secondary">
                                            <span class="btn-icon">🔄</span>
                                            Refresh
                                        </button>
                                    </div>

                                    <div class="input-group">
                                        <label for="s3Select">Select File</label>
                                        <select id="s3Select" disabled>
                                            <option>Loading...</option>
                                        </select>
                                    </div>
                                </div>

                                <!-- Process Button -->
                                <div class="process-section">
                                    <button id="processBtn" class="btn-primary">
                                        <span class="btn-icon">🚀</span>
                                        Process Document
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Loading -->
                        <div id="loading" class="loading-card" style="display:none;">
                            <div class="loading-content">
                                <div class="spinner"></div>
                                <h3>Processing Document</h3>
                                <p>Analyzing your document with AI...</p>
                            </div>
                        </div>

                        <!-- Results -->
                        <div id="results" class="results-section" style="display:none;">
                            <div class="card success-card">
                                <div id="successMessage" class="success-message"></div>
                            </div>

                            <div class="card">
                                <div class="card-header expandable-header" data-target="rawJson">
                                    <div class="header-left">
                                        <span class="icon">🔍</span>
                                        <h3>Raw JSON Output</h3>
                                    </div>
                                    <span class="expand-icon">+</span>
                                </div>
                                <div id="rawJson" class="card-body expandable-content" style="display:none;">
                                    <pre id="jsonContent" class="json-output"></pre>
                                </div>
                            </div>

                            <div id="processedResults"></div>
                        </div>

                        <!-- Error -->
                        <div id="error" class="error-card" style="display:none;">
                            <div class="error-icon">❌</div>
                            <div class="error-message"></div>
                        </div>
                    </div>
                </main>
            </div>
        `;

        const style = document.createElement('style');
        style.textContent = `
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #f8fafc;
                min-height: 100vh;
                color: #333;
                line-height: 1.6;
            }

            .app {
                min-height: 100vh;
            }

            .container {
                width: 65%;
                margin: 0 auto;
                padding: 0 20px;
            }

            /* Header */
            .header {
                background: #1079A4;
                padding: 2rem 0;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }

            .logo {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 1rem;
                margin-bottom: 0.5rem;
            }

            .logo-icon {
                font-size: 2.5rem;
            }

            .logo h1 {
                font-size: 2.5rem;
                font-weight: 700;
                color: white;
                text-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }

            .subtitle {
                color: rgba(255, 255, 255, 0.95);
                font-size: 1.1rem;
                font-weight: 300;
            }

            /* Main Content */
            .main {
                padding: 2rem 0 4rem;
                background: white;
            }

            /* Cards */
            .card {
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                margin-bottom: 1.5rem;
                overflow: hidden;
                border: 1px solid #e2e8f0;
            }

            .card-header {
                padding: 1rem 1.5rem;
                border-bottom: 1px solid #e2e8f0;
                display: flex;
                align-items: center;
                gap: 0.75rem;
                cursor: pointer;
                background: #f8fafc;
            }

            .expandable-header {
                justify-content: space-between;
            }

            .header-left {
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }

            .card-header h3 {
                font-size: 1.25rem;
                font-weight: 600;
                color: #2d3748;
            }

            .icon {
                font-size: 1.25rem;
            }

            .expand-icon {
                font-size: 1.5rem;
                font-weight: bold;
                color: #1079A4;
                transition: transform 0.2s ease;
            }

            .card-body {
                padding: 1.5rem;
                background: white;
            }

            /* AI Warning */
            .ai-warning {
                background: #f9fda7ff;
                border: 1px solid #dcb700ff;
                border-radius: 8px;
                padding: 1rem 1.5rem;
                margin-bottom: 1.5rem;
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .warning-icon {
                font-size: 1.5rem;
                flex-shrink: 0;
            }

            .warning-text {
                color: #101010ff;
                font-weight: 500;
            }

            /* Input Groups */
            .input-group {
                margin-bottom: 1.5rem;
            }

            .input-group label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 600;
                color: #4a5568;
                font-size: 0.95rem;
            }

            .input-group input,
            .input-group select,
            .input-group textarea {
                width: 100%;
                padding: 0.75rem 1rem;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 1rem;
                transition: all 0.2s ease;
                background: white;
                font-family: inherit;
                resize: vertical;
            }

            .input-group input:focus,
            .input-group select:focus,
            .input-group textarea:focus {
                outline: none;
                border-color: #1079A4;
                box-shadow: 0 0 0 3px rgba(16, 121, 164, 0.1);
            }

            /* Placeholder styles */
            .input-group input::placeholder,
            .input-group textarea::placeholder {
                color: #ced1d6ff;
                opacity: 1;
                font-style: italic;
            }

            .input-hint {
                margin-top: 0.5rem;
                font-size: 0.875rem;
                color: #718096;
                background: #fcf7f7ff;
                padding: 0.5rem;
                border-radius: 6px;
            }

            /* Radio Tabs */
            .radio-tabs {
                display: flex;
                background: #E7F4FF;
                border-radius: 6px;
                padding: 3px;
                margin-bottom: 1.5rem;
                border: 1px solid #81B8C1;
            }

            .radio-tabs input[type="radio"] {
                display: none;
            }

            .tab-button {
                flex: 1;
                padding: 0.5rem 1rem;
                text-align: center;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s ease;
                font-weight: 500;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                color: #1079A4;
            }

            .radio-tabs input[type="radio"]:checked + .tab-button {
                background: white;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                color: #1079A4;
            }

            .tab-icon {
                font-size: 1.1rem;
            }

            /* File Upload */
            .file-upload-area {
                border: 2px dashed #81B8C1;
                border-radius: 8px;
                padding: 2rem;
                text-align: center;
                transition: all 0.2s ease;
                cursor: pointer;
                position: relative;
                background: #fafbfc;
            }

            .file-upload-area:hover {
                border-color: #1079A4;
                background: #E7F4FF;
            }

            .file-upload-area.dragover {
                border-color: #8CBF3F;
                background: #f0fff4;
                transform: scale(1.02);
            }

            .upload-icon {
                font-size: 2.5rem;
                margin-bottom: 0.75rem;
                color: #81B8C1;
            }

            .upload-text p {
                font-size: 1.1rem;
                color: #4a5568;
                margin-bottom: 0.5rem;
            }

            .upload-subtext {
                color: #718096 !important;
                font-size: 0.9rem !important;
            }

            .file-upload-area input[type="file"] {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
            }

            .file-types {
                margin-top: 1rem;
                text-align: center;
                font-size: 0.875rem;
                color: #718096;
            }

            .upload-info {
                margin-top: 1rem;
                padding: 0.75rem 1rem;
                background: #E7F4FF;
                border: 1px solid #81B8C1;
                border-radius: 6px;
                color: #1079A4;
                font-size: 0.9rem;
            }

            /* Buttons */
            .btn-primary {
                background: #1079A4;
                color: white;
                border: none;
                padding: 0.875rem 2rem;
                border-radius: 6px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                width: 100%;
            }

            .btn-primary:hover {
                background: #0d6b8a;
                transform: translateY(-1px);
            }

            .btn-secondary {
                background: white;
                color: #1079A4;
                border: 2px solid #1079A4;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .btn-secondary:hover {
                background: #1079A4;
                color: white;
            }

            .btn-icon {
                font-size: 1.1rem;
            }

            .process-section {
                margin-top: 1.5rem;
                padding-top: 1.5rem;
                border-top: 1px solid #e2e8f0;
            }

            .s3-controls {
                margin-bottom: 1.5rem;
            }

            /* Loading */
            .loading-card {
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                padding: 2rem;
                text-align: center;
            }

            .loading-content h3 {
                margin: 1rem 0 0.5rem;
                color: #2d3748;
                font-size: 1.5rem;
            }

            .loading-content p {
                color: #718096;
                font-size: 1.1rem;
            }

            .spinner {
                width: 50px;
                height: 50px;
                border: 4px solid #E7F4FF;
                border-top: 4px solid #1079A4;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            /* Results */
            .success-card {
                background: linear-gradient(135deg, #8CBF3F 0%, #a8d158 100%);
                border: none;
            }

            .success-message {
                color: white;
                font-weight: 600;
                font-size: 1.1rem;
                text-align: center;
                padding: 0.5rem;
            }

            .json-output {
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 8px;
                overflow-x: auto;
                font-size: 0.9rem;
                border: 1px solid #e9ecef;
            }

            .result-item {
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
                margin-bottom: 1.5rem;
                overflow: hidden;
                border: 1px solid #e2e8f0;
            }

            .result-item h4 {
                background: linear-gradient(135deg, #1079A4 0%, #81B8C1 100%);
                color: white;
                padding: 1rem 1.5rem;
                margin: 0;
                font-size: 1.2rem;
            }

            .result-field {
                padding: 0.75rem 1.5rem;
                border-bottom: 1px solid #f0f0f0;
            }

            .result-field:last-child {
                border-bottom: none;
            }

            .result-field strong {
                color: #2d3748;
                display: inline-block;
                min-width: 140px;
                font-weight: 600;
            }

            .result-table {
                margin-top: 0.5rem;
            }

            .result-table table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
                background: white;
                border-radius: 6px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }

            .result-table th {
                background: #f7fafc;
                padding: 0.75rem;
                text-align: left;
                font-weight: 600;
                color: #4a5568;
                border-bottom: 2px solid #e2e8f0;
            }

            .result-table td {
                padding: 0.75rem;
                border-bottom: 1px solid #e2e8f0;
            }

            .result-table tr:last-child td {
                border-bottom: none;
            }

            /* Error */
            .error-card {
                background: linear-gradient(135deg, #DA5350 0%, #f56565 100%);
                border-radius: 12px;
                padding: 1.5rem;
                display: flex;
                align-items: center;
                gap: 1rem;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            }

            .error-icon {
                font-size: 1.5rem;
                flex-shrink: 0;
                color: white;
            }

            .error-message {
                color: white;
                font-weight: 500;
                font-size: 1.1rem;
            }

            /* Responsive */
            @media (max-width: 1200px) {
                .container {
                    width: 85%;
                }
            }

            @media (max-width: 768px) {
                .container {
                    width: 95%;
                    padding: 0 1rem;
                }

                .logo h1 {
                    font-size: 2rem;
                }

                .card-body {
                    padding: 1rem;
                }

                .file-upload-area {
                    padding: 2rem 1rem;
                }

                .upload-icon {
                    font-size: 2rem;
                }
            }

            /* Animations */
            .card {
                animation: slideUp 0.3s ease-out;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .expandable-content {
                transition: all 0.3s ease;
            }

            .settings-card {
                background: #E7F4FF;
                border: 1px solid #81B8C1;
            }

            /* Prompt Mode Styles */
            .prompt-mode-selector {
                margin-bottom: 1rem;
            }

            .prompt-section {
                transition: all 0.3s ease;
            }

            .custom-prompt-controls {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-bottom: 1rem;
            }

            .btn-secondary:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                background: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }

            .btn-secondary:disabled:hover {
                background: #f8f9fa;
                color: #6c757d;
                transform: none;
            }

            .save-prompt-section {
                background: #f8fafc;
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                margin-top: 1rem;
                display: none;
            }

            #customPrompt {
                min-height: 200px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 0.9rem;
                line-height: 1.4;
            }

            /* Free-form response styles */
            .free-form-response {
                margin-bottom: 1rem;
            }

            .free-form-content p {
                margin-bottom: 1rem;
            }

            .free-form-content p:last-child {
                margin-bottom: 0;
            }

            .free-form-content strong {
                color: #1079A4;
                font-weight: 600;
            }

            .free-form-content em {
                color: #6b7280;
                font-style: italic;
            }

            .response-note {
                display: flex;
                align-items: flex-start;
                gap: 0.5rem;
            }
        `;
        document.head.appendChild(style);
    }

    bindEvents() {
        // Mode switching
        document.querySelectorAll('input[name="mode"]').forEach(radio => {
            radio.addEventListener('change', () => this.handleModeChange());
        });

        // File input and drag & drop
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('fileUploadArea');

        fileInput.addEventListener('change', () => this.handleFileChange());

        // Drag and drop events
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                this.handleFileChange();
            }
        });

        // Process button
        document.getElementById('processBtn').addEventListener('click', () => this.processDocument());

        // Expandable sections
        document.addEventListener('click', (e) => {
            if (e.target.closest('.expandable-header')) {
                this.toggleExpandable(e.target.closest('.expandable-header'));
            }
        });

        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => this.loadS3Objects());

        // Additional prefix input
        document.getElementById('additionalPrefix').addEventListener('input', () => this.updateSearchInfo());

        // Prompt mode switching
        document.querySelectorAll('input[name="promptMode"]').forEach(radio => {
            radio.addEventListener('change', () => this.handlePromptModeChange());
        });

        // Load placeholder prompt
        document.getElementById('loadPlaceholderBtn').addEventListener('click', () => this.loadPlaceholderPrompt());

        // Download custom prompt
        document.getElementById('downloadPromptBtn').addEventListener('click', () => this.downloadPrompt());

        // Custom prompt changes
        document.getElementById('customPrompt').addEventListener('input', () => this.handleCustomPromptChange());

        // Initial setup
        this.handleModeChange();
        this.updateSearchInfo();
        this.handlePromptModeChange();
    }

    handleModeChange() {
        const mode = document.querySelector('input[name="mode"]:checked').value;
        const uploadSection = document.getElementById('uploadSection');
        const s3Section = document.getElementById('s3Section');

        if (mode === 'upload') {
            uploadSection.style.display = 'block';
            s3Section.style.display = 'none';
        } else {
            uploadSection.style.display = 'none';
            s3Section.style.display = 'block';
            this.loadS3Objects();
        }
    }

    handleFileChange() {
        const fileInput = document.getElementById('fileInput');
        const uploadInfo = document.getElementById('uploadInfo');
        const uploadArea = document.getElementById('fileUploadArea');
        
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            uploadInfo.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.2rem;">📁</span>
                    <strong>Selected:</strong> ${file.name}
                </div>
                <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #666;">
                    Will be uploaded to: <code>${this.bucket}/${this.folderPath}${file.name}</code>
                </div>
            `;
            uploadInfo.style.display = 'block';
            
            uploadArea.style.borderColor = '#8CBF3F';
            uploadArea.style.backgroundColor = '#f0fff4';
        } else {
            uploadInfo.style.display = 'none';
            uploadArea.style.borderColor = '#cbd5e0';
            uploadArea.style.backgroundColor = '#fafafa';
        }
    }

    updateSearchInfo() {
        const additionalPrefix = document.getElementById('additionalPrefix').value;
        const searchInfo = document.getElementById('searchInfo');
        if (additionalPrefix.trim()) {
            searchInfo.innerHTML = `📁 Searching with prefix: <code>${additionalPrefix}</code>`;
        } else {
            searchInfo.innerHTML = `📁 Searching in default folder`;
        }
        
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        this.searchTimeout = setTimeout(() => {
            this.loadS3Objects();
        }, 500);
    }

    handlePromptModeChange() {
        const mode = document.querySelector('input[name="promptMode"]:checked').value;
        const defaultSection = document.getElementById('defaultPromptSection');
        const customSection = document.getElementById('customPromptSection');

        if (mode === 'default') {
            defaultSection.style.display = 'block';
            customSection.style.display = 'none';
        } else {
            defaultSection.style.display = 'none';
            customSection.style.display = 'block';
            // Initialize download button state
            this.handleCustomPromptChange();
        }
    }

    async loadPlaceholderPrompt() {
        const promptTextarea = document.getElementById('customPrompt');
        const loadBtn = document.getElementById('loadPlaceholderBtn');
        
        // Show loading state
        loadBtn.disabled = true;
        loadBtn.innerHTML = '<span class="btn-icon">⏳</span> Loading...';
        
        try {
            // Load prompt from backend if not already loaded
            if (!this.defaultPlaceholderPrompt) {
                const response = await fetch(`${this.apiBaseUrl}/aiccra/prompt`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`Failed to load prompt: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                
                if (data.status === 'success') {
                    this.defaultPlaceholderPrompt = data.content;
                } else {
                    throw new Error(data.message || 'Failed to load prompt');
                }
            }
            
            // Set the prompt in the textarea
            promptTextarea.value = this.defaultPlaceholderPrompt;
            this.showInfo('✅ Template prompt loaded successfully! You can now edit it as needed.');
            
        } catch (error) {
            console.error('Error loading prompt:', error);
            this.showError('❌ Could not load prompt from backend. Please check your connection and try again.');
        } finally {
            // Reset button state
            loadBtn.disabled = false;
            loadBtn.innerHTML = '<span class="btn-icon">📋</span> Load Template';
        }
    }

    downloadPrompt() {
        const promptContent = document.getElementById('customPrompt').value.trim();
        
        if (!promptContent) {
            this.showError('❌ No prompt content to download. Please enter some text first.');
            return;
        }

        try {
            // Create a timestamp for the filename
            const now = new Date();
            const timestamp = now.toISOString().slice(0, 19).replace(/[T:]/g, '-');
            const filename = `aiccra-custom-prompt-${timestamp}.txt`;

            // Create blob and download
            const blob = new Blob([promptContent], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            
            // Create download link
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.style.display = 'none';
            
            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Clean up
            window.URL.revokeObjectURL(url);
            
            this.showInfo(`💾 Prompt downloaded as "${filename}"`);
            
        } catch (error) {
            console.error('Error downloading prompt:', error);
            this.showError('❌ Error downloading prompt. Please try again.');
        }
    }

    handleCustomPromptChange() {
        const promptContent = document.getElementById('customPrompt').value.trim();
        const downloadBtn = document.getElementById('downloadPromptBtn');
        
        // Enable/disable download button based on content
        downloadBtn.disabled = !promptContent;
        downloadBtn.style.opacity = promptContent ? '1' : '0.6';
    }

    showInfo(message) {
        // Create a temporary info message
        const infoDiv = document.createElement('div');
        infoDiv.className = 'info-message';
        infoDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #8CBF3F;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            font-weight: 500;
            max-width: 400px;
        `;
        infoDiv.textContent = message;
        document.body.appendChild(infoDiv);

        // Remove after 5 seconds
        setTimeout(() => {
            if (infoDiv.parentNode) {
                infoDiv.parentNode.removeChild(infoDiv);
            }
        }, 5000);
    }

    async loadS3Objects() {
        const select = document.getElementById('s3Select');
        const additionalPrefix = document.getElementById('additionalPrefix').value;
        const fullPrefix = this.folderPath + additionalPrefix;

        select.innerHTML = '<option>Loading...</option>';
        select.disabled = true;

        try {
            const response = await fetch(`${this.apiBaseUrl}/list-s3-objects`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    bucket: this.bucket,
                    prefix: fullPrefix,
                    max_items: 1000
                })
            });

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.status === 'error') {
                throw new Error(data.message || 'Failed to list files');
            }

            const objects = data.objects || [];

            select.innerHTML = '';
            select.disabled = false;

            if (objects.length === 0) {
                select.innerHTML = '<option>No files found</option>';
                select.disabled = true;
            } else {
                select.innerHTML = '<option value="">Select a file...</option>';
                objects.forEach(key => {
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = key.split('/').pop();
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading S3 objects:', error);
            select.innerHTML = '<option>Error loading files</option>';
            select.disabled = true;
            
            let errorMessage = `Failed to load S3 objects: ${error.message}`;
            
            if (error.message.includes('NetworkError') || error.message.includes('Network Failure')) {
                errorMessage = 'Network error. Please check your internet connection and try again.';
            } else if (error.message.includes('CORS')) {
                errorMessage = 'CORS error. The API may need to be configured to allow browser requests.';
            }
            
            this.showError(errorMessage);
        }
    }

    async processDocument() {
        const email = document.getElementById('userEmail').value.trim();
        if (!email) {
            this.showError('Please provide your email address.');
            return;
        }

        const promptMode = document.querySelector('input[name="promptMode"]:checked').value;
        let customPrompt = '';

        if (promptMode === 'custom') {
            customPrompt = document.getElementById('customPrompt').value.trim();
            
            if (!customPrompt) {
                this.showError('Please enter a custom prompt or switch to default mode.');
                return;
            }
        }

        const mode = document.querySelector('input[name="mode"]:checked').value;

        if (mode === 'upload') {
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files.length) {
                this.showError('Please select a file to upload.');
                return;
            }
            
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            formData.append('bucketName', this.bucket);
            formData.append('user_id', email);
            
            // Add custom prompt if provided
            if (customPrompt) {
                formData.append('prompt', customPrompt);
            }
            
            this.showLoading(true);
            this.hideError();
            this.hideResults();

            try {
                const startTime = Date.now();
                const response = await this.callAPI(formData);
                const elapsed = (Date.now() - startTime) / 1000;

                if (response.status === 'error' || response.isError) {
                    throw new Error(response.error || response.message || 'Unknown error occurred');
                }

                this.lastResult = response;
                this.showResults(response, elapsed);
            } catch (error) {
                this.showError(error.message);
            } finally {
                this.showLoading(false);
            }
        } else {
            const selectedKey = document.getElementById('s3Select').value;
            if (!selectedKey) {
                this.showError('Please select a file from S3.');
                return;
            }
            
            const formData = new FormData();
            formData.append('bucketName', this.bucket);
            formData.append('user_id', email);
            formData.append('key', selectedKey);
            
            // Add custom prompt if provided
            if (customPrompt) {
                formData.append('prompt', customPrompt);
            }

            this.showLoading(true);
            this.hideError();
            this.hideResults();

            try {
                const startTime = Date.now();
                const response = await this.callAPI(formData);
                const elapsed = (Date.now() - startTime) / 1000;

                if (response.status === 'error' || response.isError) {
                    throw new Error(response.error || response.message || 'Unknown error occurred');
                }

                this.lastResult = response;
                this.showResults(response, elapsed);
            } catch (error) {
                this.showError(error.message);
            } finally {
                this.showLoading(false);
            }
        }
    }

    async callAPI(formData) {
        const url = `${this.apiBaseUrl}/aiccra/text-mining`;
        
        const options = {
            method: 'POST',
            body: formData
        };

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`API error ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    showLoading(show) {
        document.getElementById('loading').style.display = show ? 'block' : 'none';
    }

    showError(message) {
        const errorDiv = document.getElementById('error');
        const errorMessage = errorDiv.querySelector('.error-message');
        errorMessage.textContent = message;
        errorDiv.style.display = 'block';
        
        // Scroll to error
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    hideError() {
        document.getElementById('error').style.display = 'none';
    }

    hideResults() {
        document.getElementById('results').style.display = 'none';
    }

    showResults(result, elapsed) {
        const resultsDiv = document.getElementById('results');
        const successDiv = document.getElementById('successMessage');
        const jsonContent = document.getElementById('jsonContent');
        const processedResults = document.getElementById('processedResults');

        successDiv.innerHTML = `
            <span style="font-size: 1.2rem;">✅</span>
            Processing completed successfully! 
            <span style="font-weight: normal;">⏱️ ${elapsed.toFixed(2)}s</span>
        `;
        jsonContent.textContent = JSON.stringify(result, null, 2);

        // Extract and display structured results
        const extractedResults = this.extractResults(result);
        processedResults.innerHTML = this.renderStructuredResults(extractedResults);

        resultsDiv.style.display = 'block';
        
        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    extractResults(result) {
        // First, check if we already have a structured results format
        if (result.results) return result;
        
        const content = result.content;
        if (Array.isArray(content)) {
            for (const item of content) {
                if (item.text) {
                    try {
                        // Try to parse the text as JSON first
                        const parsed = JSON.parse(item.text);
                        if (parsed.results) return parsed;
                        if (parsed.json_content && parsed.json_content.results) return parsed.json_content;
                        
                        // Check if there's a nested json_content with text
                        if (parsed.json_content && parsed.json_content.text) {
                            // This is likely a free-form response, not structured JSON
                            return {
                                results: [],
                                freeFormResponse: parsed.json_content.text,
                                interactionId: parsed.interaction_id
                            };
                        }
                    } catch (e) {
                        // If JSON parsing fails, treat as free-form text
                        return {
                            results: [],
                            freeFormResponse: item.text,
                            rawContent: item
                        };
                    }
                }
            }
        }
        
        // If no content found, return empty structure
        return { results: [] };
    }

    renderStructuredResults(data) {
        const results = data.results || [];
        
        // Check if we have a free-form response (when custom prompt is used)
        if (data.freeFormResponse && results.length === 0) {
            return `
                <div class="card">
                    <div class="card-header">
                        <span class="icon">💬</span>
                        <h3>AI Analysis Response</h3>
                        <span style="background: #8CBF3F; color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.875rem; font-weight: 600;">
                            Custom Prompt
                        </span>
                    </div>
                    <div class="card-body">
                        <div class="free-form-response">
                            ${this.renderFreeFormResponse(data.freeFormResponse)}
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Standard structured results display
        if (results.length === 0) {
            return `
                <div class="card">
                    <div class="card-body" style="text-align: center; padding: 3rem;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
                        <h3 style="color: #718096; margin-bottom: 0.5rem;">No Results Found</h3>
                        <p style="color: #a0aec0;">The document was processed but no structured data was extracted.</p>
                        <div class="input-hint" style="margin-top: 1rem;">
                            💡 <strong>Tip:</strong> Try using the "Load Template" option in Custom Prompt mode for structured data extraction.
                        </div>
                    </div>
                </div>
            `;
        }

        let html = `
            <div class="card">
                <div class="card-header">
                    <span class="icon">📊</span>
                    <h3>Extracted Results</h3>
                    <span style="background: #1079A4; color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.875rem; font-weight: 600;">
                        ${results.length} found
                    </span>
                </div>
                <div class="card-body" style="padding: 0;">
        `;

        results.forEach((result, index) => {
            html += `<div class="result-item">
                <h4>📊 Result ${index + 1}</h4>
                <div style="padding: 0;">
                    ${this.renderResultFields(result)}
                </div>
            </div>`;
        });

        html += `</div></div>`;
        return html;
    }

    renderResultFields(result) {
        const fieldMapping = {
            "indicator": "Indicator",
            "title": "Result title",
            "short_title": "Short result title",
            "description": "Description",
            "main_contact_person": "Main contact person",
            "keywords": "Keywords",
            "geoscope_level": "Geoscope level",
            "regions": "Regions codes",
            "countries": "Countries codes",
            "innovation_nature": "Innovation nature",
            "innovation_type": "Innovation type",
            "assess_readiness": "Readiness level",
            "anticipated_users": "Anticipated users",
            "innovation_actors_detailed": "Actors",
            "organizations_detailed": "Organizations"
        };

        let html = '';
        for (const [field, label] of Object.entries(fieldMapping)) {
            const value = result[field];
            if (value !== undefined && value !== null && value !== '') {
                html += this.renderField(field, label, value);
            }
        }
        return html || '<div class="result-field" style="color: #a0aec0; font-style: italic;">No data available</div>';
    }

    renderField(field, label, value) {
        if (field === 'keywords' && Array.isArray(value)) {
            const keywords = value.map(k => `<span style="background: #E7F4FF; color: #1079A4; padding: 0.25rem 0.5rem; border-radius: 15px; font-size: 0.875rem; margin-right: 0.5rem; display: inline-block; margin-bottom: 0.25rem; border: 1px solid #81B8C1;">${k}</span>`).join('');
            return `<div class="result-field"><strong>${label}:</strong><br/><div style="margin-top: 0.5rem;">${keywords}</div></div>`;
        } else if ((field === 'innovation_actors_detailed' || field === 'organizations_detailed') && Array.isArray(value)) {
            return `<div class="result-field">
                <strong>${label}:</strong>
                <div class="result-table" style="margin-top: 0.75rem;">${this.renderTable(value, field)}</div>
            </div>`;
        } else if (typeof value === 'object') {
            return `<div class="result-field"><strong>${label}:</strong><br/><pre style="margin-top: 0.5rem; background: #f7fafc; padding: 1rem; border-radius: 6px; font-size: 0.875rem; white-space: pre-wrap;">${JSON.stringify(value, null, 2)}</pre></div>`;
        } else {
            return `<div class="result-field"><strong>${label}:</strong> ${value}</div>`;
        }
    }

    renderFreeFormResponse(response) {
        // Clean up the response text
        let cleanResponse = response;
        
        // Remove common markdown-like patterns if present
        cleanResponse = cleanResponse.replace(/```[\s\S]*?```/g, ''); // Remove code blocks
        cleanResponse = cleanResponse.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Bold text
        cleanResponse = cleanResponse.replace(/\*(.*?)\*/g, '<em>$1</em>'); // Italic text
        
        // Convert line breaks to HTML
        cleanResponse = cleanResponse.replace(/\n\n/g, '</p><p>');
        cleanResponse = cleanResponse.replace(/\n/g, '<br>');
        
        // Wrap in paragraphs if not already wrapped
        if (!cleanResponse.includes('<p>')) {
            cleanResponse = `<p>${cleanResponse}</p>`;
        }
        
        return `
            <div class="free-form-content" style="
                line-height: 1.6; 
                color: #374151; 
                font-size: 1rem;
                background: #f9fafb;
                padding: 1.5rem;
                border-radius: 8px;
                border-left: 4px solid #8CBF3F;
            ">
                ${cleanResponse}
            </div>
            <div class="response-note" style="
                margin-top: 1rem; 
                padding: 0.75rem; 
                background: #e7f4ff; 
                border-radius: 6px; 
                font-size: 0.875rem; 
                color: #1079A4;
                border: 1px solid #81B8C1;
            ">
                <strong>📝 Note:</strong> This is a free-form AI response based on your custom prompt. 
                For structured data extraction, use the "Load Template" option in Custom Prompt mode.
            </div>
        `;
    }

    renderTable(data, type) {
        if (!Array.isArray(data) || data.length === 0) {
            return '<p style="color: #a0aec0; font-style: italic; margin: 0.5rem 0;">No data available</p>';
        }

        const columns = type === 'innovation_actors_detailed' 
            ? { name: 'Actor name', type: 'Type', gender_age: 'Gender/Age', other_actor_type: 'Other type' }
            : { name: 'Organization name', type: 'Organization type', sub_type: 'Organization sub-type', other_type: 'Other type' };

        let html = '<table><thead><tr>';
        Object.values(columns).forEach(col => {
            html += `<th>${col}</th>`;
        });
        html += '</tr></thead><tbody>';

        data.forEach(row => {
            html += '<tr>';
            Object.keys(columns).forEach(key => {
                const cellValue = row[key] || '-';
                html += `<td>${cellValue}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        return html;
    }

    toggleExpandable(header) {
        const targetId = header.getAttribute('data-target');
        const content = document.getElementById(targetId);
        const icon = header.querySelector('.expand-icon');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.textContent = '−';
            icon.style.transform = 'rotate(180deg)';
        } else {
            content.style.display = 'none';
            icon.textContent = '+';
            icon.style.transform = 'rotate(0deg)';
        }
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AICCRATextMiningUI();
});