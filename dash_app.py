import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import asyncio
from langchain_core.messages import HumanMessage

# Import our custom modules
from report_handler import report_handler
from report_display import report_display

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.config.suppress_callback_exceptions = True

# Store for conversation history
conversation_history = []

# Global MCP client instance for memory persistence - LAZY INITIALIZATION
mcp_client = None
DASH_THREAD_ID = "dash_conversation_main"

def get_or_create_client():
    """Get or create a persistent MCP client with memory - LAZY INITIALIZATION"""
    global mcp_client
    if mcp_client is None:
        print("🚀 Creating new MCP client with memory...")
        from report_agent import SimpleMCPClient
        # Create client with specific session for Dash app
        mcp_client = SimpleMCPClient(session_id="dash_session")
        print("✅ MCP client created, will connect on first use")
    return mcp_client

async def ensure_client_connected():
    """Ensure the MCP client is connected"""
    client = get_or_create_client()
    if client and not client.agent:
        print("🔌 Connecting MCP client...")
        await client.connect()
        print("✅ MCP client connected with memory!")
    return client

# Define the layout (following original pattern exactly)
app.layout = html.Div([
    dbc.Row([
        # Left column (70% width) - Report display area
        dbc.Col([
            html.Div(
                id="left-column-content",
                children=[
                    report_display.create_report_layout()
                ],
                style={
                    'height': '100vh',
                    'overflow-y': 'auto',
                    'padding': '20px',
                    'background-color': '#f8f9fa'
                }
            )
        ], id="left-column", width=8),
        
        # Right column (30% width) - Chat interface
        dbc.Col([
            html.Div([
                # Header with memory indicator
                html.Div([
                    html.H4("AI Assistant", style={'margin': '0', 'text-align': 'center'}),
                    # Memory status indicator
                    html.Div([
                        html.Small("🧠 Memory: Active", 
                                  style={'color': '#28a745', 'font-weight': 'bold'}),
                        html.Br(),
                        html.Small(f"Thread: {DASH_THREAD_ID}", 
                                  style={'color': '#6c757d', 'font-size': '0.8em'})
                    ], style={'margin-top': '10px', 'padding': '8px', 
                             'background-color': '#f8f9fa', 'border-radius': '5px',
                             'text-align': 'center'})
                ], style={'margin-bottom': '20px'}),
                
                # Results area (scrollable)
                html.Div(
                    id="conversation-div",
                    children=[],
                    style={
                        'height': 'calc(100vh - 250px)',  # Adjusted for memory indicator
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

# Main callback function with memory support and report display
@app.callback(
    [Output('conversation-div', 'children'),
     Output('query-input', 'value'),
     Output('report-content', 'children'),
     Output('report-status', 'children')],
    [Input('send-button', 'n_clicks'),
     Input('query-input', 'n_submit')],
    [State('query-input', 'value'),
     State('conversation-div', 'children')]
)
def process_query(n_clicks, n_submit, query, current_conversation):
    if (n_clicks and n_clicks > 0) or n_submit:
        if query and query.strip():
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
                
                # Process MCP client query with memory and file handle support
                async def run_query_with_memory():
                    client = await ensure_client_connected()
                    if not client:
                        return {"response": "Error: Could not connect to MCP client", "raw_content": ""}
                    
                    try:
                        # Use persistent thread ID for conversation continuity
                        # Use the new method that returns both response and raw content
                        result = await client.analyze_territories_with_file_handle(query, thread_id=DASH_THREAD_ID)
                        return result
                    except Exception as e:
                        return {"response": f"Error processing query: {str(e)}", "raw_content": ""}
                
                # Create new event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(run_query_with_memory())
                
                # Extract response and raw content
                if isinstance(result, dict):
                    agent_response = str(result.get('response', ''))
                    raw_content = result.get('raw_content', '')
                else:
                    agent_response = str(result)
                    raw_content = str(result)
                
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
                
                # Handle report display
                report_content = report_display._create_empty_state()
                report_status = report_display.create_report_status_indicator('empty')
                
                # Try to extract file handle from raw content and display report
                if raw_content:
                    print(f"🔍 Processing raw content for file handle extraction...")
                    file_handle = report_handler.parse_file_handle_from_response(raw_content)
                    if file_handle:
                        print(f"📄 Found file handle: {file_handle}")
                        # Try to read the report
                        md_content = report_handler.read_md_report(file_handle)
                        if md_content:
                            report_content = report_display.format_markdown_for_dash(md_content)
                            # Get report metadata
                            metadata = report_handler.extract_report_metadata(file_handle)
                            report_status = report_display.create_report_status_indicator('loaded', metadata)
                            print(f"✅ Report loaded and displayed")
                        else:
                            print(f"❌ Could not read report from handle: {file_handle}")
                            report_status = report_display.create_report_status_indicator('error')
                    else:
                        print("ℹ️ No file handle found in response")
                
                return updated_conversation, "", report_content, report_status
                
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
                
                # Return error state for report display
                error_report_content = report_display.create_error_display(str(e))
                error_report_status = report_display.create_report_status_indicator('error')
                
                return updated_conversation, "", error_report_content, error_report_status
    
    # Return current state if no valid input
    empty_report = report_display._create_empty_state()
    empty_status = report_display.create_report_status_indicator('empty')
    return current_conversation or [], query or "", empty_report, empty_status

if __name__ == '__main__':
    app.run(debug=True)