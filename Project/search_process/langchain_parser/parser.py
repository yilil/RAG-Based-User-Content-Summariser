import json
import markdown

class LangchainResponse:
    def __init__(self, response):
        self.response = response
        self.parsed_response = self.parse_response(response)

    def parse_response(self, response):
        try:
            # 尝试将 GenerateContentResponse 对象转换为字典
            response_dict = response.to_dict()
            response_json = json.dumps(response_dict, ensure_ascii=False)
            parsed_response = json.loads(response_json)
        except (json.JSONDecodeError, AttributeError):
            try:
                parsed_response = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                parsed_response = {"error": "Invalid JSON response"}
        return parsed_response

    def get_answer(self):
        # 从解析后的响应中提取答案
        if "candidates" in self.parsed_response:
            candidates = self.parsed_response.get("candidates", [])
            if candidates:
                content_parts = candidates[0].get("content", {}).get("parts", [])
                if content_parts:
                    data = content_parts[0].get("text", "No answer found")
                    html_content = markdown.markdown(data, extensions=['fenced_code'])
                    return html_content
        elif "choices" in self.parsed_response:
            choices = self.parsed_response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                data = message.get("content", "No answer found")
                html_content = markdown.markdown(data, extensions=['fenced_code'])
                return html_content
        print("DEBUG: parsed_response =", self.parsed_response)
        print("DEBUG: candidates =", self.parsed_response.get("candidates"))
        print("DEBUG: choices =", self.parsed_response.get("choices"))
        return "No answer found!"

    def get_metadata(self):
        if "usage_metadata" in self.parsed_response:
            return self.parsed_response.get("usage_metadata", {})
        elif "usage" in self.parsed_response:
            return self.parsed_response.get("usage", {})
        return {}

def parse_langchain_response(response):
    response_obj = LangchainResponse(response)
    print("DEBUG: parsed_response =", response_obj.parsed_response)
    answer = response_obj.get_answer()
    metadata = response_obj.get_metadata()
    return answer, metadata