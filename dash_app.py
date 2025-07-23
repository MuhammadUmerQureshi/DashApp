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

# Define the app layout
app.layout = html.Div([
    dbc.Row([
        # Left column - can be used for other content or kept empty
        dbc.Col([
            html.Div([
                html.H5("Chat Dashboard", style={'margin-bottom': '20px', 'color': '#495057'}),
                html.P("Welcome to the location intelligence chat interface.", 
                      style={'color': '#6c757d'}),
                html.Hr(),
                html.P("Ask questions about:", style={'font-weight': 'bold', 'margin-bottom': '10px'}),
                html.Ul([
                    html.Li("Territory analysis"),
                    html.Li("Location intelligence"),
                    html.Li("Market research"),
                    html.Li("Demographic data")
                ], style={'color': '#6c757d'})
            ], id="left-column-content", style={
                'height': '100vh',
                'padding': '20px',
                'background-color': '#f8f9fa',
                'overflow-y': 'auto'
            })
        ], id="left-column", width=8),
        
        # Right column - Chat interface
        dbc.Col([
            html.Div([
                # Chat header
                html.H6("Chat Assistant", style={
                    'text-align': 'center',
                    'margin-bottom': '20px',
                    'padding': '10px',
                    'background-color': '#007bff',
                    'color': 'white',
                    'border-radius': '10px'
                }),
                
                # Conversation area (scrollable)
                html.Div(
                    id="conversation-div",
                    children=[],
                    style={
                        'height': '85vh',
                        'overflow-y': 'auto',
                        'border': '1px solid #dee2e6',
                        'border-radius': '10px',
                        'padding': '15px',
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
                'padding': '20px 20px 0 20px',
                'display': 'flex',
                'flex-direction': 'column'
            })
        ], id="right-column", width=4)
    ], style={'margin': '0', 'height': '100vh'}),
    
    # Floating toggle button
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

# Initialize resizer without callback - use a different approach
# The resizer will be initialized automatically when the page loads via the JavaScript

# Callback for minimize/expand functionality
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

# Simplified main callback function for chat only
@app.callback(
    [Output('conversation-div', 'children'),
     Output('query-input', 'value')],
    [Input('send-button', 'n_clicks'),
     Input('query-input', 'n_submit')],
    [State('query-input', 'value'),
     State('conversation-div', 'children')]
)
def process_query(n_clicks, n_submit, query, current_conversation):
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
            
            return updated_conversation, ""
            
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
            
            return updated_conversation, ""
    
    # Return current state if no valid input
    return current_conversation or [], query or ""

if __name__ == '__main__':
    app.run(debug=True)