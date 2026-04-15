"""
mcp_server.py — Mock MCP Server
Sprint 3: Implement ít nhất 2 MCP tools.

Mô phỏng MCP (Model Context Protocol) interface trong Python.
Agent (MCP client) gọi dispatch_tool() thay vì hard-code từng API.

Tools available:
    1. search_kb(query, top_k)           → tìm kiếm Knowledge Base (ChromaDB thật)
    2. get_ticket_info(ticket_id)        → tra cứu thông tin ticket (mock data)
    3. check_access_permission(access_level, requester_role, is_emergency)
                                         → kiểm tra quyền truy cập theo SOP
    4. create_ticket(priority, title, description)
                                         → tạo ticket mới (mock, không tạo thật)

Sử dụng:
    from mcp_server import dispatch_tool, list_tools

    # Discover available tools
    tools = list_tools()

    # Call a tool
    result = dispatch_tool("search_kb", {"query": "SLA P1", "top_k": 3})

Sprint 3 NOTE:
    - Mode Standard: file này dùng as-is (mock/in-process class)
    - Mode Advanced: thay bằng HTTP server với FastAPI hoặc dùng `mcp` library

Chạy thử:
    python mcp_server.py
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


# (ChromaDB config lives in workers/retrieval.py — không duplicate ở đây)


# ─────────────────────────────────────────────
# Tool Definitions (Schema Discovery)
# Giống với cách MCP server expose tool list cho client
# ─────────────────────────────────────────────

TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Tìm kiếm Knowledge Base nội bộ bằng semantic search (ChromaDB). Trả về top-k chunks liên quan nhất.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Câu hỏi hoặc keyword cần tìm"},
                "top_k": {"type": "integer", "description": "Số chunks cần trả về", "default": 3},
            },
            "required": ["query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "chunks": {"type": "array"},
                "sources": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    },
    "get_ticket_info": {
        "name": "get_ticket_info",
        "description": "Tra cứu thông tin ticket từ hệ thống Jira nội bộ (mock data).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "ID ticket (VD: IT-1234, P1-LATEST)"},
            },
            "required": ["ticket_id"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "priority": {"type": "string"},
                "status": {"type": "string"},
                "assignee": {"type": "string"},
                "created_at": {"type": "string"},
                "sla_deadline": {"type": "string"},
            },
        },
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_level": {"type": "integer", "description": "Level cần cấp (1, 2, hoặc 3)"},
                "requester_role": {"type": "string", "description": "Vai trò của người yêu cầu (vd: contractor, employee, manager)"},
                "is_emergency": {"type": "boolean", "description": "Có phải tình huống khẩn cấp không", "default": False},
            },
            "required": ["access_level", "requester_role"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "can_grant": {"type": "boolean"},
                "required_approvers": {"type": "array"},
                "emergency_override": {"type": "boolean"},
                "source": {"type": "string"},
            },
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Tạo ticket mới trong hệ thống Jira (MOCK — không tạo thật trong lab).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["priority", "title"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "url": {"type": "string"},
                "created_at": {"type": "string"},
            },
        },
    },
}


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

def tool_search_kb(query: str, top_k: int = 3) -> dict:
    """
    Tìm kiếm Knowledge Base bằng semantic search qua ChromaDB.

    Delegate hoàn toàn sang workers/retrieval.py — không duplicate logic.
    Nếu retrieval lỗi → trả về mock data để pipeline không crash.
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from workers.retrieval import retrieve_dense
        chunks = retrieve_dense(query, top_k=top_k)
        sources = list({c["source"] for c in chunks})
        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }

    except Exception as e:
        # Fallback: mock data nếu ChromaDB chưa setup
        print(f"  [MCP search_kb] Retrieval unavailable ({e}). Trả về mock data.")

        return {
            "chunks": [
                {
                    "text": (
                        "SLA P1: Phản hồi ban đầu 15 phút. Xử lý và khắc phục trong 4 giờ. "
                        "Escalation tự động sau 10 phút nếu chưa có phản hồi."
                    ),
                    "source": "sla_p1_2026.txt",
                    "score": 0.75,
                },
                {
                    "text": (
                        "Chính sách hoàn tiền v4: Yêu cầu trong 7 ngày, sản phẩm lỗi nhà sản xuất, "
                        "chưa sử dụng. Ngoại lệ: Flash Sale, digital product, sản phẩm đã kích hoạt "
                        "không được hoàn tiền."
                    ),
                    "source": "policy_refund_v4.txt",
                    "score": 0.70,
                },
            ],
            "sources": ["sla_p1_2026.txt", "policy_refund_v4.txt"],
            "total_found": 2,
            "_mock": True,
            "_error": str(e),
        }


# ─────────────────────────────────────────────
# Mock Ticket Database
# ─────────────────────────────────────────────

MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": [
            "slack:#incident-p1",
            "email:incident@company.internal",
            "pagerduty:oncall",
        ],
        "sla_remaining_minutes": -5,   # đã quá hạn
        "resolution_steps": [
            "Kiểm tra health check API Gateway",
            "Restart service nếu cần",
            "Notify stakeholders",
        ],
    },
    "IT-1234": {
        "ticket_id": "IT-1234",
        "priority": "P2",
        "title": "Feature login chậm cho một số user",
        "status": "open",
        "assignee": None,
        "created_at": "2026-04-13T09:15:00",
        "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
        "notifications_sent": ["slack:#it-helpdesk"],
        "sla_remaining_minutes": 240,
    },
    "IT-9999": {
        "ticket_id": "IT-9999",
        "priority": "P3",
        "title": "Yêu cầu cấp quyền Level 2 cho contractor",
        "status": "pending_approval",
        "assignee": "it.admin@company.internal",
        "created_at": "2026-04-14T08:00:00",
        "sla_deadline": "2026-04-15T08:00:00",
        "escalated": False,
        "notifications_sent": [],
        "sla_remaining_minutes": 1440,
    },
}


def tool_get_ticket_info(ticket_id: str) -> dict:
    """
    Tra cứu thông tin ticket (mock Jira data).

    Hỗ trợ alias: P1-LATEST → IT-9847
    """
    ticket = MOCK_TICKETS.get(ticket_id.upper())
    if ticket:
        return ticket

    # Không tìm thấy
    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy trong hệ thống.",
        "available_mock_ids": list(MOCK_TICKETS.keys()),
        "suggestion": "Thử P1-LATEST để xem ticket P1 hiện tại.",
    }


# ─────────────────────────────────────────────
# Mock Access Control Rules
# ─────────────────────────────────────────────

ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
        "note": "Standard user access — chỉ cần Line Manager approve.",
        "typical_sla": "1 ngày làm việc",
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": (
            "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager "
            "và IT Admin on-call. Phải review lại trong 24h."
        ),
        "note": "Elevated access — cần Line Manager + IT Admin.",
        "typical_sla": "2 ngày làm việc",
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
        "note": (
            "Admin access — KHÔNG có emergency bypass. "
            "Phải qua đầy đủ quy trình dù tình huống khẩn cấp."
        ),
        "typical_sla": "3-5 ngày làm việc",
    },
}

ROLE_RESTRICTIONS = {
    "contractor": {
        "max_level": 2,
        "note": "Contractor không được cấp Level 3 dù trong tình huống khẩn cấp.",
    },
    "intern": {
        "max_level": 1,
        "note": "Intern chỉ được cấp Level 1.",
    },
}


def tool_check_access_permission(
    access_level: int,
    requester_role: str,
    is_emergency: bool = False,
) -> dict:
    """
    Kiểm tra điều kiện cấp quyền theo Access Control SOP.

    Logic:
    - Level 1: chỉ cần Line Manager
    - Level 2: cần Line Manager + IT Admin; emergency bypass cho phép
    - Level 3: cần Line Manager + IT Admin + IT Security; KHÔNG có bypass
    - Contractor: tối đa Level 2
    - Intern: tối đa Level 1
    """
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {
            "error": f"Access level {access_level} không hợp lệ. Chỉ hỗ trợ levels: 1, 2, 3.",
        }

    notes = []
    can_grant = True
    emergency_override = False

    # Role restrictions
    role_key = requester_role.lower()
    restriction = ROLE_RESTRICTIONS.get(role_key)
    if restriction and access_level > restriction["max_level"]:
        can_grant = False
        notes.append(
            f"Vai trò '{requester_role}' bị giới hạn tối đa Level {restriction['max_level']}. "
            f"{restriction['note']}"
        )

    # Emergency logic
    if is_emergency and can_grant:
        if rule.get("emergency_can_bypass"):
            emergency_override = True
            notes.append(rule["emergency_bypass_note"])
        else:
            notes.append(
                f"Level {access_level} KHÔNG có emergency bypass. "
                "Phải tuân theo quy trình chuẩn dù khẩn cấp."
            )

    return {
        "access_level": access_level,
        "requester_role": requester_role,
        "can_grant": can_grant,
        "required_approvers": rule["required_approvers"],
        "approver_count": len(rule["required_approvers"]),
        "emergency_override": emergency_override,
        "typical_sla": rule.get("typical_sla", "N/A"),
        "notes": notes,
        "source": "access_control_sop.txt",
    }


