import json
from collections import deque
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

class Node:
    def __init__(self, state, parent=None, action=None, depth=0):
        self.state = state        # Câu hoàn chỉnh tính đến thời điểm này
        self.parent = parent      # Node câu trước đó
        self.action = action      # Token vừa được thêm vào
        self.depth = depth        # Số token đã sinh (độ sâu)

    def get_path(self):
        """Lần ngược từ đích về gốc để lấy chuỗi token đã chọn"""
        path = []
        curr = self
        while curr:
            path.append((curr.action, curr.state))
            curr = curr.parent
        return path[::-1]

    def __repr__(self):
        return f"Node(token='{self.action}', text='{self.state}')"



def get_llm_next_tokens(current_text):
    """LLM đóng vai trò là hàm Successor: sinh ra 2 token tiếp theo hợp lý nhất"""
    system_prompt = """Bạn là bộ sinh token tiếp theo (Next-Token Generator).
    Cho một câu đang viết dở, hãy đưa ra ĐÚNG 2 từ (token) tiếng Việt tiếp theo hợp lý nhất để nối tiếp câu.
    BẮT BUỘC trả về đúng định dạng JSON dạng:
    {
        "candidates": [
            {"token": "từ_1"},
            {"token": "từ_2"}
        ]
    }"""

    user_prompt = f'Câu hiện tại: "{current_text}"'

    try:
        response = client.chat.completions.create(
            model="qwen2.5:1.5b",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7 
        )
        
        data = json.loads(response.choices[0].message.content)
        successors = []
        
        for item in data.get("candidates", []):
            token = item["token"].strip()

            # Trạng thái mới = Câu cũ + token mới
            next_state = f"{current_text} {token}".strip()
            successors.append((token, next_state))
            
        return successors
    except Exception as e:
        print(f"Lỗi gọi LLM: {e}")
        return []



def bfs_token_search(start_word, goal_keyword, max_length=13):
    print(f"🚀 BẮT ĐẦU TÌM KIẾM BFS")
    print(f"- Từ xuất phát : '{start_word}'")
    print(f"- Mục tiêu      : Tìm câu có chứa từ '{goal_keyword}' (trong tối đa {max_depth} bước)\n")

    root = Node(state=start_word, depth=0)
    queue = deque([root])
    seen_states = {root.state}

    step_count = 0

    while queue:
        curr_node = queue.popleft()
        step_count += 1

        print(f"👉 [Bước {step_count} | Tầng {curr_node.depth}] Đang xét câu: '{curr_node.state}'")

        if goal_keyword.lower() in curr_node.state.lower():
            print(f"\n🎉 ĐÃ TÌM THẤY MỤC TIÊU!")
            return curr_node.get_path()

        if len(curr_node.state) >= 13:
            continue

        # Gọi LLM để sinh 2 nhánh con tiếp theo
        branches = get_llm_next_tokens(curr_node.state)
        print(f"   🤖 LLM đề xuất 2 nhánh: {[b[0] for b in branches]}")

        for token, next_text in branches:
            if next_text not in seen_states:
                seen_states.add(next_text)
                child_node = Node(state=next_text, parent=curr_node, action=token, depth=curr_node.depth + 1)
                queue.append(child_node)

    print("\n❌ Không tìm thấy câu nào đạt mục tiêu trong độ sâu cho phép.")
    return None


if __name__ == "__main__":
    path = bfs_token_search(start_word="Hôm nay", goal_keyword="mưa", max_length=13)

    if path:
        print("\n--- LỘ TRÌNH TOKEN DẪN ĐẾN ĐÍCH ---")
        for i, (token, state) in enumerate(path):
            if token is None:
                print(f"Gốc: '{state}'")
            else:
                print(f"Bước {i}: Chọn token '{token}' -> Câu: '{state}'")