"""
Simplified Geospatial Analysis Agent - Pure MCP Orchestration with Memory

This agent focuses solely on tool orchestration via MCP protocol with conversation memory.
All report generation, file saving, and visualization handling is done by the server tools.
"""

import asyncio
import uuid
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from system_prompts import TERRITORY_OPTIMIZATION_PROMPT
from config import Config


class SimpleMCPClient:
    """
    Simple MCP client that orchestrates tools without duplicating their functionality.
    All report generation is handled by server tools.
    """
    
    def __init__(self, 
                 session_id: str = None,
                 config_override: dict = None,
                 model: str = None,
                 temperature: float = None):
        """
        Initialize the MCP client with memory support
        
        Args:
            session_id: Session identifier for conversation continuity
            config_override: Optional configuration overrides
            model: OpenAI model to use (defaults to config)
            temperature: Model temperature setting (defaults to config)
        """
        print("🚀 Initializing Simple MCP Client with Memory...")
        
        # Session management
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.default_thread_id = f"conversation_{self.session_id}"
        
        # Validate configuration
        if not Config.validate_paths():
            raise ValueError("Required paths are missing. Please check configuration.")
        
        # Set model parameters
        self.model = model or Config.DEFAULT_MODEL
        self.temperature = temperature if temperature is not None else Config.DEFAULT_TEMPERATURE
        
        # Get MCP configuration
        self.mcp_config = Config.get_mcp_config()
        
        # Apply any configuration overrides
        if config_override:
            self.mcp_config.update(config_override)
        
        # Initialize memory checkpointer
        self.checkpointer = MemorySaver()
        
        # Initialize client and agent (will be set up in connect method)
        self.client = None
        self.agent = None
        self.tools = None
        
        print(f"📋 Session ID: {self.session_id}")
        
    async def connect(self):
        """Connect to MCP server and initialize tools with memory"""
        print("🔌 Connecting to MCP server...")
        
        # Initialize MCP client
        self.client = MultiServerMCPClient(self.mcp_config)
        
        # Get available tools from the MCP server
        self.tools = await self.client.get_tools()
        print(f"📋 Available tools: {[tool.name for tool in self.tools]}")
        
        # Initialize LLM and agent with checkpointer
        llm = ChatOpenAI(model=self.model, temperature=self.temperature)
        self.agent = create_react_agent(
            llm, 
            self.tools, 
            checkpointer=self.checkpointer
        )
        
        print("✅ MCP client successfully connected with memory!")
        
    async def analyze_territories(self, user_query: str, thread_id: str = None) -> str:
        """
        Analyze territories based on user query with conversation memory.
        Pure tool orchestration - no file operations.
        
        Args:
            user_query: User's request for territory analysis
            thread_id: Thread identifier for conversation continuity (optional)
        
        Returns:
            Final response from the agent
        """
        if not self.agent:
            raise ValueError("Agent not connected. Please call connect() first.")
        
        # Use provided thread_id or default
        current_thread_id = thread_id or self.default_thread_id
        
        # Create configuration with thread_id for memory
        config = {"configurable": {"thread_id": current_thread_id}}
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=TERRITORY_OPTIMIZATION_PROMPT),
            HumanMessage(content=user_query)
        ]
        
        print(f"🔄 Processing query: {user_query[:100]}...")
        print(f"🧠 Using thread: {current_thread_id}")
        print(f"🤖 Using {self.model} with temperature {self.temperature}")
        
        # Let the LLM orchestrate tools via MCP with memory
        response = await self.agent.ainvoke({"messages": messages}, config=config)
        
        # Extract the final AI response
        return self._extract_final_response(response)
    
    async def analyze_territories_with_file_handle(self, user_query: str, thread_id: str = None) -> dict:
        """
        Analyze territories and return both response and file handle for Dash app
        
        Args:
            user_query: User's request for territory analysis
            thread_id: Thread identifier for conversation continuity (optional)
        
        Returns:
            Dictionary with 'response' and 'raw_content' keys
        """
        if not self.agent:
            raise ValueError("Agent not connected. Please call connect() first.")
        
        # Use provided thread_id or default
        current_thread_id = thread_id or self.default_thread_id
        
        # Create configuration with thread_id for memory
        config = {"configurable": {"thread_id": current_thread_id}}
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=TERRITORY_OPTIMIZATION_PROMPT),
            HumanMessage(content=user_query)
        ]
        
        print(f"🔄 Processing query: {user_query[:100]}...")
        print(f"🧠 Using thread: {current_thread_id}")
        print(f"🤖 Using {self.model} with temperature {self.temperature}")
        
        # Let the LLM orchestrate tools via MCP with memory
        response = await self.agent.ainvoke({"messages": messages}, config=config)
        
        # Return both formatted response and raw content for file handle extraction
        return {
            'response': self._extract_final_response(response),
            'raw_content': self._extract_file_handle_from_response(response)
        }
    
    def _extract_final_response(self, response) -> str:
        """Extract the final AI response from the agent output"""
        if isinstance(response, dict) and 'messages' in response:
            messages = response['messages']
            
            # Look for the last AI message with content
            for message in reversed(messages):
                if hasattr(message, '__class__') and 'AI' in str(message.__class__):
                    if hasattr(message, 'content') and message.content and message.content.strip():
                        return message.content
            
            return "✅ Territory analysis completed! Reports have been generated and saved by the system."
        else:
            return "✅ Analysis completed successfully."
    
    def _extract_file_handle_from_response(self, response) -> str:
        """
        Extract file handle from response for Dash app integration
        Returns the response with file handle information for parsing
        """
        if isinstance(response, dict) and 'messages' in response:
            messages = response['messages']
            
            # Look for the last AI message with content
            for message in reversed(messages):
                if hasattr(message, '__class__') and 'AI' in str(message.__class__):
                    if hasattr(message, 'content') and message.content and message.content.strip():
                        # Return the full content for file handle parsing
                        return message.content
        
        return response
    
    def get_conversation_history(self, thread_id: str = None) -> dict:
        """Get conversation history for a specific thread"""
        current_thread_id = thread_id or self.default_thread_id
        config = {"configurable": {"thread_id": current_thread_id}}
        
        try:
            # Get state from checkpointer
            state = self.checkpointer.get(config)
            if state and 'messages' in state:
                return {
                    "thread_id": current_thread_id,
                    "message_count": len(state['messages']),
                    "messages": state['messages']
                }
        except Exception as e:
            print(f"⚠️ Could not retrieve conversation history: {e}")
        
        return {"thread_id": current_thread_id, "message_count": 0, "messages": []}
    
    async def interactive_mode(self):
        """Run the agent in interactive mode with memory - simple conversation interface"""
        if not self.agent:
            print("❌ Agent not connected. Please call connect() first.")
            return
        
        print("\n" + "="*80)
        print("🎯 GEOSPATIAL ANALYSIS AGENT - Interactive Mode with Memory")
        print("="*80)
        print("💡 Ask me to analyze sales territories, optimize locations, or generate reports!")
        print("💡 I'll remember our conversation context automatically!")
        print("💡 Example: 'Create 6 sales territories for supermarkets in Riyadh'")
        print("💡 Type 'exit' to quit")
        print(f"🧠 Session: {self.session_id}")
        print("="*80)
        
        while True:
            try:
                # Get user input
                print(f"\n🎯 Enter your analysis request:")
                user_input = input(">>> ").strip()
                
                # Handle exit commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    print("⚠️ Please enter a query.")
                    continue
                
                # Process the query with memory
                print(f"\n🔄 Processing your request...")
                response = await self.analyze_territories(user_input)
                
                # Display results
                print(f"\n" + "="*80)
                print(f"📋 ANALYSIS COMPLETED")
                print("="*80)
                print(response)
                print("="*80)
                
                # Simple status message
                print(f"\n📁 All reports and visualizations have been automatically saved by the system.")
                print(f"📊 Check the server's reports directory for generated files.")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("🔄 Please try again with a different query.")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.close()


async def main():
    """Main entry point for the simplified MCP client"""
    try:
        # Create and run the client
        async with SimpleMCPClient() as client:
            await client.interactive_mode()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())