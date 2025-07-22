import dash
from dash import dcc, html, Input, Output, State, clientside_callback, ClientsideFunction
import dash_bootstrap_components as dbc
import asyncio
import re
from langchain_core.messages import HumanMessage

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.config.suppress_callback_exceptions = True

# Store for conversation history
conversation_history = []

# Add JavaScript for resizing functionality (unchanged)
# app.index_string = '''
# <!DOCTYPE html>
# <html>
#     <head>
#         {%metas%}
#         <title>{%title%}</title>
#         {%favicon%}
#         {%css%}
#         <script>
#             // Initialize resizer when page loads
#             document.addEventListener('DOMContentLoaded', function() {
#                 let isDragging = false;
#                 let startX = 0;
#                 let startLeftWidth = 0;
                
#                 const resizer = document.getElementById('resizer');
#                 const leftCol = document.getElementById('left-column');
#                 const rightCol = document.getElementById('right-column');
                
#                 if (resizer && leftCol && rightCol) {
#                     resizer.addEventListener('mousedown', function(e) {
#                         isDragging = true;
#                         startX = e.clientX;
#                         startLeftWidth = leftCol.offsetWidth;
#                         document.body.style.cursor = 'col-resize';
#                         e.preventDefault();
#                     });
                    
#                     document.addEventListener('mousemove', function(e) {
#                         if (!isDragging) return;
                        
#                         const deltaX = e.clientX - startX;
#                         const containerWidth = leftCol.parentElement.offsetWidth;
#                         const newLeftWidth = startLeftWidth + deltaX;
#                         const leftPercent = (newLeftWidth / containerWidth) * 100;
#                         const rightPercent = 100 - leftPercent;
                        
#                         // Enforce minimum widths (20% each)
#                         if (leftPercent >= 20 && rightPercent >= 20) {
#                             leftCol.style.flex = `0 0 ${leftPercent}%`;
#                             rightCol.style.flex = `0 0 ${rightPercent}%`;
#                             if (resizer) resizer.style.left = `${leftPercent}%`;
#                         }
#                     });
                    
#                     document.addEventListener('mouseup', function() {
#                         isDragging = false;
#                         document.body.style.cursor = 'default';
#                     });
                    
#                     // Hover effect
#                     resizer.addEventListener('mouseenter', function() {
#                         resizer.style.backgroundColor = '#007bff';
#                     });
                    
#                     resizer.addEventListener('mouseleave', function() {
#                         if (!isDragging) {
#                             resizer.style.backgroundColor = '#dee2e6';
#                         }
#                     });
#                 }
#             });
#         </script>
#     </head>
#     <body>
#         {%app_entry%}
#         <footer>
#             {%config%}
#             {%scripts%}
#             {%renderer%}
#         </footer>
#     </body>
# </html>
# '''

# Define the layout (updated to support left panel reports)
app.layout = html.Div([
    dbc.Row([
        # Left column (70% width) - Report display area
        dbc.Col([
            html.Div(
                id="left-column-content",
                children=[
                    html.Div([
                        html.H5("📊 Territory Reports", style={'margin-bottom': '20px', 'color': '#495057'}),
                        html.P("Generated reports will appear here automatically when territory analysis is completed.", 
                               style={'color': '#6c757d', 'font-style': 'italic'})
                    ], style={'text-align': 'center', 'margin-top': '50px'})
                ],
                style={
                    'height': '100vh',
                    'overflow-y': 'auto',
                    'padding': '20px',
                    'background-color': '#f8f9fa'
                }
            )
        ], id="left-column", width=8),
        
        # Right column (30% width) - Chat interface (unchanged)
        dbc.Col([
            html.Div([
                # Header
                html.Div([
                    html.H4("AI Assistant", style={'margin': '0', 'text-align': 'center'}),
                ], style={'margin-bottom': '20px'}),
                
                # Results area (scrollable)
                html.Div(
                    id="conversation-div",
                    children=[],
                    style={
                        'height': 'calc(100vh - 200px)',
                        'overflow-y': 'auto',
                        'padding': '15px',
                        'border': '1px solid #dee2e6',
                        'border-radius': '5px',
                        'background-color': 'white',
                        'margin-bottom': '15px',
                        'display': 'flex',
                        'flex-direction': 'column-reverse'  # Show latest messages at bottom
                    }
                ),
                
                # Input area (fixed at bottom)
                html.Div([
                    dbc.InputGroup([
                        dbc.Input(
                            id="query-input",
                            placeholder="Enter your query here...",
                            type="text",
                            style={'border-radius': '20px 0 0 20px'}
                        ),
                        dbc.Button(
                            "Send",
                            id="send-button",
                            color="primary",
                            n_clicks=0,
                            style={'border-radius': '0 20px 20px 0'}
                        )
                    ])
                ], style={'position': 'sticky', 'bottom': '0'})
            ], style={
                'height': '100vh',
                'padding': '20px',
                'display': 'flex',
                'flex-direction': 'column'
            })
        ], id="right-column", width=4)
    ], style={'margin': '0', 'height': '100vh'}),
    
    # Floating toggle button (unchanged)
    dbc.Button(
        "−",
        id="minimize-button",
        style={
            'position': 'fixed',
            'top': '20px',
            'right': '20px',
            'width': '50px',
            'height': '50px',
            'border-radius': '50%',
            'background-color': '#28a745',
            'border': 'none',
            'color': 'white',
            'font-size': '24px',
            'font-weight': 'bold',
            'box-shadow': '0 4px 8px rgba(0,0,0,0.3)',
            'z-index': '1000',
            'display': 'flex',
            'align-items': 'center',
            'justify-content': 'center'
        },
        n_clicks=0
    )
], style={'height': '100vh', 'overflow': 'hidden'})

