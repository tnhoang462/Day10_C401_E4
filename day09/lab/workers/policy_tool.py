"""
workers/policy_tool.py — Policy & Tool Worker (Refactored)
Sprint 2+3: Kiểm tra policy dựa vào context, gọi MCP tools khi cần.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: context từ retrieval_worker
    - needs_tool: True nếu supervisor quyết định cần tool call

Output (vào AgentState):
    - policy_result: {"policy_applies", "policy_name", "exceptions_found", "source", "rule"}
    - mcp_tools_used: list of tool calls đã thực hiện
    - worker_io_log: log

Gọi độc lập để test:
    python workers/policy_tool.py
"""

import os
import sys
from typing import Optional
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env (QUAN TRỌNG: Để đọc được NVIDIA_API_KEY)
load_dotenv()

# Khởi tạo client NVIDIA - Lấy API Key từ môi trường
client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = os.getenv("NVIDIA_API_KEY") 
)

WORKER_NAME = "policy_tool_worker"


def _call_llm(messages: list) -> str:
    """Gọi NVIDIA LLM với cơ chế streaming và bắt reasoning_content."""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.1,
            top_p=1,
            max_tokens=4096,
            stream=True
        )

        full_content = ""
        # Loop qua từng chunk để nhặt reasoning và content
        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            
            # Bắt nội dung suy luận nếu có
            reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
            if reasoning:
                print(f"[Reasoning]: {reasoning}", end="", flush=True)
            
            # Nhặt nội dung câu trả lời chính
            if chunk.choices[0].delta.content is not None:
                full_content += chunk.choices[0].delta.content
                
        return full_content
    except Exception as e:
        return f"Lỗi gọi NVIDIA API: {str(e)}"


def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """Gọi MCP tool thông qua mcp_server.py"""
    try:
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }


def analyze_policy(task: str, chunks: list) -> dict:
    """Phân tích chính sách dựa trên Rule-based và AI Reasoning."""
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    # 1. Rule-based exception detection
    exceptions_found = []

    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })

    if any(kw in task_lower for kw in ["license key", "license", "subscription", "kỹ thuật số"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm kỹ thuật số không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt không được hoàn tiền.",
            "source": "policy_refund_v4.txt",
        })

    # 2. AI Analysis using NVIDIA LLM
    explanation = "Phân tích dựa trên quy tắc nghiệp vụ."
    if chunks:
        prompt = (
            f"Bạn là một chuyên gia pháp chế AI.\n"
            f"Dựa vào tài liệu nội bộ:\n{context_text}\n"
            f"Hãy xem xét yêu cầu: '{task}'\n"
            f"1. Yêu cầu này có vi phạm chính sách không?\n"
            f"2. Nếu có, hãy chỉ rõ điều khoản nào.\n"
            f"3. Nếu không, hãy xác nhận là hợp lệ."
        )
        explanation = _call_llm([{"role": "user", "content": prompt}])

    policy_name = "refund_policy_v4"
    policy_version_note = ""
    if any(kw in task_lower for kw in ["31/01", "30/01", "trước 01/02"]):
        policy_version_note = "Đơn hàng trước 01/02/2026 áp dụng chính sách v3."

    return {
        "policy_applies": len(exceptions_found) == 0,
        "policy_name": policy_name,
        "exceptions_found": exceptions_found,
        "source": list({c.get("source", "unknown") for c in chunks if c}),
        "policy_version_note": policy_version_note,
        "explanation": explanation,
    }


def run(state: dict) -> dict:
    """Worker entry point - Quản lý luồng thực thi chính."""
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "needs_tool": needs_tool,
        },
        "output": None,
        "error": None,
    }

    try:
        # Step 1: Tra cứu kiến thức nếu thiếu data
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # Step 2: Phân tích chính sách
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # Step 3: Tra cứu Ticket trạng thái thực tế
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)

        # Ghi log output
        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "mcp_calls": len(state["mcp_tools_used"]),
        }
        state["history"].append(f"[{WORKER_NAME}] Phân tích hoàn tất.")

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        state["history"].append(f"[{WORKER_NAME}] Lỗi: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


if __name__ == "__main__":
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)

    test_cases = [
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
            "needs_tool": True
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
            "needs_tool": True
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
            "needs_tool": True
        },
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n✅ policy_tool_worker test done.")
