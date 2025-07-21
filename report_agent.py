"""
Simplified Geospatial Analysis Agent - Pure MCP Orchestration

This agent focuses solely on tool orchestration via MCP protocol.
All report generation, file saving, and visualization handling is done by the server tools.
"""

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from system_prompts import GEOSPATIAL_ANALYSIS_PROMPT as TERRITORY_OPTIMIZATION_PROMPT
from config import Config


class SimpleMCPClient:
    """
    Simple MCP client that orchestrates tools without duplicating their functionality.
    All report generation is handled by server tools.
    """
    
    def __init__(self, 
                 config_override: dict = None,
                 model: str = None,
                 temperature: float = None):
        """
        Initialize the MCP client
        
        Args:
            config_override: Optional configuration overrides
            model: OpenAI model to use (defaults to config)
            temperature: Model temperature setting (defaults to config)
        """
        print("🚀 Initializing Simple MCP Client...")
        
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
        
        # Initialize client and agent (will be set up in connect method)
        self.client = None
        self.agent = None
        self.tools = None
        
    async def connect(self):
        """Connect to MCP server and initialize tools"""
        print("🔌 Connecting to MCP server...")
        
        # Initialize MCP client
        self.client = MultiServerMCPClient(self.mcp_config)
        
        # Get available tools from the MCP server
        self.tools = await self.client.get_tools()
        print(f"📋 Available tools: {[tool.name for tool in self.tools]}")
        
        # Initialize LLM and agent
        llm = ChatOpenAI(model=self.model, temperature=self.temperature)
        self.agent = create_react_agent(llm, self.tools)
        
        print("✅ MCP client successfully connected!")
        
    async def analyze_territories(self, user_query: str) -> str:
        """
        Analyze territories based on user query.
        Pure tool orchestration - no file operations.
        
        Args:
            user_query: User's request for territory analysis
        
        Returns:
            Final response from the agent
        """
        if not self.agent:
            raise ValueError("Agent not connected. Please call connect() first.")
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=TERRITORY_OPTIMIZATION_PROMPT),
            HumanMessage(content=user_query)
        ]
        
        print(f"🔄 Processing query: {user_query[:100]}...")
        print(f"🤖 Using {self.model} with temperature {self.temperature}")
        
        # Let the LLM orchestrate tools via MCP
        response = await self.agent.ainvoke({"messages": messages})
        
        # Extract the final AI response
        return self._extract_final_response(response)
    
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
    
    async def interactive_mode(self):
        """Run the agent in interactive mode - simple conversation interface"""
        if not self.agent:
            print("❌ Agent not connected. Please call connect() first.")
            return
        
        print("\n" + "="*80)
        print("🎯 GEOSPATIAL ANALYSIS AGENT - Interactive Mode")
        print("="*80)
        print("💡 Ask me to analyze sales territories, optimize locations, or generate reports!")
        print("💡 Example: 'Create 6 sales territories for supermarkets in Riyadh'")
        print("💡 Type 'exit' to quit")
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
                
                # Process the query
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