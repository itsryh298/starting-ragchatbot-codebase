"""
Tests for AIGenerator in ai_generator.py

Tests validate:
- generate_response() with and without tools
- Tool calling flow (_handle_tool_execution)
- Message formatting for tool results
- Conversation history integration
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai_generator import AIGenerator


class MockContentBlock:
    """Mock for Anthropic content block"""
    def __init__(self, block_type, text=None, tool_name=None, tool_id=None, tool_input=None):
        self.type = block_type
        self.text = text
        self.name = tool_name
        self.id = tool_id
        self.input = tool_input or {}


class MockResponse:
    """Mock for Anthropic API response"""
    def __init__(self, content_blocks, stop_reason="end_turn"):
        self.content = content_blocks
        self.stop_reason = stop_reason


class TestAIGeneratorBasics:
    """Test basic AIGenerator functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.api_key = "test-api-key"
        self.model = "claude-sonnet-4-20250514"
        self.generator = AIGenerator(self.api_key, self.model)

    def test_initialization(self):
        """Test AIGenerator initializes correctly"""
        assert self.generator.model == self.model
        assert self.generator.base_params["model"] == self.model
        assert self.generator.base_params["temperature"] == 0
        assert self.generator.base_params["max_tokens"] == 800

    def test_system_prompt_exists(self):
        """Test that system prompt is defined"""
        assert hasattr(AIGenerator, 'SYSTEM_PROMPT')
        assert len(AIGenerator.SYSTEM_PROMPT) > 0
        assert "tool" in AIGenerator.SYSTEM_PROMPT.lower()


class TestGenerateResponseWithoutTools:
    """Test generate_response without tool calls"""

    def setup_method(self):
        """Set up test fixtures"""
        self.generator = AIGenerator("test-key", "test-model")

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_simple_response(self, mock_anthropic_class):
        """Test generating a simple response without tools"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Python is a programming language")],
            stop_reason="end_turn"
        )
        mock_client.messages.create.return_value = mock_response

        # Reinitialize generator with mocked client
        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        # Act
        result = generator.generate_response(query="What is Python?")

        # Assert
        assert result == "Python is a programming language"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["messages"][0]["content"] == "What is Python?"

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_with_conversation_history(self, mock_anthropic_class):
        """Test that conversation history is included in system prompt"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Response with context")],
            stop_reason="end_turn"
        )
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        history = "User: Previous question\nAssistant: Previous answer"

        # Act
        result = generator.generate_response(
            query="Follow-up question",
            conversation_history=history
        )

        # Assert
        call_kwargs = mock_client.messages.create.call_args[1]
        assert history in call_kwargs["system"]


class TestGenerateResponseWithTools:
    """Test generate_response with tool calling"""

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_use_detection(self, mock_anthropic_class):
        """Test that tool_use stop_reason triggers tool execution"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # First response: tool use
        tool_use_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_123",
                    tool_input={"query": "Python basics"}
                )
            ],
            stop_reason="tool_use"
        )

        # Second response: final answer
        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Here's what I found about Python")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search results: Python is great"

        # Mock tools
        tools = [{"name": "search_course_content", "description": "Search"}]

        # Act
        result = generator.generate_response(
            query="Tell me about Python",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert
        assert result == "Here's what I found about Python"
        assert mock_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="Python basics"
        )

    @patch('ai_generator.anthropic.Anthropic')
    def test_tools_added_to_api_call(self, mock_anthropic_class):
        """Test that tools are included in API parameters"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Answer")],
            stop_reason="end_turn"
        )
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        tools = [{"name": "search_course_content", "description": "Search"}]

        # Act
        generator.generate_response(query="Query", tools=tools)

        # Assert
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}


