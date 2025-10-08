import anthropic
from typing import List, Optional, Dict, Any
from config import config

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Tool Usage Guidelines:
- **Content Search Tool** (`search_course_content`): Use for questions about specific course content or detailed educational materials
- **Outline Tool** (`get_course_outline`): Use for questions about course structure, lesson lists, or course overviews
- **Use tools efficiently**: Prefer getting all needed information in one search when possible. If initial results are insufficient, you may make one additional tool call to gather missing information
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

When Using the Outline Tool:
- Include the course title, course link, and complete lesson list in your response
- For each lesson, provide both the lesson number and lesson title
- Present information clearly and directly

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the outline tool"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages array
        messages = [{"role": "user", "content": query}]

        # Prepare initial API call parameters
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get initial response from Claude
        response = self.client.messages.create(**api_params)

        # Handle sequential tool execution if needed
        tool_round = 0
        while (response.stop_reason == "tool_use" and
               tool_round < config.MAX_TOOL_ROUNDS and
               tool_manager is not None):

            # Determine if this is the final tool round
            is_final_round = (tool_round == config.MAX_TOOL_ROUNDS - 1)

            # Execute tools and get next response
            response, messages = self._handle_tool_execution(
                response,
                messages,
                system_content,
                tools,
                tool_manager,
                is_final_round
            )

            tool_round += 1

        # Extract and return text response
        return self._extract_text_response(response)
    
    def _handle_tool_execution(self, current_response, messages: list, system_content: str,
                              tools: Optional[List], tool_manager, is_final_round: bool):
        """
        Handle execution of tool calls and get follow-up response.

        Args:
            current_response: The response containing tool use requests
            messages: Current message history
            system_content: System prompt content
            tools: Available tools for Claude to use
            tool_manager: Manager to execute tools
            is_final_round: Whether this is the final tool round (affects tool availability)

        Returns:
            Tuple of (response, updated_messages)
        """
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": current_response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in current_response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )
                    # Ensure non-empty result
                    if not tool_result:
                        tool_result = "No results returned"
                except Exception as e:
                    tool_result = f"Tool execution failed: {str(e)}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Prepare next API call
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        # Only include tools if not final round
        if not is_final_round and tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get next response
        next_response = self.client.messages.create(**api_params)
        return (next_response, messages)

    def _extract_text_response(self, response) -> str:
        """
        Safely extract text from response content blocks.

        Args:
            response: API response object

        Returns:
            Text content from first text block, or empty string if none found
        """
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""