def tool_create_ticket(priority: str, title: str, description: str = "") -> dict:
    """
    Tạo ticket mới (MOCK — in log, không push lên Jira thật).

    Sinh mock ticket ID dựa trên hash của title để deterministic.
    """
    mock_id = f"IT-{9900 + abs(hash(title)) % 99}"
    ticket = {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:300] if description else "",
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "url": f"https://jira.company.internal/browse/{mock_id}",
        "assigned_queue": f"IT-{priority}-queue",
        "note": "MOCK ticket — không tồn tại trong hệ thống thật",
    }
    print(f"  [MCP create_ticket] MOCK created: {mock_id} | {priority} | {title[:60]}")
    return ticket


# ─────────────────────────────────────────────
# Tool Registry — map tool name → function
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
}


# ─────────────────────────────────────────────
# Dispatch Layer — MCP server public interface
# ─────────────────────────────────────────────

def list_tools() -> list:
    """
    MCP discovery: trả về danh sách tools có sẵn cùng schema.
    Tương đương lệnh `tools/list` trong MCP protocol thật.

    Returns:
        List of tool schema dicts
    """
    return list(TOOL_SCHEMAS.values())


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """
    MCP execution: nhận tool_name và input dict, gọi tool tương ứng.
    Tương đương lệnh `tools/call` trong MCP protocol thật.

    Args:
        tool_name:  tên tool (phải có trong TOOL_REGISTRY)
        tool_input: input dict (phải match với tool's inputSchema)

    Returns:
        Tool output dict, hoặc error dict nếu thất bại.
        Không bao giờ raise exception — luôn trả về dict.
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "error": (
                f"Tool '{tool_name}' không tồn tại. "
                f"Available tools: {list(TOOL_REGISTRY.keys())}"
            ),
        }

    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        result = tool_fn(**tool_input)
        return result
    except TypeError as e:
        return {
            "error": f"Input không hợp lệ cho tool '{tool_name}': {e}",
            "schema": TOOL_SCHEMAS[tool_name]["inputSchema"],
        }
    except Exception as e:
        return {
            "error": f"Tool '{tool_name}' thực thi thất bại: {e}",
        }


# ─────────────────────────────────────────────
# Test & Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Server — Tool Discovery & Test")
    print("=" * 60)

    # 1. Discover tools
    print("\n📋 Available Tools:")
    for tool in list_tools():
        print(f"  • {tool['name']}: {tool['description'][:70]}...")

    # 2. Test search_kb
    print("\n🔍 Test: search_kb — 'SLA P1 resolution time'")
    result = dispatch_tool("search_kb", {"query": "SLA P1 resolution time", "top_k": 2})
    if result.get("chunks"):
        for c in result["chunks"]:
            print(f"  [{c.get('score', '?')}] {c.get('source')}: {c.get('text', '')[:80]}...")
    else:
        print(f"  Result: {result}")

    # 3. Test get_ticket_info
    print("\n🎫 Test: get_ticket_info — P1-LATEST")
    ticket = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
    print(f"  Ticket  : {ticket.get('ticket_id')} | {ticket.get('priority')} | {ticket.get('status')}")
    print(f"  Assignee: {ticket.get('assignee')}")
    if ticket.get("notifications_sent"):
        print(f"  Notified: {ticket['notifications_sent']}")

    # 4. Test check_access_permission — Level 3 emergency (không bypass)
    print("\n🔐 Test: check_access_permission — Level 3, contractor, emergency=True")
    perm = dispatch_tool("check_access_permission", {
        "access_level": 3,
        "requester_role": "contractor",
        "is_emergency": True,
    })
    print(f"  can_grant         : {perm.get('can_grant')}")
    print(f"  required_approvers: {perm.get('required_approvers')}")
    print(f"  emergency_override: {perm.get('emergency_override')}")
    for note in perm.get("notes", []):
        print(f"  note: {note}")

    # 5. Test check_access_permission — Level 2 emergency (bypass được)
    print("\n🔐 Test: check_access_permission — Level 2, employee, emergency=True")
    perm2 = dispatch_tool("check_access_permission", {
        "access_level": 2,
        "requester_role": "employee",
        "is_emergency": True,
    })
    print(f"  can_grant         : {perm2.get('can_grant')}")
    print(f"  emergency_override: {perm2.get('emergency_override')}")
    for note in perm2.get("notes", []):
        print(f"  note: {note[:100]}...")

    # 6. Test create_ticket
    print("\n🎟️  Test: create_ticket")
    new_ticket = dispatch_tool("create_ticket", {
        "priority": "P1",
        "title": "Database connection pool exhausted",
        "description": "Connection pool maxed out, prod users cannot connect.",
    })
    print(f"  Created: {new_ticket.get('ticket_id')} | {new_ticket.get('url')}")

    # 7. Test invalid tool
    print("\n❌ Test: invalid tool")
    err = dispatch_tool("nonexistent_tool", {})
    print(f"  Error: {err.get('error')}")

    print("\n✅ MCP server test done.")
    print("\nBonus Sprint 3: Implement HTTP server với FastAPI cho +2 điểm.")
