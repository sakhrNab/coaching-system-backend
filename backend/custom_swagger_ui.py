"""
Custom Swagger UI with environment switching
"""
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

def get_custom_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
    swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
    swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    swagger_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
    oauth2_redirect_url: str = None,
    init_oauth: dict = None,
    swagger_ui_parameters: dict = None,
) -> HTMLResponse:
    """
    Generate custom Swagger UI HTML with environment switching
    """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="{swagger_css_url}">
        <link rel="shortcut icon" href="{swagger_favicon_url}">
        <title>{title}</title>
        <style>
            .environment-switcher {{
                position: fixed;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: #fff;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .environment-switcher select {{
                margin-right: 10px;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }}
            .environment-switcher button {{
                padding: 5px 10px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 3px;
                cursor: pointer;
            }}
            .environment-switcher button:hover {{
                background: #0056b3;
            }}
            .current-env {{
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="environment-switcher">
            <select id="env-selector">
                <option value="http://localhost:8001">Development Server</option>
                <option value="https://coach.aiwaverider.com">Production Server</option>
            </select>
            <button onclick="switchEnvironment()">Switch Environment</button>
            <div class="current-env" id="current-env">Current: Development Server</div>
        </div>
        
        <div id="swagger-ui"></div>
        
        <script src="{swagger_js_url}"></script>
        <script>
            let currentEnv = 'http://localhost:8001';
            
            function switchEnvironment() {{
                const selector = document.getElementById('env-selector');
                const newEnv = selector.value;
                currentEnv = newEnv;
                
                // Update current environment display
                const currentEnvDiv = document.getElementById('current-env');
                const envName = selector.options[selector.selectedIndex].text;
                currentEnvDiv.textContent = 'Current: ' + envName;
                
                // Reload Swagger UI with new environment
                loadSwaggerUI();
            }}
            
            function loadSwaggerUI() {{
                const ui = SwaggerUIBundle({{
                    url: currentEnv + '/openapi.json',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout",
                    validatorUrl: null,
                    tryItOutEnabled: true,
                    requestInterceptor: function(request) {{
                        // Update request URL to use current environment
                        if (request.url.startsWith('/')) {{
                            request.url = currentEnv + request.url;
                        }}
                        return request;
                    }}
                }});
            }}
            
            // Load Swagger UI on page load
            window.onload = function() {{
                loadSwaggerUI();
            }};
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

def setup_custom_swagger_routes(app: FastAPI):
    """Setup custom Swagger UI routes with environment switching"""
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_custom_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        from fastapi.openapi.docs import get_redoc_html
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
        )

