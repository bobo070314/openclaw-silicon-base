"""
headroom_adapter.py — Headroom MCP Token 压缩适配器 (v3.0)

7.15 合规依赖: 日志量 > 1GB/天时启用压缩，压缩率 60-95%。
默认禁用，通过环境变量 USE_HEADROOM=true 开启。

与主环境隔离:
  - 不修改 mes_adapter.py / apply_repair.py 等核心模块
  - 通过环境变量开关控制
  - 未来可升级为独立 requirements-optional.txt

用法:
  python -c "from integrations.headroom_adapter import HeadroomAdapter; ha = HeadroomAdapter(); print(ha.compress('test'))"
  USE_HEADROOM=true python src/core/mes_adapter.py --inject
"""

import os
import json
import logging

logger = logging.getLogger("headroom_adapter")

# 环境变量开关
ENABLED = os.getenv("USE_HEADROOM", "false").lower() == "true"
# v9.0: Headroom MCP Server 模式开关
MCP_ENABLED = os.getenv("USE_HEADROOM_MCP", "false").lower() == "true"


class HeadroomAdapter:
    """
    Headroom 压缩适配器。

    封装 headroom SDK 的 Compressor，提供统一的 compress() 接口。
    当 ENABLED=False 时以空操作模式运行，不影响现有逻辑。
    """

    def __init__(self):
        self._compressor = None
        if ENABLED:
            self._init_compressor()

    def _init_compressor(self):
        """懒初始化 headroom LogCompressor。"""
        try:
            from headroom._core import LogCompressor  # type: ignore
            self._compressor = LogCompressor()
            logger.info("Headroom LogCompressor initialized")
        except ImportError:
            logger.warning("headroom-ai not installed. Run: pip install headroom-ai")
            self._compressor = None

    def compress(self, data: str) -> str:
        """
        压缩输入字符串。

        如果 Headroom 未启用或无 compressor，直接返回原始数据。
        """
        if not self._compressor:
            return data
        try:
            result = self._compressor.compress(data)
            # result 可能是对象，提取文本内容
            if hasattr(result, "compressed"):
                compressed_text = result.compressed
            elif hasattr(result, "text"):
                compressed_text = result.text
            elif not isinstance(result, str):
                compressed_text = str(result)
            else:
                compressed_text = result
            original_size = len(data.encode("utf-8"))
            compressed_size = len(compressed_text.encode("utf-8"))
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            logger.debug(f"Compressed {original_size} -> {compressed_size} bytes ({ratio:.1f}% savings)")
            return compressed_text
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return data  # fallback: 返回未压缩数据

    def compress_json(self, data: dict) -> str:
        """压缩 JSON 字典。"""
        return self.compress(json.dumps(data, ensure_ascii=False))

    @property
    def enabled(self) -> bool:
        return ENABLED and self._compressor is not None

    @property
    def mcp_enabled(self) -> bool:
        """Headroom MCP Server 模式是否启用。
        需同时设置 USE_HEADROOM_MCP=true 和 USE_HEADROOM=true。
        实际 MCP Server 启动需 API Key，这是适配层信号。
        """
        return MCP_ENABLED and self.enabled


# 单例
adapter = HeadroomAdapter()


# 独立测试入口
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_data = (
        "This is a test log line with repetitive information " * 50
    )

    original_size = len(test_data.encode("utf-8"))

    if adapter.enabled:
        compressed = adapter.compress(test_data)
        compressed_size = len(compressed.encode("utf-8"))
        ratio = (1 - compressed_size / original_size) * 100
        print(f"USE_HEADROOM=true")
        print(f"  Original:   {original_size} bytes")
        print(f"  Compressed: {compressed_size} bytes")
        print(f"  Savings:    {ratio:.1f}%")
    else:
        print(f"USE_HEADROOM=false (default)")
        print(f"  Not compressed. Set USE_HEADROOM=true to enable.")
        print(f"  Original size: {original_size} bytes")