# Helper function to extract report handle from agent response
def extract_report_handle(agent_response: str) -> str:
    """Extract report data handle from agent response"""
    try:
        # Look for pattern: **Report Data Handle**: `handle_name`
        handle_pattern = r'Report Data Handle.*?`([^`]+)`'
        match = re.search(handle_pattern, agent_response)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"Error extracting report handle: {e}")
        return None

# Helper function to fetch report content using MCP
def fetch_report_content(report_handle: str) -> str:
    """Fetch markdown report content from handle using MCP client"""
    try:
        from report_agent import SimpleMCPClient
        
        async def get_report_data():
            client = SimpleMCPClient()
            await client.connect()
            try:
                # Create a message to use get_data_from_handle tool
                messages = [HumanMessage(content=f"Get data from handle: {report_handle}")]
                
                # Invoke the agent with the get data request
                response = await client.agent.ainvoke({"messages": messages})
                
                # Extract the markdown content from the response
                if isinstance(response, dict) and 'messages' in response:
                    messages = response['messages']
                    for message in reversed(messages):
                        if hasattr(message, '__class__') and 'AI' in str(message.__class__):
                            if hasattr(message, 'content') and message.content:
                                # Parse JSON content from the response
                                content = message.content
                                # Look for JSON content between ```json``` blocks
                                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                                if json_match:
                                    import json
                                    try:
                                        data = json.loads(json_match.group(1))
                                        return data.get('markdown_content', 'No markdown content found')
                                    except json.JSONDecodeError:
                                        pass
                                # Fallback to raw content
                                return content
                
                return "Error: Could not extract report content"
                
            finally:
                if hasattr(client, 'client') and client.client:
                    await client.client.close()
        
        return asyncio.run(get_report_data())
        
    except Exception as e:
        return f"Error loading report: {str(e)}"

# Initialize resizer without callback - use a different approach
# The resizer will be initialized automatically when the page loads via the JavaScript

# Callback for minimize/expand functionality (unchanged)
@app.callback(
    [Output('left-column', 'width'),
     Output('right-column', 'width'),
     Output('minimize-button', 'children')],
    [Input('minimize-button', 'n_clicks')]
)
def toggle_right_panel(n_clicks):
    if n_clicks % 2 == 1:  # Odd clicks = minimized
        return 12, 0, "+"  # Left column full width, right hidden, show expand button
    else:  # Even clicks = expanded
        return 8, 4, "−"   # Normal layout, show minimize button

