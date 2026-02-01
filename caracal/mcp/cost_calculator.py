"""
Cost calculator for MCP operations.

This module provides cost estimation for MCP tool calls and resource reads
based on the pricebook.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from caracal.core.pricebook import Pricebook
from caracal.logging_config import get_logger

logger = get_logger(__name__)


class MCPCostCalculator:
    """
    Calculates costs for MCP operations.
    
    Provides cost estimation for:
    - Tool invocations (based on tool type and arguments)
    - Resource reads (based on resource type and size)
    - Prompt access (based on template and arguments)
    - Sampling requests (based on model and token usage)
    
    Requirements: 12.2
    """

    def __init__(self, pricebook: Pricebook):
        """
        Initialize MCPCostCalculator.
        
        Args:
            pricebook: Pricebook instance for price lookups
        """
        self.pricebook = pricebook
        logger.info("MCPCostCalculator initialized")

    async def estimate_tool_cost(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Decimal:
        """
        Estimate cost for MCP tool invocation.
        
        Cost estimation strategies:
        - LLM tools: Based on estimated token usage
        - API tools: Based on endpoint and data size
        - Compute tools: Based on execution time estimate
        - Default: Flat rate per tool invocation
        
        Args:
            tool_name: Name of the MCP tool
            tool_args: Tool arguments containing cost parameters
            
        Returns:
            Estimated cost in USD
        """
        # Check if this is an LLM tool
        if self._is_llm_tool(tool_name, tool_args):
            return await self._estimate_llm_tool_cost(tool_name, tool_args)
        
        # Check if this is an API tool
        if self._is_api_tool(tool_name, tool_args):
            return await self._estimate_api_tool_cost(tool_name, tool_args)
        
        # Default: flat rate per tool invocation
        resource_type = f"mcp.tool.{tool_name}"
        price = self.pricebook.get_price(resource_type)
        
        if price is None or price == Decimal("0"):
            # Use default MCP tool price if specific tool not in pricebook
            price = self.pricebook.get_price("mcp.tool.default")
            if price is None or price == Decimal("0"):
                # Fallback to a reasonable default
                price = Decimal("0.01")
                logger.warning(
                    f"No price found for tool '{tool_name}' or 'mcp.tool.default', "
                    f"using fallback price: {price} USD"
                )
        
        logger.debug(
            f"Estimated cost for tool '{tool_name}': {price} USD (flat rate)"
        )
        
        return price

    async def calculate_actual_tool_cost(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any
    ) -> Decimal:
        """
        Calculate actual cost for MCP tool invocation based on result.
        
        For LLM tools, extracts actual token usage from result.
        For other tools, uses the estimated cost.
        
        Args:
            tool_name: Name of the MCP tool
            tool_args: Tool arguments
            tool_result: Tool execution result
            
        Returns:
            Actual cost in USD
        """
        # For LLM tools, try to extract actual token usage from result
        if self._is_llm_tool(tool_name, tool_args) and isinstance(tool_result, dict):
            metadata = tool_result.get("metadata", {})
            tokens_used = metadata.get("tokens_used")
            
            if tokens_used:
                model = tool_args.get("model", "gpt-4")
                
                # Get token prices
                input_price = self.pricebook.get_price(f"mcp.llm.{model}.input_tokens")
                output_price = self.pricebook.get_price(f"mcp.llm.{model}.output_tokens")
                
                if input_price and output_price:
                    # Assume 50/50 split if not specified
                    input_tokens = tokens_used // 2
                    output_tokens = tokens_used - input_tokens
                    
                    cost = (Decimal(str(input_tokens)) * input_price) + \
                           (Decimal(str(output_tokens)) * output_price)
                    
                    logger.debug(
                        f"Calculated actual cost for LLM tool '{tool_name}': "
                        f"{cost} USD (tokens={tokens_used})"
                    )
                    
                    return cost
        
        # For other tools, use estimated cost
        return await self.estimate_tool_cost(tool_name, tool_args)

    async def estimate_resource_cost(
        self,
        resource_uri: str,
        estimated_size: int = 0
    ) -> Decimal:
        """
        Estimate cost for MCP resource read.
        
        Cost calculation strategies:
        - File resources: Cost per MB
        - Database resources: Cost per query + data transfer
        - API resources: Flat rate per call
        - Default: Cost per MB
        
        Args:
            resource_uri: URI of the resource
            estimated_size: Estimated size in bytes (0 if unknown)
            
        Returns:
            Estimated cost in USD
        """
        # Extract resource type from URI
        resource_type = self._get_resource_type_from_uri(resource_uri)
        
        # Get base price for resource type
        price_key = f"mcp.resource.{resource_type}"
        base_price = self.pricebook.get_price(price_key)
        
        if base_price is None or base_price == Decimal("0"):
            # Use default resource price
            base_price = self.pricebook.get_price("mcp.resource.default")
            if base_price is None or base_price == Decimal("0"):
                # Fallback to a reasonable default
                base_price = Decimal("0.001")
                logger.warning(
                    f"No price found for resource type '{resource_type}' or 'mcp.resource.default', "
                    f"using fallback price: {base_price} USD"
                )
        
        # If size is known, calculate based on size
        if estimated_size > 0:
            # Get price per MB
            price_per_mb_key = f"mcp.resource.{resource_type}.per_mb"
            price_per_mb = self.pricebook.get_price(price_per_mb_key)
            
            if price_per_mb and price_per_mb > Decimal("0"):
                size_mb = Decimal(str(estimated_size)) / Decimal("1048576")  # bytes to MB
                cost = base_price + (size_mb * price_per_mb)
                
                logger.debug(
                    f"Estimated cost for resource '{resource_uri}': "
                    f"{cost} USD (base={base_price}, size={estimated_size} bytes)"
                )
                
                return cost
        
        # Return base price if size unknown or no per-MB pricing
        logger.debug(
            f"Estimated cost for resource '{resource_uri}': {base_price} USD (flat rate)"
        )
        
        return base_price

    def _is_llm_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """
        Check if tool is an LLM tool.
        
        Args:
            tool_name: Tool name
            tool_args: Tool arguments
            
        Returns:
            True if tool is an LLM tool
        """
        # Check tool name
        llm_keywords = ["llm", "gpt", "claude", "completion", "chat", "generate"]
        if any(keyword in tool_name.lower() for keyword in llm_keywords):
            return True
        
        # Check if tool args contain LLM-specific parameters
        llm_params = ["prompt", "model", "max_tokens", "temperature"]
        if any(param in tool_args for param in llm_params):
            return True
        
        return False

    def _is_api_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """
        Check if tool is an API tool.
        
        Args:
            tool_name: Tool name
            tool_args: Tool arguments
            
        Returns:
            True if tool is an API tool
        """
        # Check tool name
        api_keywords = ["api", "http", "rest", "request"]
        if any(keyword in tool_name.lower() for keyword in api_keywords):
            return True
        
        # Check if tool args contain API-specific parameters
        api_params = ["endpoint", "url", "method", "headers"]
        if any(param in tool_args for param in api_params):
            return True
        
        return False

    async def _estimate_llm_tool_cost(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Decimal:
        """
        Estimate cost for LLM tool calls.
        
        Extracts:
        - prompt: str (estimate input tokens)
        - max_tokens: int (estimate output tokens)
        - model: str (lookup price per token)
        
        Args:
            tool_name: Tool name
            tool_args: Tool arguments
            
        Returns:
            Estimated cost in USD
        """
        prompt = tool_args.get("prompt", "")
        max_tokens = tool_args.get("max_tokens", 1000)
        model = tool_args.get("model", "gpt-4")
        
        # Estimate input tokens (rough: 4 characters per token)
        input_tokens = len(str(prompt)) // 4
        output_tokens = max_tokens
        
        # Lookup prices from pricebook
        input_price = self.pricebook.get_price(f"mcp.llm.{model}.input_tokens")
        output_price = self.pricebook.get_price(f"mcp.llm.{model}.output_tokens")
        
        # Use defaults if not found
        if input_price is None or input_price == Decimal("0"):
            input_price = Decimal("0.00003")  # Default GPT-4 input price
            logger.warning(
                f"No input token price found for model '{model}', "
                f"using default: {input_price} USD/token"
            )
        
        if output_price is None or output_price == Decimal("0"):
            output_price = Decimal("0.00006")  # Default GPT-4 output price
            logger.warning(
                f"No output token price found for model '{model}', "
                f"using default: {output_price} USD/token"
            )
        
        cost = (Decimal(str(input_tokens)) * input_price) + \
               (Decimal(str(output_tokens)) * output_price)
        
        logger.debug(
            f"Estimated LLM cost for tool '{tool_name}': {cost} USD "
            f"(input_tokens={input_tokens}, output_tokens={output_tokens}, model={model})"
        )
        
        return cost

    async def _estimate_api_tool_cost(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Decimal:
        """
        Estimate cost for API tool calls.
        
        Extracts:
        - endpoint: str (lookup flat rate or per-request cost)
        - data_size: int (for data transfer costs)
        
        Args:
            tool_name: Tool name
            tool_args: Tool arguments
            
        Returns:
            Estimated cost in USD
        """
        endpoint = tool_args.get("endpoint", "")
        data_size = tool_args.get("data_size", 0)
        
        # Lookup base cost for endpoint
        base_cost = self.pricebook.get_price(f"mcp.api.{endpoint}")
        
        if base_cost is None or base_cost == Decimal("0"):
            # Use default API cost
            base_cost = self.pricebook.get_price("mcp.api.default")
            if base_cost is None or base_cost == Decimal("0"):
                base_cost = Decimal("0.001")  # Fallback
                logger.warning(
                    f"No API price found for endpoint '{endpoint}', "
                    f"using default: {base_cost} USD"
                )
        
        # Add data transfer cost if applicable
        if data_size > 0:
            transfer_price = self.pricebook.get_price("mcp.api.data_transfer_gb")
            if transfer_price and transfer_price > Decimal("0"):
                data_gb = Decimal(str(data_size)) / Decimal("1073741824")  # bytes to GB
                cost = base_cost + (data_gb * transfer_price)
                
                logger.debug(
                    f"Estimated API cost for tool '{tool_name}': {cost} USD "
                    f"(base={base_cost}, data_size={data_size} bytes)"
                )
                
                return cost
        
        logger.debug(
            f"Estimated API cost for tool '{tool_name}': {base_cost} USD (flat rate)"
        )
        
        return base_cost

    def _get_resource_type_from_uri(self, resource_uri: str) -> str:
        """
        Extract resource type from URI scheme.
        
        Args:
            resource_uri: Resource URI
            
        Returns:
            Resource type string
        """
        if resource_uri.startswith("file://"):
            return "file"
        elif resource_uri.startswith("http://") or resource_uri.startswith("https://"):
            return "http"
        elif resource_uri.startswith("db://"):
            return "database"
        elif resource_uri.startswith("s3://"):
            return "s3"
        else:
            return "unknown"
