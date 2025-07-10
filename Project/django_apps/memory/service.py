from .models import SessionMemory

class MemoryService:
    @staticmethod
    def get_or_create_memory(session_id, platform=None, topic=None):
        """
        获取或创建会话记忆对象
        """
        try:
            # 先尝试获取已存在的记录
            memory = SessionMemory.objects.get(session_id=session_id)
            # 如果提供了platform和topic，则更新
            if platform is not None or topic is not None:
                if platform is not None:
                    memory.platform = platform
                if topic is not None:
                    memory.topic = topic
                memory.save()
            return memory
        except SessionMemory.DoesNotExist:
            # 如果不存在，创建新记录
            return SessionMemory.objects.create(
                session_id=session_id, 
                platform=platform, 
                topic=topic
            )

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
        try:
            memory = SessionMemory.objects.get(session_id=session_id)
            memory.clear_memory()
        except SessionMemory.DoesNotExist:
            # 如果记录不存在，则无需清空
            pass

    @staticmethod
    def get_all_sessions():
        """
        按照更新时间倒序获取所有会话信息
        """
        return list(SessionMemory.objects.order_by('-updated_at'))