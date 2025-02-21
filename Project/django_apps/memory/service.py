from .models import SessionMemory

class MemoryService:
    @staticmethod
    def get_or_create_memory(session_id):
        """
        获取或创建会话记忆对象
        """
        memory, created = SessionMemory.objects.get_or_create(session_id=session_id)
        return memory

    @staticmethod
    def add_to_memory(session_id, user_input, ai_response):
        """
        添加一条对话到记忆
        """
        memory = MemoryService.get_or_create_memory(session_id)
        memory.add_memory(user_input, ai_response)

    @staticmethod
    def get_recent_memory(session_id, limit=5):
        """
        获取最近的记忆
        """
        memory = MemoryService.get_or_create_memory(session_id)
        return memory.get_recent_memory(limit)

    @staticmethod
    def clear_memory(session_id):
        """
        清空指定会话的记忆
        """
        memory = MemoryService.get_or_create_memory(session_id)
        memory.clear_memory()
