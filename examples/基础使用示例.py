#!/usr/bin/env python3
"""
CogniMem 基础使用示例

运行方式：
    PYTHONPATH=src python3 docs/examples/basic_usage.py
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from cognimem.service import MemoryService

def main():
    # 初始化服务
    service = MemoryService(db_path="./data/memory.db")

    print("=== CogniMem 基础使用示例 ===\n")

    # 1. 添加记忆
    print("1. 添加记忆...")
    memory_id = service.add_memory(
        agent_id="demo_agent",
        session_id="session_001",
        content="用户更偏好使用 Python 进行自动化脚本开发，习惯使用 f-string 格式化字符串"
    )
    print(f"   记忆已保存，ID: {memory_id}\n")

    # 2. 检索记忆
    print("2. 检索相关记忆...")
    results = service.retrieve(
        query="用户喜欢什么编程语言",
        top_k=3,
        agent_id="demo_agent"
    )

    if results:
        print(f"   找到 {len(results)} 条相关记忆：")
        for result in results:
            print(f"   - [{result.id}] {result.summary}")
            print(f"     重要性: {result.importance:.2f}")
            print(f"     检索原因: {result.why_retrieved}")
    else:
        print("   未找到相关记忆\n")

    # 3. 提供反馈
    print("3. 提供反馈...")
    feedback_result = service.give_feedback(
        memory_id=memory_id,
        success=True,
        note="准确识别了用户偏好"
    )
    print(f"   反馈已记录: {feedback_result}\n")

    # 4. 执行反思
    print("4. 执行知识反思...")
    reflection_results = service.reflect(limit=50, min_group_size=2)
    print(f"   生成了 {len(reflection_results)} 条语义记忆\n")

    # 5. 查看统计
    print("5. 系统统计：")
    stats = service.stats()
    for key, value in stats.items():
        print(f"   - {key}: {value}")

if __name__ == "__main__":
    main()