# 🔥 MODIFIED: Main callback function with report display support
@app.callback(
    [Output('conversation-div', 'children'),
     Output('query-input', 'value'),
     Output('left-column-content', 'children')],  # 🔥 Added left panel output
    [Input('send-button', 'n_clicks'),
     Input('query-input', 'n_submit')],
    [State('query-input', 'value'),
     State('conversation-div', 'children'),
     State('left-column-content', 'children')]  # 🔥 Added left panel state
)
def process_query(n_clicks, n_submit, query, current_conversation, current_left_content):
    if (n_clicks > 0 or n_submit) and query and query.strip():
        try:
            # Add user message to conversation
            user_message = html.Div([
                html.Div("Me:", style={
                    'font-weight': 'bold', 
                    'color': '#007bff',
                    'margin-bottom': '5px'
                }),
                html.Div(query, style={
                    'background-color': '#e3f2fd',
                    'padding': '10px',
                    'border-radius': '10px',
                    'margin-bottom': '10px'
                })
            ], style={'margin-bottom': '15px'})
            
            # Process MCP client query
            from report_agent import SimpleMCPClient
            
            async def run_query():
                client = SimpleMCPClient()
                await client.connect()
                try:
                    response = await client.analyze_territories(query)
                    return response
                finally:
                    if hasattr(client, 'client') and client.client:
                        try:
                            await client.client.close()
                        except:
                            pass
            
            result = asyncio.run(run_query())
            
            # Format agent response
            if isinstance(result, str):
                agent_response = result
            else:
                agent_response = str(result)
            
            # Add agent message to conversation
            agent_message = html.Div([
                html.Div("Agent:", style={
                    'font-weight': 'bold', 
                    'color': '#28a745',
                    'margin-bottom': '5px'
                }),
                html.Div(agent_response, style={
                    'background-color': '#f8f9fa',
                    'padding': '10px',
                    'border-radius': '10px',
                    'white-space': 'pre-wrap'
                })
            ], style={'margin-bottom': '15px'})
            
            # Update conversation history
            if current_conversation is None:
                current_conversation = []
            
            updated_conversation = [agent_message, user_message] + current_conversation
            
            # 🔥 NEW: Check for report handle and update left panel
            left_panel_content = current_left_content  # Default to current content
            report_handle = extract_report_handle(agent_response)
            print(f"Extracted report handle: {report_handle}")
            if report_handle:
                # Fetch the markdown report content
                try:
                    markdown_content = fetch_report_content(report_handle)
                    
                    # Create the report display
                    left_panel_content = [
                        html.Div([
                            html.H5(f"📊 Territory Analysis Report", 
                                   style={'margin-bottom': '20px', 'color': '#495057', 'border-bottom': '2px solid #007bff', 'padding-bottom': '10px'}),
                            html.Div([
                                html.Small(f"Report Handle: {report_handle}", 
                                         style={'color': '#6c757d', 'font-style': 'italic'})
                            ], style={'margin-bottom': '20px'}),
                            dcc.Markdown(
                                markdown_content,
                                style={
                                    'background-color': 'white',
                                    'padding': '20px',
                                    'border-radius': '8px',
                                    'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
                                }
                            )
                        ])
                    ]
                except Exception as e:
                    left_panel_content = [
                        html.Div([
                            html.H5("❌ Error Loading Report", style={'color': '#dc3545'}),
                            html.P(f"Could not load report from handle: {report_handle}"),
                            html.P(f"Error: {str(e)}", style={'color': '#6c757d', 'font-size': '0.9em'})
                        ])
                    ]
            
            return updated_conversation, "", left_panel_content  # 🔥 Return updated left panel
            
        except Exception as e:
            # Add error message to conversation
            error_message = html.Div([
                html.Div("Agent:", style={
                    'font-weight': 'bold', 
                    'color': '#dc3545',
                    'margin-bottom': '5px'
                }),
                html.Div(f"Error: {str(e)}", style={
                    'background-color': '#f8d7da',
                    'padding': '10px',
                    'border-radius': '10px',
                    'color': '#721c24'
                })
            ], style={'margin-bottom': '15px'})
            
            user_message = html.Div([
                html.Div("Me:", style={
                    'font-weight': 'bold', 
                    'color': '#007bff',
                    'margin-bottom': '5px'
                }),
                html.Div(query, style={
                    'background-color': '#e3f2fd',
                    'padding': '10px',
                    'border-radius': '10px',
                    'margin-bottom': '10px'
                })
            ], style={'margin-bottom': '15px'})
            
            if current_conversation is None:
                current_conversation = []
            
            updated_conversation = [error_message, user_message] + current_conversation
            
            return updated_conversation, "", current_left_content  # Keep current left panel content on error
    
    # Return current state if no valid input
    return current_conversation or [], query or "", current_left_content

if __name__ == '__main__':
    app.run(debug=True)