class TestHandleToolExecution:
    """Test _handle_tool_execution method"""

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_result_message_format(self, mock_anthropic_class):
        """Test that tool results are formatted correctly"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        tool_use_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_abc",
                    tool_input={"query": "test"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Final answer")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result content"

        tools = [{"name": "search_course_content"}]

        # Act
        generator.generate_response(
            query="Query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert
        # Get the second API call (after tool execution)
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # Check message structure
        assert len(messages) == 3  # user query, assistant tool_use, user tool_result
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Check tool result format
        tool_result = messages[2]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "tool_abc"
        assert tool_result["content"] == "Tool result content"

    @patch('ai_generator.anthropic.Anthropic')
    def test_multiple_tool_calls(self, mock_anthropic_class):
        """Test handling multiple tool calls in one response"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        tool_use_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_1",
                    tool_input={"query": "Python"}
                ),
                MockContentBlock(
                    "tool_use",
                    tool_name="get_course_outline",
                    tool_id="tool_2",
                    tool_input={"course_name": "Python 101"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Combined answer")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        tools = [
            {"name": "search_course_content"},
            {"name": "get_course_outline"}
        ]

        # Act
        result = generator.generate_response(
            query="Query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert
        assert mock_tool_manager.execute_tool.call_count == 2
        # Check both tools were called
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="Python")
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="Python 101")

    @patch('ai_generator.anthropic.Anthropic')
    def test_no_tools_in_final_call(self, mock_anthropic_class):
        """Test that tools are not included in the final API call"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Two rounds of tool use, then final response
        tool_use_response_1 = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_1",
                    tool_input={"query": "test"}
                )
            ],
            stop_reason="tool_use"
        )

        tool_use_response_2 = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="get_course_outline",
                    tool_id="tool_2",
                    tool_input={"course_name": "Test Course"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Final answer")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [
            tool_use_response_1,
            tool_use_response_2,
            final_response
        ]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        tools = [{"name": "search_course_content"}, {"name": "get_course_outline"}]

        # Act
        generator.generate_response(query="Query", tools=tools, tool_manager=mock_tool_manager)

        # Assert
        # First call (initial) should have tools
        first_call_kwargs = mock_client.messages.create.call_args_list[0][1]
        assert "tools" in first_call_kwargs

        # Second call (round 0 follow-up) should have tools
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs

        # Third call (round 1 follow-up, final) should NOT have tools
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs


class TestSequentialToolCalling:
    """Test sequential tool calling with up to 2 rounds"""

    @patch('ai_generator.anthropic.Anthropic')
    def test_two_rounds_tool_use(self, mock_anthropic_class):
        """Test that Claude can use tools in 2 sequential rounds"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Three responses: tool_use -> tool_use -> end_turn
        round1_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="get_course_outline",
                    tool_id="tool_1",
                    tool_input={"course_name": "Python"}
                )
            ],
            stop_reason="tool_use"
        )

        round2_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_2",
                    tool_input={"query": "lesson 4", "course_name": "Python"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Here's the comparison")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [
            round1_response,
            round2_response,
            final_response
        ]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Outline: Lesson 4 is about X",
            "Content: Lesson 4 teaches Y"
        ]

        tools = [
            {"name": "get_course_outline"},
            {"name": "search_course_content"}
        ]

        # Act
        result = generator.generate_response(
            query="What does lesson 4 teach?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert
        assert result == "Here's the comparison"
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

    @patch('ai_generator.anthropic.Anthropic')
    def test_single_round_still_works(self, mock_anthropic_class):
        """Test that single-round tool calling still works (regression test)"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        tool_use_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_1",
                    tool_input={"query": "Python"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Python is a language")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Python course content"

        tools = [{"name": "search_course_content"}]

        # Act
        result = generator.generate_response(
            query="What is Python?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert
        assert result == "Python is a language"
        assert mock_client.messages.create.call_count == 2
        assert mock_tool_manager.execute_tool.call_count == 1

    @patch('ai_generator.anthropic.Anthropic')
    def test_max_rounds_enforced(self, mock_anthropic_class):
        """Test that loop terminates at MAX_TOOL_ROUNDS limit"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Three tool_use responses to test limit enforcement
        tool_use_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_abc",
                    tool_input={"query": "test"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Final answer")],
            stop_reason="end_turn"
        )

        # Return tool_use twice, then final response
        mock_client.messages.create.side_effect = [
            tool_use_response,
            tool_use_response,
            final_response
        ]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        tools = [{"name": "search_course_content"}]

        # Act
        result = generator.generate_response(
            query="Query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert
        # Should make exactly 3 API calls (initial + 2 rounds)
        assert mock_client.messages.create.call_count == 3
        # Should execute tools exactly 2 times (MAX_TOOL_ROUNDS)
        assert mock_tool_manager.execute_tool.call_count == 2
        assert result == "Final answer"

    @patch('ai_generator.anthropic.Anthropic')
    def test_messages_accumulate_correctly(self, mock_anthropic_class):
        """Test that messages array grows correctly across rounds"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Track messages at each call by capturing copies
        captured_messages = []

        def create_with_capture(**kwargs):
            # Capture a copy of messages at this point
            if "messages" in kwargs:
                captured_messages.append(len(kwargs["messages"]))
            # Return appropriate response based on call count
            call_count = len(captured_messages)
            if call_count == 1:
                return round1_response
            elif call_count == 2:
                return round2_response
            else:
                return final_response

        round1_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_1",
                    tool_input={"query": "test1"}
                )
            ],
            stop_reason="tool_use"
        )

        round2_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_2",
                    tool_input={"query": "test2"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Done")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = create_with_capture

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        tools = [{"name": "search_course_content"}]

        # Act
        generator.generate_response(query="Query", tools=tools, tool_manager=mock_tool_manager)

        # Assert - verify message counts at each call
        # First call: 1 message (user query)
        assert captured_messages[0] == 1

        # Second call: 3 messages (user, assistant tool_use, user tool_result)
        assert captured_messages[1] == 3

        # Third call: 5 messages (all previous + round 2 assistant + tool_result)
        assert captured_messages[2] == 5

        # Verify 3 total API calls
        assert len(captured_messages) == 3

    @patch('ai_generator.anthropic.Anthropic')
    def test_tools_removed_in_final_round(self, mock_anthropic_class):
        """Test that tools parameter is removed in the final round"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        round1_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_1",
                    tool_input={"query": "test1"}
                )
            ],
            stop_reason="tool_use"
        )

        round2_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_2",
                    tool_input={"query": "test2"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="Done")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [
            round1_response,
            round2_response,
            final_response
        ]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        tools = [{"name": "search_course_content"}]

        # Act
        generator.generate_response(query="Query", tools=tools, tool_manager=mock_tool_manager)

        # Assert
        calls = mock_client.messages.create.call_args_list

        # Initial call should have tools
        assert "tools" in calls[0][1]

        # Round 0 follow-up should have tools (not final round)
        assert "tools" in calls[1][1]

        # Round 1 follow-up should NOT have tools (is final round)
        assert "tools" not in calls[2][1]

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_error_handling(self, mock_anthropic_class):
        """Test that tool execution errors are handled gracefully"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        tool_use_response = MockResponse(
            content_blocks=[
                MockContentBlock(
                    "tool_use",
                    tool_name="search_course_content",
                    tool_id="tool_1",
                    tool_input={"query": "test"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content_blocks=[MockContentBlock("text", text="I encountered an error")],
            stop_reason="end_turn"
        )

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool failed")

        tools = [{"name": "search_course_content"}]

        # Act
        result = generator.generate_response(
            query="Query",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert - should not raise exception, should return graceful response
        assert result == "I encountered an error"
        assert mock_client.messages.create.call_count == 2

        # Verify error message was sent to Claude
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result = second_call_messages[-1]["content"][0]
        assert "Tool execution failed" in tool_result["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
