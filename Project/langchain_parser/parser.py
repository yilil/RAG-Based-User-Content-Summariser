import json

class LangchainResponse:
    def __init__(self, response):
        self.response = response
        self.parsed_response = self.parse_response(response)

    def parse_response(self, response):
        try:
            # 将 GenerateContentResponse 对象转换为字典
            response_dict = response.to_dict()
            # 将字典转换为 JSON 字符串
            response_json = json.dumps(response_dict)
            # 解析 JSON 字符串
            parsed_response = json.loads(response_json)
        except (json.JSONDecodeError, AttributeError):
            parsed_response = {"error": "Invalid JSON response"}
        return parsed_response

    def get_answer(self):
        # 从解析后的响应中提取答案
        candidates = self.parsed_response.get("candidates", [])
        if candidates:
            content_parts = candidates[0].get("content", {}).get("parts", [])
            if content_parts:
                return content_parts[0].get("text", "No answer found")
        return "No answer found"

    def get_metadata(self):
        # 从解析后的响应中提取元数据
        return self.parsed_response.get("usage_metadata", {})

def parse_langchain_response(response):
    response_obj = LangchainResponse(response)
    print("DEBUG: parsed_response =", response_obj.parsed_response)
    answer = response_obj.get_answer()
    metadata = response_obj.get_metadata()
    return answer, metadata