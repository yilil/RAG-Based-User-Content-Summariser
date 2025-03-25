from .models import SessionMemory

class MemoryService:
    @staticmethod
    def get_or_create_memory(session_id, platform, topic):
        """
        获取或创建会话记忆对象
        """
        memory, created = SessionMemory.objects.get_or_create(session_id=session_id, defaults={"platform": platform, "topic": topic})
        if not created:  # 如果已存在，更新平台和话题
            memory.platform = platform
            memory.topic = topic
            memory.save()
        return memory

    @staticmethod
    def add_to_memory(session_id, user_input, ai_response, platform=None, topic=None):
        """
        添加一条对话到记忆
        """
        memory = MemoryService.get_or_create_memory(session_id, platform, topic)
        memory.add_memory(user_input, ai_response)

    @staticmethod
    def get_recent_memory(session_id, limit=5, platform=None, topic=None):
        """
        获取最近的记忆
        """
        memory = MemoryService.get_or_create_memory(session_id, platform, topic)
        return memory.get_recent_memory(limit)

    @staticmethod
    def clear_memory(session_id):
        """
        清空指定会话的记忆
        """
        memory = MemoryService.get_or_create_memory(session_id)
        memory.clear_memory()

    @staticmethod
    def get_all_sessions():
        """
        按照更新时间倒序获取所有会话信息
        """
        return list(SessionMemory.objects.order_by('-updated_at'))